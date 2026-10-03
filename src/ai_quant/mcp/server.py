from __future__ import annotations

import json

from ai_quant.config.settings import get_settings
from ai_quant.storage.database import PredictionStore


def create_server():
    """Create a FastMCP server lazily so the core package stays usable without MCP extras."""
    try:
        from fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install optional dependency with: pip install '.[mcp]'") from exc
    mcp = FastMCP("ai-quant")
    store = PredictionStore(get_settings().database_url)

    @mcp.tool()
    async def get_market_data(symbols: list[str], intervals: list[str] | None = None, lookback_days: int = 7) -> dict:
        """Fetch recent historical candles for Hermes research; this tool cannot trade."""
        settings = get_settings()
        if not symbols or len(symbols) > settings.market.max_symbols:
            raise ValueError(f"provide 1 to {settings.market.max_symbols} symbols")
        if not 1 <= lookback_days <= 30:
            raise ValueError("lookback_days must be between 1 and 30")
        from ai_quant.market.client import MarketDataClient
        history = await MarketDataClient(settings.market).historical_data(symbols, intervals=intervals or settings.market.intervals, lookback_days=lookback_days)
        return {"lookback_days": lookback_days, "intervals": intervals or settings.market.intervals, "data": {symbol: {interval: [c.model_dump(mode="json") for c in candles] for interval, candles in values.items()} for symbol, values in history.items()}}

    @mcp.tool()
    async def get_market_state(symbol: str) -> dict:
        rows = store.get(symbol=symbol, limit=1)
        return rows[0]["state_snapshot"] if rows else {"symbol": symbol.upper(), "message": "No stored state"}

    @mcp.tool()
    async def get_prediction(symbol: str, limit: int = 20) -> list[dict]:
        return store.get(symbol=symbol, limit=limit)

    @mcp.tool()
    async def get_predictions(symbols: list[str] | None = None, limit: int = 20) -> list[dict]:
        if not symbols:
            return store.get(limit=limit)
        return [item for symbol in symbols for item in store.get(symbol=symbol, limit=limit)]

    @mcp.tool()
    async def jev_decide(symbol: str, state: dict) -> dict:
        from ai_quant.jev.decision import JEVDecisionEngine
        from ai_quant.jev.client import JEVClient
        decision = await JEVDecisionEngine(JEVClient(get_settings().jev)).decide(symbol=symbol, state=state)
        return decision.model_dump(mode="json")

    @mcp.tool()
    async def analyze_market(symbol: str, news: list[dict] | None = None, lookback_days: int = 7, intervals: list[str] | None = None) -> dict:
        from ai_quant.jev.client import JEVClient
        from ai_quant.jev.decision import JEVDecisionEngine
        from ai_quant.llm.analyzer import LLMAnalyzer
        from ai_quant.llm.client import LLMClient
        from ai_quant.market.client import MarketDataClient
        from ai_quant.pipeline.analysis import AnalysisPipeline
        settings = get_settings()
        result = await AnalysisPipeline(MarketDataClient(settings.market), LLMAnalyzer(LLMClient(settings.llm)), JEVDecisionEngine(JEVClient(settings.jev)), store).analyze(symbol, news=news, lookback_days=lookback_days, intervals=intervals)
        return result.model_dump(mode="json")

    return mcp


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
