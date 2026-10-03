from __future__ import annotations

import httpx

from ai_quant.config.settings import JEVSettings, get_settings


class JEVClientError(RuntimeError):
    pass


class JEVClient:
    """Independent HTTP client for the JEV decision service."""

    def __init__(self, settings: JEVSettings | None = None, *, timeout: float = 30.0,
                 client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings().jev
        self.timeout = timeout
        self._client = client

    async def models(self) -> list[dict]:
        return await self._request("GET", "/v1/models")

    async def decide(self, *, state: dict, question: dict, model: str | None = None) -> dict:
        payload = {"model": model or self.settings.model, "state": state, "question": question}
        result = await self._request("POST", "/v1/systemone", json=payload)
        if not isinstance(result, dict):
            raise JEVClientError("JEV response must be a JSON object")
        return result

    async def _request(self, method: str, path: str, **kwargs):
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self.timeout)
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        try:
            response = await client.request(method, f"{self.settings.base_url.rstrip('/')}{path}", headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise JEVClientError(f"JEV request failed: {exc}") from exc
        finally:
            if owns:
                await client.aclose()
