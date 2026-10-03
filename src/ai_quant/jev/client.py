from __future__ import annotations

import math

import httpx

from ai_quant.config.settings import JEVSettings, get_settings


class JEVClientError(RuntimeError):
    pass


class JEVClient:
    """Independent HTTP client for the JEV decision service."""

    def __init__(self, settings: JEVSettings | None = None, *, timeout: float | None = None,
                 client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings().jev
        self.timeout = getattr(self.settings, "timeout_seconds", 30.0) if timeout is None else timeout
        self._client = client

    async def models(self) -> list[dict]:
        return await self._request("GET", "/v1/models")

    async def decide(
        self,
        *,
        state_text: str,
        instructions: str,
        criteria: dict,
        question_name: str = "direction_appropriateness",
        model: str | None = None,
    ) -> float:
        """Return the JEV noul score in [0, 1]."""
        payload = {
            "model": model or self.settings.model,
            "state": state_text,
            "questions": {
                question_name: {
                    "type": "noul",
                    "instructions": instructions,
                    "criteria": criteria,
                }
            },
        }
        result = await self._request("POST", "/v1/systemone", json=payload)
        if not isinstance(result, dict):
            raise JEVClientError("JEV response must be a JSON object")
        try:
            raw_score = result["answers"][question_name]["noul"]
            if isinstance(raw_score, bool):
                raise ValueError("boolean is not a score")
            score = float(raw_score)
        except (KeyError, TypeError, ValueError) as exc:
            raise JEVClientError(f"JEV response did not contain answers.{question_name}.noul") from exc
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise JEVClientError("JEV noul score must be a finite number in [0, 1]")
        return score

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
