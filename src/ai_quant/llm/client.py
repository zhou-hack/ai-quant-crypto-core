from __future__ import annotations

import httpx

from ai_quant.config.settings import LLMSettings, get_settings


class LLMClientError(RuntimeError):
    pass


class LLMClient:
    """OpenAI-compatible client. Its configuration is independent of JEV."""

    def __init__(self, settings: LLMSettings | None = None, *, timeout: float = 30.0, client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings().llm
        self.timeout = timeout
        self._client = client

    async def chat(self, messages: list[dict], *, model: str | None = None, temperature: float = 0.2) -> str:
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self.timeout)
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        try:
            response = await client.post(f"{self.settings.base_url.rstrip('/')}/chat/completions", headers=headers,
                                         json={"model": model or self.settings.model, "messages": messages, "temperature": temperature})
            response.raise_for_status()
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMClientError(f"LLM request failed: {exc}") from exc
        finally:
            if owns:
                await client.aclose()
