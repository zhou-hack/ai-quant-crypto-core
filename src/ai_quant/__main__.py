from __future__ import annotations

import asyncio
import sys

from ai_quant.config.settings import get_settings
from ai_quant.jev.client import JEVClient
from ai_quant.jev.decision import JEVDecisionEngine
from ai_quant.llm.analyzer import LLMAnalyzer
from ai_quant.llm.client import LLMClient
from ai_quant.market.client import MarketDataClient
from ai_quant.pipeline.analysis import AnalysisPipeline
from ai_quant.storage.database import PredictionStore


async def run_analyze(symbol: str) -> None:
    settings = get_settings()
    result = await AnalysisPipeline(MarketDataClient(settings.market), LLMAnalyzer(LLMClient(settings.llm)), JEVDecisionEngine(JEVClient(settings.jev)), PredictionStore(settings.database_url)).analyze(symbol)
    print(symbol.upper())
    print("\nLLM Analysis:")
    for name in ("trend", "fundamental", "risk", "event", "sentiment"):
        print(f"{name + ':':14}{getattr(result.llm_analysis, name):.2f}")
    print("\nJEV:")
    print(f"direction:   {result.jev_decision.direction}")
    print(f"confidence:  {result.jev_decision.confidence:.2f}")


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "analyze":
        asyncio.run(run_analyze(sys.argv[2]))
    else:
        print("Usage: python -m ai_quant analyze SYMBOL")


if __name__ == "__main__":
    main()
