from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from .client import JEVClient


class JEVDecision(BaseModel):
    symbol: str
    direction: Literal["LONG", "SHORT", "HOLD"]
    confidence: float = Field(ge=0, le=1)
    score: float = Field(ge=0, le=1)
    model: str
    timestamp: datetime


class JEVDecisionEngine:
    def __init__(self, client: JEVClient):
        self.client = client

    async def decide(
        self,
        *,
        symbol: str,
        state: dict,
        direction_pick: Literal["LONG", "SHORT", "HOLD"] | None = None,
        llm_pick: Literal["LONG", "SHORT", "HOLD"] | None = None,
        model: str | None = None,
    ) -> JEVDecision:
        state_data = state.model_dump() if hasattr(state, "model_dump") else state
        if not isinstance(state_data, dict):
            raise ValueError("market state must be an object")
        llm_analysis = state_data.get("llm_analysis") or {}
        if not isinstance(llm_analysis, dict):
            llm_analysis = llm_analysis.model_dump() if hasattr(llm_analysis, "model_dump") else {}
        if direction_pick is not None and llm_pick is not None and direction_pick != llm_pick:
            raise ValueError("direction_pick and llm_pick must match when both are provided")
        nominated_direction = direction_pick if direction_pick is not None else llm_pick
        nominated_direction = nominated_direction or llm_analysis.get("direction_pick", "HOLD")
        if nominated_direction not in {"LONG", "SHORT", "HOLD"}:
            raise ValueError("LLM direction_pick must be LONG, SHORT, or HOLD")
        rationale = llm_analysis.get("direction_rationale", "")
        state_text = json.dumps(state_data, default=str, ensure_ascii=False)
        instructions = (
            f"LLM 提名的方向是 {nominated_direction}，交易对为 {symbol.upper()}，评估窗口为未来 24-72 小时。"
            f"LLM 提名理由：{rationale or '未提供'}。请基于提供的市场状态和新闻，评估这个提名是否合理。"
        )
        criteria = {
            "true": "LLM 提名的方向与市场状态、新闻信号一致，操作合理。",
            "false": "LLM 提名的方向缺乏支撑，存在被否决的风险或更适合观望。",
        }
        score = await self.client.decide(
            state_text=state_text,
            instructions=instructions,
            criteria=criteria,
            question_name=getattr(self.client.settings, "question_name", "direction_appropriateness"),
            model=model,
        )
        threshold = getattr(self.client.settings, "score_threshold", 0.65)
        if score >= threshold:
            direction = nominated_direction
            confidence = score
        else:
            direction = "HOLD"
            confidence = 1.0 - score
        return JEVDecision(
            symbol=symbol.upper(),
            direction=direction,
            confidence=confidence,
            score=score,
            model=model or self.client.settings.model,
            timestamp=datetime.now(timezone.utc),
        )
