"""Run AnalysisPipeline.analyze(symbol, news=...) and format result for Telegram.

Adapts to the v3 API: LLMAnalysis carries direction_pick + direction_rationale,
JEVDecision carries score (in [0,1]; >= threshold adopts LLM pick, else HOLD).

Reads .env from the project root. Configurable via --news-file (JSON list) or
HTTP fetcher fallback.

Usage:
    python -m scripts.run_analysis BTCUSDT
    python -m scripts.run_analysis ETHUSDT --news-file path/to/news.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import traceback
from pathlib import Path

# Make src/ importable when run from project root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_quant.config.settings import get_settings
from ai_quant.jev.client import JEVClient
from ai_quant.jev.decision import JEVDecisionEngine
from ai_quant.llm.analyzer import LLMAnalyzer
from ai_quant.llm.client import LLMClient
from ai_quant.market.client import MarketDataClient
from ai_quant.pipeline.analysis import AnalysisPipeline
from ai_quant.storage.database import PredictionStore


# JEV score_threshold defaults to 0.65 in JEVSettings; if LLM pick is rejected
# the engine returns HOLD with confidence = 1 - score.
JEV_SCORE_THRESHOLD = 0.65
DEFAULT_NEWS_HOURS = 24
DEFAULT_NEWS_MAX = 10


def load_news(symbol: str, hours: int, max_items: int) -> list[dict]:
    """Synchronous wrapper around fetch_all.

    Note: do NOT call this from inside a running event loop — use
    `await fetch_all(...)` directly instead. main_async() does that.
    """
    from scripts.fetch_news import fetch_all  # type: ignore

    table = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}
    currencies = [table[symbol.upper()]] if symbol.upper() in table else ["BTC", "ETH"]
    items = asyncio.run(fetch_all(currencies, hours, max_items))
    return [{k: v for k, v in i.items() if not k.startswith("_")} for i in items]


async def load_news_async(symbol: str, hours: int, max_items: int) -> list[dict]:
    """Async version — awaits fetch_all directly inside the running loop."""
    from scripts.fetch_news import fetch_all  # type: ignore

    table = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}
    currencies = [table[symbol.upper()]] if symbol.upper() in table else ["BTC", "ETH"]
    items = await fetch_all(currencies, hours, max_items)
    return [{k: v for k, v in i.items() if not k.startswith("_")} for i in items]


def load_news_from_file(path: str) -> list[dict]:
    """Read pre-fetched news from a JSON file (e.g. written by a browser driver).

    Expected: list of dicts with at minimum {title, source, url, ...}.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"news file must contain a JSON list, got {type(data).__name__}")
    return data


async def analyze_with_jev_retry(pipeline: AnalysisPipeline, symbol: str, news: list[dict]) -> object:
    """Run pipeline.analyze(); retry on transient failures.

    JEV's free tier rate limit (1 req/min) is the dominant failure mode; we
    back off 65s between retries. LLM errors retry together — re-running
    the LLM is cheap.
    """
    last_exc = None
    for attempt in range(1, 3):  # MAX_RETRIES = 2
        try:
            return await pipeline.analyze(symbol, news=news)
        except Exception as exc:
            last_exc = exc
            print(
                f"[analyze] attempt {attempt}/2 failed: {exc.__class__.__name__}: {exc}",
                file=sys.stderr,
            )
            print("[analyze] sleeping 65s before retry", file=sys.stderr)
            await asyncio.sleep(65)
    raise RuntimeError("analyze failed after 2 attempts") from last_exc


def format_for_telegram(result, symbol: str, news_count: int) -> str:
    """Compact Telegram-friendly summary.

    Shows LLM pick + JEV score + JEV adopted direction. If JEV rejected the
    LLM pick (score < threshold), the message flags that explicitly.
    """
    a = result.llm_analysis
    j = result.jev_decision

    direction_map = {"LONG": "🟢 LONG", "SHORT": "🔴 SHORT", "HOLD": "⚪ HOLD"}
    jev_str = direction_map.get(j.direction, j.direction)
    llm_str = direction_map.get(a.direction_pick, a.direction_pick)

    score_line = (
        f"trend {a.trend:.2f} · fund {a.fundamental:.2f} · risk {a.risk:.2f} · "
        f"event {a.event:.2f} · sent {a.sentiment:.2f}"
    )

    summary = (a.summary or "").strip()
    if "." in summary and len(summary) > 200:
        summary = summary.split(". ")[0].rstrip(".") + "."

    jev_rejected = a.direction_pick != j.direction and j.direction == "HOLD"
    if jev_rejected:
        verdict_note = (
            f"⚠️ JEV rejected LLM pick ({a.direction_pick}); "
            f"score {j.score:.2f} < threshold {JEV_SCORE_THRESHOLD:.2f}"
        )
    elif a.direction_pick != j.direction:
        verdict_note = (
            f"⚠️ LLM pick {a.direction_pick} → JEV adopted {j.direction} "
            f"(score {j.score:.2f})"
        )
    else:
        verdict_note = f"LLM & JEV agree ({a.direction_pick}, score {j.score:.2f})"

    return (
        f"📊 *{symbol}*\n"
        f"\n"
        f"JEV: {jev_str}  (score {j.score:.2f}, conf {j.confidence:.2f})\n"
        f"LLM pick: {llm_str}\n"
        f"{score_line}\n"
        f"\n"
        f"{summary or '(no summary)'}\n"
        f"\n"
        f"{verdict_note}"
    )


async def main_async(symbol: str, hours: int, max_news: int, news_file: str | None = None) -> int:
    settings = get_settings()
    if news_file:
        news = load_news_from_file(news_file)
        print(f"[analyze] {symbol} news loaded from {news_file}: {len(news)} items", file=sys.stderr)
    else:
        news = await load_news_async(symbol, hours, max_news)
        print(f"[analyze] {symbol} news items: {len(news)}", file=sys.stderr)

    pipeline = AnalysisPipeline(
        MarketDataClient(settings.market),
        LLMAnalyzer(LLMClient(settings.llm)),
        JEVDecisionEngine(JEVClient(settings.jev)),
        PredictionStore(settings.database_url),
    )
    try:
        result = await analyze_with_jev_retry(pipeline, symbol, news)
    except Exception as exc:
        print(f"[analyze] giving up: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        failure_msg = (
            f"⚠️ *{symbol}* analysis failed\n"
            f"`{exc.__class__.__name__}: {str(exc)[:200]}`"
        )
        print(failure_msg)
        return 1

    print(format_for_telegram(result, symbol, len(news)))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", help="e.g. BTCUSDT")
    parser.add_argument("--hours", type=int, default=DEFAULT_NEWS_HOURS)
    parser.add_argument("--max-news", type=int, default=DEFAULT_NEWS_MAX)
    parser.add_argument("--news-file", type=str, default=None,
                        help="Path to a JSON list of pre-fetched news; "
                             "if provided, fetcher is skipped.")
    args = parser.parse_args()
    sys.exit(asyncio.run(main_async(args.symbol.upper(), args.hours, args.max_news, args.news_file)))


if __name__ == "__main__":
    main()
