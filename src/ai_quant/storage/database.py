from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ai_quant.jev.decision import JEVDecision
from ai_quant.market.state import MarketState
from ai_quant.llm.analyzer import LLMAnalysis


class PredictionStore:
    def __init__(self, database_url: str = "sqlite:///./data/quant.db"):
        self.path = Path(database_url.removeprefix("sqlite:///"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL, state_snapshot TEXT NOT NULL,
                llm_analysis TEXT NOT NULL, jev_model TEXT NOT NULL,
                jev_direction TEXT NOT NULL, jev_confidence REAL NOT NULL,
                horizon TEXT NOT NULL)""")

    def _connect(self):
        return sqlite3.connect(self.path)

    def save(self, *, state: MarketState, llm_analysis: LLMAnalysis, decision: JEVDecision, horizon: str = "24-72h") -> int:
        with self._connect() as conn:
            cur = conn.execute("INSERT INTO predictions(timestamp,symbol,state_snapshot,llm_analysis,jev_model,jev_direction,jev_confidence,horizon) VALUES(?,?,?,?,?,?,?,?)",
                (decision.timestamp.isoformat(), decision.symbol, state.model_dump_json(), llm_analysis.model_dump_json(), decision.model, decision.direction, decision.confidence, horizon))
            return int(cur.lastrowid)

    def list(self, *, symbol: str | None = None, limit: int = 20) -> list[dict]:
        query = "SELECT * FROM predictions"
        params: list = []
        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol.upper())
        query += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, limit))
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        keys = ["id", "timestamp", "symbol", "state_snapshot", "llm_analysis", "jev_model", "jev_direction", "jev_confidence", "horizon"]
        return [dict(zip(keys, row)) for row in rows]

    def get(self, *, symbol: str | None = None, limit: int = 20) -> list[dict]:
        """Compatibility alias used by the MCP tools."""
        return self.list(symbol=symbol, limit=limit)
