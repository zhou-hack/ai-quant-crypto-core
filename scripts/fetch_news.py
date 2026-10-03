"""Fetch and dedupe BTC/ETH news from CryptoPanic + CoinDesk RSS.

Output: list of dicts compatible with ai_quant.news.models.NewsEvent.
Filters to currency keywords BTC/Bitcoin and ETH/Ethereum.

Run: python -m scripts.fetch_news --currencies BTC,ETH --hours 24
Writes JSON list to stdout (one event per line in compact form).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx


CRYPTOPANIC_URL = "https://cryptopanic.com/api/v1/posts/"

# Multiple RSS sources — some are flaky from the VM's VPN exit, so we run them all
# in parallel and dedupe. The first one that works wins; later ones fill gaps.
RSS_SOURCES = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("The Block", "https://www.theblock.co/rss.xml"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("Bitcoin Magazine", "https://bitcoinmagazine.com/.rss/full/"),
]

TIMEOUT = 15.0

# Match either ticker or full name. Word boundary so "eth" doesn't fire on "feather".
CURRENCY_PATTERNS = {
    "BTC": re.compile(r"\b(btc|bitcoin)\b", re.IGNORECASE),
    "ETH": re.compile(r"\b(eth|ethereum)\b", re.IGNORECASE),
}


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def _filter_currency(text: str, currencies: list[str]) -> list[str]:
    """Return which currencies this text mentions. Empty list = skip."""
    hits = []
    for c in currencies:
        if CURRENCY_PATTERNS[c].search(text):
            hits.append(c)
    return hits


async def fetch_cryptopanic(client: httpx.AsyncClient, currencies: list[str]) -> list[dict]:
    """CryptoPanic public API; free tier, no key needed."""
    cur_param = ",".join(currencies)
    try:
        resp = await client.get(
            CRYPTOPANIC_URL,
            params={"currencies": cur_param, "kind": "news", "public": "true"},
        )
        resp.raise_for_status()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        print(f"[cryptopanic] fetch failed: {exc}", file=sys.stderr)
        return []
    items = []
    for post in resp.json().get("results", []):
        text = f"{post.get('title', '')} {post.get('url', '')}"
        hits = _filter_currency(text, currencies)
        if not hits:
            continue
        items.append({
            "title": post.get("title", "").strip(),
            "source": "CryptoPanic",
            "url": post.get("url", ""),
            "published_at": post.get("published_at"),  # ISO string
            "summary": "",  # CryptoPanic free tier has no body
            "impact": "uncertain",
            "confidence": 0.5,
            "_currencies": hits,
        })
    return items


async def fetch_all_rss(client: httpx.AsyncClient, currencies: list[str]) -> list[dict]:
    """Fan out across all RSS sources in parallel."""
    results = await asyncio.gather(
        *(fetch_one_rss(client, name, url, currencies) for name, url in RSS_SOURCES),
        return_exceptions=False,
    )
    out = []
    for r in results:
        out.extend(r)
    return out


def _normalize_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _within_hours(item: dict, cutoff: datetime) -> bool:
    dt = _normalize_dt(item.get("published_at"))
    if dt is None:
        # Keep undated items rather than drop; LLM can handle.
        return True
    return dt >= cutoff


def dedupe(items: list[dict]) -> list[dict]:
    """Drop duplicate URLs and identical titles (case-folded)."""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    out = []
    for item in items:
        url = item.get("url", "")
        title_key = (item.get("title") or "").strip().lower()
        if not url or url in seen_urls:
            continue
        if title_key and title_key in seen_titles:
            continue
        seen_urls.add(url)
        if title_key:
            seen_titles.add(title_key)
        out.append(item)
    return out


async def fetch_one_rss(client: httpx.AsyncClient, source_name: str, url: str, currencies: list[str]) -> list[dict]:
    """Single RSS source. Failures are swallowed; caller runs many in parallel."""
    try:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"[{source_name}] fetch failed: {exc}", file=sys.stderr)
        return []
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as exc:
        print(f"[{source_name}] parse failed: {exc}", file=sys.stderr)
        return []
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        text = f"{title} {desc}"
        hits = _filter_currency(text, currencies)
        if not hits:
            continue
        try:
            dt = parsedate_to_datetime(pub).astimezone(timezone.utc) if pub else None
            published_at = dt.isoformat() if dt else None
        except (ValueError, TypeError):
            published_at = None
        items.append({
            "title": title,
            "source": source_name,
            "url": link,
            "published_at": published_at,
            "summary": desc[:280],
            "impact": "uncertain",
            "confidence": 0.5,
            "_currencies": hits,
        })
    return items


async def fetch_all(currencies: list[str], hours: int, max_items: int = 30) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        cp, rss = await asyncio.gather(
            fetch_cryptopanic(client, currencies),
            fetch_all_rss(client, currencies),
        )
    merged = dedupe(cp + rss)
    filtered = [m for m in merged if _within_hours(m, cutoff)]
    filtered.sort(key=lambda i: i.get("published_at") or "", reverse=True)
    return filtered[:max_items]


def _strip_internal(item: dict) -> dict:
    """Drop the _currencies marker before returning to LLM."""
    return {k: v for k, v in item.items() if not k.startswith("_")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--currencies", default="BTC,ETH", help="comma-separated tickers")
    parser.add_argument("--hours", type=int, default=24, help="lookback window")
    parser.add_argument("--max", type=int, default=30, help="max items after dedupe")
    args = parser.parse_args()
    currencies = [c.strip().upper() for c in args.currencies.split(",") if c.strip()]
    items = asyncio.run(fetch_all(currencies, args.hours, args.max))
    clean = [_strip_internal(i) for i in items]
    json.dump(clean, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
