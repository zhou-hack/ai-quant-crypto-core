from datetime import datetime, timezone

from ai_quant.config.settings import get_settings
from ai_quant.llm.analyzer import LLMAnalysis
from ai_quant.market.candles import Candle
from ai_quant.market.state import StateBuilder
from ai_quant.storage.database import PredictionStore
from ai_quant.jev.decision import JEVDecision


def test_config_keeps_llm_and_jev_separate(tmp_path):
    env = tmp_path / ".env"
    env.write_text("LLM_BASE_URL=https://llm\nLLM_API_KEY=l\nJEV_BASE_URL=https://jev\nJEV_API_KEY=j\nSYMBOLS=BTCUSDT,ETHUSDT\n", encoding="utf-8")
    settings = get_settings(env_file=env, yaml_file=tmp_path / "none.yaml")
    assert settings.llm.base_url != settings.jev.base_url
    assert settings.llm.api_key != settings.jev.api_key
    assert settings.symbols == ["BTCUSDT", "ETHUSDT"]


def test_state_builder_and_prediction_storage(tmp_path):
    candles = [Candle(timestamp=datetime.now(timezone.utc), open=i, high=i + 1, low=i - 1, close=i, volume=100 + i) for i in range(1, 20)]
    analysis = LLMAnalysis(trend=.7, fundamental=.5, risk=.2, event=.4, sentiment=.6, summary="ok")
    state = StateBuilder().build(symbol="BTCUSDT", candles=candles, llm_analysis=analysis)
    assert 0 <= state.llm_analysis.trend <= 1
    decision = JEVDecision(symbol="BTCUSDT", direction="HOLD", confidence=.8, model="jev-latest", timestamp=datetime.now(timezone.utc))
    store = PredictionStore(f"sqlite:///{tmp_path / 'q.db'}")
    ident = store.save(state=state, llm_analysis=analysis, decision=decision)
    assert ident == 1
    assert store.get(symbol="BTCUSDT", limit=1)[0]["jev_direction"] == "HOLD"
