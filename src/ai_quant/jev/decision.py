from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from .client import JEVClient


class JEVDecision(BaseModel):
    symbol: str
    direction: Literal["LONG", "SHORT", "HOLD"]
    confidence: float = Field(ge=0, le=1)
    model: str
    timestamp: datetime


class JEVDecisionEngine:
    def __init__(self, client: JEVClient):
        self.client = client

    async def decide(self, *, symbol: str, state: dict, model: str | None = None) -> JEVDecision:
        question = {
            "text": "Based on the provided market state, what is the most appropriate directional decision for the next 1-3 days?",
            "choices": ["LONG", "SHORT", "HOLD"],
        }
        payload = await self.client.decide(state=state, question=question, model=model)
        decision = payload.get("decision", payload)
        direction = decision.get("direction") or decision.get("choice")
        confidence = decision.get("confidence")
        if direction not in {"LONG", "SHORT", "HOLD"} or confidence is None:
            raise ValueError("JEV response did not contain a valid direction and confidence")
        return JEVDecision(symbol=symbol.upper(), direction=direction, confidence=confidence,
                           model=model or self.client.settings.model,
                           timestamp=datetime.now(timezone.utc))
