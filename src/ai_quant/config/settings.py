"""Application configuration with deliberately separate LLM and JEV settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class LLMSettings(BaseModel):
    base_url: str = "https://example.com/v1"
    api_key: str = ""
    model: str = ""


class JEVSettings(BaseModel):
    base_url: str = "https://example.com"
    api_key: str = ""
    model: str = "jev-latest"


class MarketSettings(BaseModel):
    base_url: str = "https://api.binance.com"
    api_key: str = ""
    interval: str = "1h"
    intervals: list[str] = Field(default_factory=lambda: ["1h", "4h"])
    lookback_days: int = Field(default=7, ge=1, le=30)
    limit: int = 100
    max_symbols: int = 5


class Settings(BaseModel):
    llm: LLMSettings = Field(default_factory=LLMSettings)
    jev: JEVSettings = Field(default_factory=JEVSettings)
    market: MarketSettings = Field(default_factory=MarketSettings)
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./data/quant.db"
    symbols: list[str] = Field(default_factory=lambda: ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"])

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, value: list[str]) -> list[str]:
        symbols = [s.strip().upper() for s in value if s.strip()]
        if not symbols:
            raise ValueError("at least one symbol is required")
        if len(symbols) > 5:
            raise ValueError("a maximum of 5 symbols is supported")
        return list(dict.fromkeys(symbols))


def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def get_settings(*, env_file: str | Path = ".env", yaml_file: str | Path = "config/config.yaml") -> Settings:
    """Build settings from YAML defaults, dotenv values, then process environment."""
    dotenv = _load_dotenv(Path(env_file))
    env = {**dotenv, **{k: v for k, v in os.environ.items() if k in {
        "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL", "JEV_BASE_URL", "JEV_API_KEY", "JEV_MODEL",
        "MARKET_DATA_BASE_URL", "MARKET_DATA_API_KEY", "APP_ENV", "LOG_LEVEL", "DATABASE_URL", "SYMBOLS",
    }}}
    raw = _yaml(Path(yaml_file))
    market = dict(raw.get("market", {}))
    market.update({"base_url": env.get("MARKET_DATA_BASE_URL", market.get("base_url", "https://api.binance.com")),
                   "api_key": env.get("MARKET_DATA_API_KEY", market.get("api_key", ""))})
    symbols = env.get("SYMBOLS")
    return Settings(
        llm=LLMSettings(base_url=env.get("LLM_BASE_URL", "https://example.com/v1"), api_key=env.get("LLM_API_KEY", ""), model=env.get("LLM_MODEL", "")),
        jev=JEVSettings(base_url=env.get("JEV_BASE_URL", "https://example.com"), api_key=env.get("JEV_API_KEY", ""), model=env.get("JEV_MODEL", "jev-latest")),
        market=MarketSettings(**market),
        app_env=env.get("APP_ENV", "development"), log_level=env.get("LOG_LEVEL", "INFO"),
        database_url=env.get("DATABASE_URL", "sqlite:///./data/quant.db"),
        symbols=(symbols.split(",") if symbols is not None else Settings().symbols),
    )
