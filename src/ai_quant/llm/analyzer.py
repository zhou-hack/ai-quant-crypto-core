from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .client import LLMClient


class LLMAnalysis(BaseModel):
    trend: float = Field(ge=0, le=1)
    fundamental: float = Field(ge=0, le=1)
    risk: float = Field(ge=0, le=1)
    event: float = Field(ge=0, le=1)
    sentiment: float = Field(ge=0, le=1)
    summary: str = ""
    direction_pick: Literal["LONG", "SHORT", "HOLD"] = "HOLD"
    direction_rationale: str = ""


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
        messages = [
            {"role": "system", "content": (
                "Analyze the crypto market and return STRICT JSON only. "
                "Required numeric keys (each MUST be a number between 0.0 and 1.0): "
                "trend, fundamental, risk, event, sentiment (use 0.0 if unknown). "
                "Required string keys: summary, direction_pick, direction_rationale. "
                "direction_pick MUST be exactly one of: LONG, SHORT, HOLD. "
                "direction_rationale is a one-sentence reason for the pick. "
                "Do NOT nest objects or add sub-fields under any numeric score. "
                "Output JSON, no prose, no markdown fences."
            )},
            {"role": "user", "content": json.dumps({"market": market_data, "context": context or {}}, default=str)},
        ]
        content = await self.client.chat(messages)
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM returned non-JSON analysis") from exc
        return LLMAnalysis.model_validate(payload)

    async def review_decision(self, *, state: dict, decision: dict, news: list[dict] | dict | None = None) -> str:
        """Explain and sanity-check JEV output without changing the original decision."""
        messages = [
            {"role": "system", "content": (
                "Review a JEV decision against the supplied market state and news. Return a concise, "
                "evidence-based explanation. Preserve the supplied JEV score and direction exactly; "
                "do not rewrite, recalculate, or replace either value. Include both values verbatim in "
                "your response. Do not create an order."
            )},
            {"role": "user", "content": json.dumps({"state": state, "jev_decision": decision, "news": news or []}, default=str)},
        ]
        return await self.client.chat(messages)
