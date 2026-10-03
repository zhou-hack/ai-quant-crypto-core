from __future__ import annotations

from pydantic import BaseModel, Field

from .candles import Candle
from ai_quant.llm.analyzer import LLMAnalysis


class MarketMetrics(BaseModel):
    price: float = Field(ge=0)
    volume: float = Field(ge=0)
    volatility: float = Field(ge=0)
    volume_zscore: float


class TechnicalMetrics(BaseModel):
    rsi: float = Field(ge=0, le=100)
    momentum: float


class MarketState(BaseModel):
    symbol: str
    market: MarketMetrics
    technical: TechnicalMetrics
    llm_analysis: LLMAnalysis
    market_context: dict = Field(default_factory=dict)


class StateBuilder:
    def build(self, *, symbol: str, candles: list[Candle], llm_analysis: LLMAnalysis, market_context: dict | None = None) -> MarketState:
        if not candles:
            raise ValueError("at least one candle is required")
        closes = [c.close for c in candles]
        volumes = [c.volume for c in candles]
        price = closes[-1]
        returns = [(b - a) / a for a, b in zip(closes, closes[1:]) if a]
        volatility = (sum((r - sum(returns) / len(returns)) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0.0
        avg_volume = sum(volumes) / len(volumes)
        std_volume = (sum((v - avg_volume) ** 2 for v in volumes) / len(volumes)) ** 0.5 if volumes else 0
        zscore = (volumes[-1] - avg_volume) / std_volume if std_volume else 0.0
        period = closes[-14:]
        gains = [max(b - a, 0) for a, b in zip(period, period[1:])]
        losses = [max(a - b, 0) for a, b in zip(period, period[1:])]
        avg_gain, avg_loss = sum(gains) / max(len(gains), 1), sum(losses) / max(len(losses), 1)
        rsi = 100.0 if avg_loss == 0 and avg_gain > 0 else 0.0 if avg_gain == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
        momentum = (closes[-1] - closes[0]) / closes[0] if closes[0] else 0.0
        return MarketState(symbol=symbol.upper(), market={"price": price, "volume": volumes[-1], "volatility": volatility, "volume_zscore": zscore}, technical={"rsi": rsi, "momentum": momentum}, llm_analysis=llm_analysis, market_context=market_context or {})
