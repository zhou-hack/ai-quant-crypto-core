from __future__ import annotations

from datetime import datetime, timezone
import httpx

from ai_quant.config.settings import MarketSettings
from .candles import Candle


class MarketDataError(RuntimeError):
    pass


class MarketDataClient:
    def __init__(self, settings: MarketSettings, *, timeout: float = 30.0, client: httpx.AsyncClient | None = None):
        self.settings, self.timeout, self._client = settings, timeout, client

    async def candles(self, symbol: str, *, interval: str | None = None, limit: int | None = None) -> list[Candle]:
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self.timeout)
        try:
            response = await client.get(f"{self.settings.base_url.rstrip('/')}/api/v3/klines", params={"symbol": symbol.upper(), "interval": interval or self.settings.interval, "limit": limit or self.settings.limit})
            response.raise_for_status()
            result = []
            for row in response.json():
                result.append(Candle(timestamp=datetime.fromtimestamp(float(row[0]) / 1000, tz=timezone.utc), open=float(row[1]), high=float(row[2]), low=float(row[3]), close=float(row[4]), volume=float(row[5])))
            return result
        except (httpx.HTTPError, ValueError, TypeError, IndexError, KeyError) as exc:
            raise MarketDataError(f"market data request failed: {exc}") from exc
        finally:
            if owns:
                await client.aclose()

    async def historical_data(self, symbols: list[str], *, intervals: list[str] | None = None, lookback_days: int = 7) -> dict[str, dict[str, list[Candle]]]:
        """Fetch bounded recent history for Hermes research; no trading operations are exposed."""
        if len(symbols) > 5:
            raise ValueError("a maximum of 5 symbols is supported")
        selected_intervals = intervals or [self.settings.interval]
        limits = {"1m": 1440, "5m": 288, "15m": 96, "1h": 24, "4h": 6, "1d": 1}
        result: dict[str, dict[str, list[Candle]]] = {}
        for symbol in symbols:
            result[symbol.upper()] = {}
            for interval in selected_intervals:
                if interval not in limits:
                    raise ValueError(f"unsupported interval: {interval}")
                per_day = limits[interval]
                result[symbol.upper()][interval] = await self.candles(symbol, interval=interval, limit=min(per_day * lookback_days, 1000))
        return result
