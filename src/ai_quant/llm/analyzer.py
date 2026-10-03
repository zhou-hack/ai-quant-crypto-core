from __future__ import annotations

import json
from pydantic import BaseModel, Field, field_validator

from .client import LLMClient


class LLMAnalysis(BaseModel):
    trend: float = Field(ge=0, le=1)
    fundamental: float = Field(ge=0, le=1)
    risk: float = Field(ge=0, le=1)
    event: float = Field(ge=0, le=1)
    sentiment: float = Field(ge=0, le=1)
    summary: str = ""


class NewsBrief(BaseModel):
    summary: str
    important_events: list[dict] = Field(default_factory=list)


class LLMAnalyzer:
    def __init__(self, client: LLMClient):
        self.client = client

    async def summarize_news(self, *, news: list[dict], max_events: int = 5) -> NewsBrief:
        if not news:
            return NewsBrief(summary="No news was provided.")
        messages = [
            {"role": "system", "content": f"Summarize the supplied crypto news. Select at most {max_events} important, non-duplicate events. Preserve source, URL, published time, factual claim, impact (positive/negative/neutral/uncertain), and confidence. Return JSON with summary and important_events. Do not make a trading decision."},
            {"role": "user", "content": json.dumps(news, default=str)},
        ]
        content = await self.client.chat(messages)
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM returned non-JSON news summary") from exc
        brief = NewsBrief.model_validate(payload)
        brief.important_events = brief.important_events[:max_events]
        return brief

    async def analyze(self, *, market_data: dict, context: dict | None = None) -> LLMAnalysis:
        messages = [{"role": "system", "content": "Analyze the market. Return JSON with trend, fundamental, risk, event, sentiment (0 to 1) and summary. Do not return a trading direction."},
                    {"role": "user", "content": json.dumps({"market": market_data, "context": context or {}}, default=str)}]
        content = await self.client.chat(messages)
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM returned non-JSON analysis") from exc
        return LLMAnalysis.model_validate(payload)

    async def review_decision(self, *, state: dict, decision: dict, news: list[dict] | None = None) -> str:
        """Explain and sanity-check JEV output without changing the original decision."""
        messages = [
            {"role": "system", "content": "Review a JEV directional decision against the supplied market state and news. Return a concise evidence-based explanation. Do not create an order and do not replace the original direction."},
            {"role": "user", "content": json.dumps({"state": state, "jev_decision": decision, "news": news or []}, default=str)},
        ]
        return await self.client.chat(messages)
