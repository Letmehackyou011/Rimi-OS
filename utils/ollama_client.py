"""Validated Ollama HTTP client shared by the API, CLI, and web console."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, Field, field_validator


class OllamaConnection(BaseModel):
    endpoint: str = "http://127.0.0.1:11434"
    model: str = "mistral"
    timeout_seconds: int = Field(default=300, ge=5, le=600)

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        parts = urlsplit(value.strip().rstrip("/"))
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError("endpoint must be an http(s) URL with a hostname or IP")
        if parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("endpoint cannot contain credentials, query parameters, or fragments")
        if parts.path not in {"", "/"}:
            raise ValueError("endpoint must contain only scheme, host, and optional port")
        return urlunsplit((parts.scheme, parts.netloc, "", "", "")).rstrip("/")

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 200 or any(char in value for char in "\r\n"):
            raise ValueError("model name is invalid")
        return value


def endpoint_from_host(host: str, port: int = 11434, scheme: str = "http") -> str:
    """Build an endpoint from the IP/DNS and port entered in the UI or CLI."""
    host = host.strip()
    if "://" in host:
        candidate = host
    else:
        candidate = f"{scheme}://{host}:{port}"
    return OllamaConnection(endpoint=candidate).endpoint


class OllamaClient:
    def __init__(self, connection: OllamaConnection):
        self.connection = connection

    async def models(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.connection.timeout_seconds, trust_env=False) as client:
            response = await client.get(f"{self.connection.endpoint}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])

    async def chat(
        self,
        messages: list[dict[str, str]],
        stream: bool = False,
        options: dict[str, int | float] | None = None,
        think: bool | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": self.connection.model, "messages": messages, "stream": stream}
        if options:
            payload["options"] = options
        if think is not None:
            payload["think"] = think
        async with httpx.AsyncClient(timeout=self.connection.timeout_seconds, trust_env=False) as client:
            response = await client.post(f"{self.connection.endpoint}/api/chat", json=payload)
            if response.is_error:
                raise RuntimeError(f"Ollama returned HTTP {response.status_code}: {response.text[:1000]}")
            return response.json()

    async def health(self) -> dict[str, Any]:
        models = await self.models()
        names = {item.get("name") for item in models}
        return {
            "status": "connected",
            "endpoint": self.connection.endpoint,
            "model": self.connection.model,
            "model_available": self.connection.model in names,
            "models": models,
        }
