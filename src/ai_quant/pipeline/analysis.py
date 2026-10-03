from __future__ import annotations

from pydantic import BaseModel, Field

from ai_quant.jev.decision import JEVDecision, JEVDecisionEngine
from ai_quant.llm.analyzer import LLMAnalysis, LLMAnalyzer
from ai_quant.market.client import MarketDataClient
from ai_quant.market.state import MarketState, StateBuilder
from ai_quant.storage.database import PredictionStore


class AnalysisResult(BaseModel):
    state: MarketState
    llm_analysis: LLMAnalysis
    jev_decision: JEVDecision
    decision_review: str | None = None
    market_data: dict = Field(default_factory=dict)
    news_brief: dict = Field(default_factory=dict)
    final_judgment: str | None = None


class AnalysisPipeline:
    def __init__(self, market: MarketDataClient, analyzer: LLMAnalyzer, jev: JEVDecisionEngine,
                 store: PredictionStore | None = None):
        self.market, self.analyzer, self.jev = market, analyzer, jev
        self.store = store

    async def analyze(self, symbol: str, *, news: list[dict] | None = None, lookback_days: int | None = None, intervals: list[str] | None = None) -> AnalysisResult:
        settings = self.market.settings
        news_brief = await self.analyzer.summarize_news(news=news or [])
        history = await self.market.historical_data([symbol], intervals=intervals or settings.intervals, lookback_days=lookback_days or settings.lookback_days)
        by_interval = history[symbol.upper()]
        primary_interval = "1h" if "1h" in by_interval else next(iter(by_interval))
        candles = by_interval[primary_interval]
        market_data = {"symbol": symbol.upper(), "lookback_days": lookback_days or settings.lookback_days, "candles": {interval: [c.model_dump(mode="json") for c in values] for interval, values in by_interval.items()}, "news": news_brief.model_dump(mode="json")}
        analysis = await self.analyzer.analyze(market_data=market_data, context={"news": news_brief.model_dump(mode="json")})
        state = StateBuilder().build(symbol=symbol, candles=candles, llm_analysis=analysis, market_context={"intervals": list(by_interval), "lookback_days": lookback_days or settings.lookback_days, "news": news_brief.model_dump(mode="json")})
        decision = await self.jev.decide(symbol=symbol, state=state.model_dump())
        review = await self.analyzer.review_decision(state=state.model_dump(mode="json"), decision=decision.model_dump(mode="json"), news=news_brief.important_events)
        if self.store:
            self.store.save(state=state, llm_analysis=analysis, decision=decision)
        return AnalysisResult(state=state, llm_analysis=analysis, jev_decision=decision, decision_review=review, market_data=market_data, news_brief=news_brief.model_dump(mode="json"), final_judgment=review)
