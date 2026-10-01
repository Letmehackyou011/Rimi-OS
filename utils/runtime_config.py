"""Persist non-secret runtime overrides such as the Ollama endpoint."""

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
    return current


_runtime = load_runtime_config()
if _runtime.get("ollama_endpoint"):
    settings.OLLAMA_ENDPOINT = _runtime["ollama_endpoint"]
if _runtime.get("ollama_model"):
    settings.OLLAMA_MODEL = _runtime["ollama_model"]
if _runtime.get("context_window"):
    settings.CONTEXT_WINDOW = _runtime["context_window"]
if _runtime.get("max_tokens"):
    settings.MAX_TOKENS = _runtime["max_tokens"]
