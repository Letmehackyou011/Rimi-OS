"""Persist runtime overrides such as provider, API keys, and endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.settings import settings

_PATH = Path(getattr(settings, "RUNTIME_CONFIG_PATH", "./runtime-config.json"))


def load_runtime_config() -> dict[str, Any]:
    if not _PATH.exists():
        return {}
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def update_runtime_config(**values: Any) -> dict[str, Any]:
    current = load_runtime_config()
    current.update(values)
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")

    # Apply immediately to settings
    _apply_to_settings(current)
    return current


def _apply_to_settings(cfg: dict[str, Any]) -> None:
    if cfg.get("active_provider"):
        settings.ACTIVE_LLM = cfg["active_provider"]
    if cfg.get("ollama_endpoint"):
        settings.OLLAMA_ENDPOINT = cfg["ollama_endpoint"]
    if cfg.get("ollama_model"):
        settings.OLLAMA_MODEL = cfg["ollama_model"]
    if cfg.get("gemini_api_key"):
        settings.GEMINI_API_KEY = cfg["gemini_api_key"]
    if cfg.get("gemini_model"):
        settings.GEMINI_MODEL = cfg["gemini_model"]
    if cfg.get("claude_api_key"):
        settings.CLAUDE_API_KEY = cfg["claude_api_key"]
    if cfg.get("openai_api_key"):
        settings.OPENAI_API_KEY = cfg["openai_api_key"]
    if cfg.get("nvidia_api_key"):
        settings.NVIDIA_API_KEY = cfg["nvidia_api_key"]
    if cfg.get("context_window"):
        settings.CONTEXT_WINDOW = cfg["context_window"]
    if cfg.get("max_tokens"):
        settings.MAX_TOKENS = cfg["max_tokens"]


# Apply on module import
_apply_to_settings(load_runtime_config())
