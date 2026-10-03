import json
import sqlite3
from datetime import datetime, timezone

import httpx
import pytest

from ai_quant.config.settings import JEVSettings, get_settings
from ai_quant.jev.client import JEVClient
from ai_quant.jev.decision import JEVDecisionEngine
from ai_quant.llm.analyzer import LLMAnalysis
from ai_quant.market.candles import Candle
from ai_quant.market.state import StateBuilder
from ai_quant.storage.database import PredictionStore
from ai_quant.jev.decision import JEVDecision


def test_config_keeps_llm_and_jev_separate(tmp_path):
    env = tmp_path / ".env"
    env.write_text("LLM_BASE_URL=https://llm\nLLM_API_KEY=l\nJEV_BASE_URL=https://jev\nJEV_API_KEY=j\nJEV_SCORE_THRESHOLD=0.72\nJEV_QUESTION_NAME=pick_check\nSYMBOLS=BTCUSDT,ETHUSDT\n", encoding="utf-8")
    settings = get_settings(env_file=env, yaml_file=tmp_path / "none.yaml")
    assert settings.llm.base_url != settings.jev.base_url
    assert settings.llm.api_key != settings.jev.api_key
    assert settings.jev.score_threshold == .72
    assert settings.jev.question_name == "pick_check"
    assert settings.symbols == ["BTCUSDT", "ETHUSDT"]


def test_state_builder_and_prediction_storage(tmp_path):
    candles = [Candle(timestamp=datetime.now(timezone.utc), open=i, high=i + 1, low=i - 1, close=i, volume=100 + i) for i in range(1, 20)]
    analysis = LLMAnalysis(trend=.7, fundamental=.5, risk=.2, event=.4, sentiment=.6, summary="ok")
    state = StateBuilder().build(symbol="BTCUSDT", candles=candles, llm_analysis=analysis)
    assert 0 <= state.llm_analysis.trend <= 1
    decision = JEVDecision(symbol="BTCUSDT", direction="HOLD", confidence=.8, score=.2, model="jev-latest", timestamp=datetime.now(timezone.utc))
    store = PredictionStore(f"sqlite:///{tmp_path / 'q.db'}")
    ident = store.save(state=state, llm_analysis=analysis, decision=decision, final_judgment="direction=HOLD; score=0.2")
    assert ident == 1
    stored = store.get(symbol="BTCUSDT", limit=1)[0]
    assert stored["jev_direction"] == "HOLD"
    assert stored["jev_score"] == .2
    assert stored["final_judgment"] == "direction=HOLD; score=0.2"


@pytest.mark.asyncio
async def test_jev_client_uses_beatapi_questions_and_parses_noul_score():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"answers": {"pick_check": {"noul": 0.73}}})

    http = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    client = JEVClient(JEVSettings(base_url="https://jev", model="jev-test"), client=http)
    score = await client.decide(
        state_text='{"symbol":"BTCUSDT"}',
        instructions="Evaluate the nominated direction.",
        criteria={"true": "supported", "false": "unsupported"},
        question_name="pick_check",
    )
    await http.aclose()

    request = requests[0]
    payload = json.loads(request.content)
    assert request.url.path == "/v1/systemone"
    assert payload["model"] == "jev-test"
    assert payload["state"] == '{"symbol":"BTCUSDT"}'
    assert payload["questions"] == {
        "pick_check": {
            "type": "noul",
            "instructions": "Evaluate the nominated direction.",
            "criteria": {"true": "supported", "false": "unsupported"},
        }
    }
    assert score == .73


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("score", "expected_direction", "expected_confidence"),
    [(.649, "HOLD", .351), (.65, "SHORT", .65)],
)
async def test_jev_decision_applies_score_threshold(score, expected_direction, expected_confidence):
    class FakeJEVClient:
        settings = JEVSettings(base_url="https://jev", score_threshold=.65, question_name="pick_check")

        async def decide(self, **kwargs):
            self.request = kwargs
            return score

    client = FakeJEVClient()
    state = {"symbol": "BTCUSDT", "llm_analysis": {"direction_pick": "SHORT", "direction_rationale": "Momentum is weakening."}}
    decision = await JEVDecisionEngine(client).decide(symbol="BTCUSDT", state=state)

    assert decision.direction == expected_direction
    assert decision.confidence == pytest.approx(expected_confidence)
    assert decision.score == score
    assert client.request["question_name"] == "pick_check"
    assert "SHORT" in client.request["instructions"]
    assert "Momentum is weakening." in client.request["instructions"]
    assert json.loads(client.request["state_text"]) == state


def test_prediction_store_migrates_existing_database(tmp_path):
    database_path = tmp_path / "legacy.db"
    with sqlite3.connect(database_path) as conn:
        conn.execute("""CREATE TABLE predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL, state_snapshot TEXT NOT NULL,
            llm_analysis TEXT NOT NULL, jev_model TEXT NOT NULL,
            jev_direction TEXT NOT NULL, jev_confidence REAL NOT NULL,
            horizon TEXT NOT NULL)""")

    store = PredictionStore(f"sqlite:///{database_path}")
    with store._connect() as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(predictions)")}
    assert {"jev_score", "final_judgment"} <= columns
