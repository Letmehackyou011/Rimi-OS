"""Application settings loaded from environment variables and an optional .env file."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def _env_origins() -> list[str]:
    value = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:8080,"
        "http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:8080",
    )
    return [origin.strip() for origin in value.split(",") if origin.strip()]


@dataclass
class Settings:
    DEBUG: bool = field(default_factory=lambda: _env_bool("DEBUG", True))
    HOST: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    PORT: int = field(default_factory=lambda: _env_int("PORT", 8000))
    DATABASE_URL: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://localhost:5432/security_os"
        )
    )
    DATABASE_ECHO: bool = field(
        default_factory=lambda: _env_bool("DATABASE_ECHO", False)
    )

    ACTIVE_LLM: str = field(default_factory=lambda: os.getenv("ACTIVE_LLM", "ollama"))
    OLLAMA_ENDPOINT: str = field(
        default_factory=lambda: os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
    )
    OLLAMA_MODEL: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "mistral")
    )
    CLAUDE_API_KEY: str = field(default_factory=lambda: os.getenv("CLAUDE_API_KEY", ""))
    CLAUDE_MODEL: str = field(
        default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    )
    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    GEMINI_MODEL: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    )
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    OPENAI_MODEL: str = field(
        default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4")
    )
    NVIDIA_API_KEY: str = field(default_factory=lambda: os.getenv("NVIDIA_API_KEY", ""))
    NVIDIA_ENDPOINT: str = field(
        default_factory=lambda: os.getenv(
            "NVIDIA_ENDPOINT", "https://integrate.api.nvidia.com/v1"
        )
    )

    MAX_TOKENS: int = field(default_factory=lambda: _env_int("MAX_TOKENS", 8000))
    CONTEXT_WINDOW: int = field(
        default_factory=lambda: _env_int("CONTEXT_WINDOW", 32000)
    )
    AGENT_TIMEOUT: int = field(default_factory=lambda: _env_int("AGENT_TIMEOUT", 300))
    MAX_RETRIES: int = field(default_factory=lambda: _env_int("MAX_RETRIES", 3))

    SECRET_KEY: str = field(
        default_factory=lambda: os.getenv(
            "SECRET_KEY", "your-secret-key-change-in-production"
        )
    )
    ALGORITHM: str = field(default_factory=lambda: os.getenv("ALGORITHM", "HS256"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = field(
        default_factory=lambda: _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    )
    ENCRYPTION_KEY: str = field(default_factory=lambda: os.getenv("ENCRYPTION_KEY", ""))

    REPORT_FORMAT: str = field(
        default_factory=lambda: os.getenv("REPORT_FORMAT", "pdf")
    )
    REPORT_STORAGE_PATH: str = field(
        default_factory=lambda: os.getenv("REPORT_STORAGE_PATH", "./reports")
    )
    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    LOG_FILE: str = field(default_factory=lambda: os.getenv("LOG_FILE", "app.log"))
    ALLOWED_ORIGINS: list[str] = field(default_factory=_env_origins)
    RUNTIME_CONFIG_PATH: str = field(
        default_factory=lambda: os.getenv(
            "RUNTIME_CONFIG_PATH", "./runtime-config.json"
        )
    )


settings = Settings()


def validate_llm_config(config: Settings | None = None) -> bool:
    """Return whether the selected provider has the required configuration."""
    config = config or settings
    provider = config.ACTIVE_LLM.strip().lower()
    required_keys = {
        "claude": config.CLAUDE_API_KEY,
        "gemini": config.GEMINI_API_KEY,
        "openai": config.OPENAI_API_KEY,
        "nvidia": config.NVIDIA_API_KEY,
    }
    return provider == "ollama" or (
        provider in required_keys and bool(required_keys[provider])
    )
