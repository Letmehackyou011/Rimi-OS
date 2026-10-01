"""LangChain-backed provider adapter used by the security agents."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from config.settings import settings
from utils import runtime_config  # noqa: F401 - applies persisted runtime overrides


class LLMClient:
    """Small provider-neutral interface for agent prompts."""

    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = (provider or settings.ACTIVE_LLM).lower()
        self.model_name = model or self._default_model(self.provider)
        self.model = self._build_model()

    def _default_model(self, provider: str) -> str:
        return {
            "ollama": settings.OLLAMA_MODEL,
            "claude": settings.CLAUDE_MODEL,
            "gemini": settings.GEMINI_MODEL,
            "openai": settings.OPENAI_MODEL,
            "nvidia": settings.OPENAI_MODEL,
        }.get(provider, settings.OLLAMA_MODEL)

    def _build_model(self) -> Any:
        if self.provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                base_url=settings.OLLAMA_ENDPOINT,
                model=self.model_name,
                temperature=0,
            )
        if self.provider == "claude":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=self.model_name,
                anthropic_api_key=settings.CLAUDE_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                temperature=0,
            )
        if self.provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=settings.GEMINI_API_KEY,
                max_output_tokens=settings.MAX_TOKENS,
                temperature=0,
            )
        if self.provider in {"openai", "nvidia"}:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=self.model_name,
                api_key=(settings.NVIDIA_API_KEY if self.provider == "nvidia" else settings.OPENAI_API_KEY),
                base_url=settings.NVIDIA_ENDPOINT if self.provider == "nvidia" else None,
                max_tokens=settings.MAX_TOKENS,
                temperature=0,
            )
        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def generate(self, prompt: str) -> str:
        """Invoke a LangChain chat model and return its text content."""
        response = await self.model.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        if isinstance(content, list):
            return "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        return str(content)


def get_llm_client(provider: str | None = None, model: str | None = None) -> LLMClient:
    return LLMClient(provider, model)
