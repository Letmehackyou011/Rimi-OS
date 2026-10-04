"""LangChain-backed provider adapter with native SDK and direct HTTP fallbacks for all providers."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage

from config.settings import settings
from utils import runtime_config  # noqa: F401 - applies persisted runtime overrides

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Offline / template fallback used when ALL LLM paths fail
# ---------------------------------------------------------------------------
_OFFLINE_RESPONSE = json.dumps({
    "summary": "Automated security reconnaissance completed based on network evidence.",
    "vulnerabilities": [],
    "verified": False,
    "executive_summary": "Automated assessment completed. Review tool evidence and findings.",
    "vulnerability_count": 0,
    "overall_risk_score": 0.0,
    "recommendations": [
        "Review open ports and exposed services",
        "Ensure Web Application Firewall is enabled",
        "Configure Google Gemini or Ollama service for deep AI reasoning",
    ],
    "next_steps": "Configure an AI model and rerun the scan for deep analysis.",
})


class LLMClient:
    """Provider-neutral async LLM client with automatic fallback chain."""

    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = (provider or settings.ACTIVE_LLM).lower()
        self.model_name = model or self._default_model(self.provider)
        self.model = self._build_model()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _default_model(self, provider: str) -> str:
        return {
            "ollama": settings.OLLAMA_MODEL,
            "claude": settings.CLAUDE_MODEL,
            "gemini": settings.GEMINI_MODEL,
            "openai": settings.OPENAI_MODEL,
            "nvidia": settings.OPENAI_MODEL,
        }.get(provider, settings.OLLAMA_MODEL)

    def _build_model(self) -> Any | None:
        """Build a LangChain chat model if supported. Returns None to use native SDK/HTTP."""
        # Ollama and Gemini: handled directly via native SDK/REST for guaranteed reliability
        if self.provider in ("ollama", "gemini"):
            return None

        if self.provider == "claude":
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model=self.model_name,
                    anthropic_api_key=settings.CLAUDE_API_KEY,
                    max_tokens=settings.MAX_TOKENS,
                    temperature=0,
                )
            except Exception as e:
                logger.warning(f"Could not load ChatAnthropic: {e}")

        elif self.provider in {"openai", "nvidia"}:
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=self.model_name,
                    api_key=(
                        settings.NVIDIA_API_KEY
                        if self.provider == "nvidia"
                        else settings.OPENAI_API_KEY
                    ),
                    base_url=settings.NVIDIA_ENDPOINT if self.provider == "nvidia" else None,
                    max_tokens=settings.MAX_TOKENS,
                    temperature=0,
                )
            except Exception as e:
                logger.warning(f"Could not load ChatOpenAI: {e}")

        return None

    # ------------------------------------------------------------------
    # Generation — Native SDK + REST + Cascade Fallback
    # ------------------------------------------------------------------

    async def generate(self, prompt: str) -> str:
        """Generate a response with automatic fallback chain."""

        # 1. Native Google Gemini execution (SDK + REST)
        if self.provider == "gemini":
            result = await self._gemini_call(prompt)
            if result is not None and len(result.strip()) > 0:
                return result
            logger.warning("[gemini] Gemini invocation did not return content. Falling back...")

        # 2. Native Ollama execution (REST)
        if self.provider == "ollama":
            result = await self._ollama_http(prompt)
            if result is not None and len(result.strip()) > 0:
                return result

        # 3. LangChain chat model if initialized (Claude, OpenAI, Nvidia)
        if self.model is not None:
            try:
                response = await self.model.ainvoke([HumanMessage(content=prompt)])
                content = response.content
                if isinstance(content, list):
                    return "".join(
                        item.get("text", "") if isinstance(item, dict) else str(item)
                        for item in content
                    )
                if content and len(str(content).strip()) > 0:
                    return str(content)
            except Exception as e:
                logger.warning(f"[{self.provider}] LangChain ainvoke failed: {e}")

        # 4. Direct OpenAI REST fallback
        if self.provider in ("openai", "nvidia"):
            result = await self._openai_call(prompt)
            if result is not None and len(result.strip()) > 0:
                return result

        # 5. Offline structured template
        logger.info(f"[{self.provider}] All LLM paths exhausted — using offline security template.")
        return _OFFLINE_RESPONSE

    async def _gemini_call(self, prompt: str) -> str | None:
        """Execute Google Gemini using either google.generativeai SDK or direct REST API."""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.warning("[gemini] GEMINI_API_KEY is not configured in settings or .env")
            return None

        model_name = self.model_name or "gemini-2.0-flash"
        if not model_name.startswith("gemini-"):
            model_name = "gemini-2.0-flash"

        # Method A: Google Generative AI SDK
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            gmodel = genai.GenerativeModel(model_name)
            resp = await asyncio.to_thread(gmodel.generate_content, prompt)
            if resp and resp.text:
                logger.info(f"[gemini] Successfully generated with SDK model {model_name}")
                return resp.text
        except Exception as e:
            logger.warning(f"[gemini] SDK call failed: {e}. Trying direct Google REST API...")

        # Method B: Direct Google Generative Language REST API (httpx)
        try:
            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": min(settings.MAX_TOKENS, 8192)
                }
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)
                        if text:
                            logger.info(f"[gemini] Successfully generated via REST API ({model_name})")
                            return text
                else:
                    logger.warning(f"[gemini] REST API returned HTTP {res.status_code}: {res.text[:300]}")
        except Exception as e:
            logger.warning(f"[gemini] REST API call failed: {e}")

        return None

    async def _ollama_http(self, prompt: str) -> str | None:
        """Call Ollama REST API directly with httpx (no LangChain)."""
        endpoint = settings.OLLAMA_ENDPOINT.rstrip("/")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=120.0) as client:
                gen_payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                }
                resp = await client.post(f"{endpoint}/api/generate", json=gen_payload)
                if resp.status_code == 200:
                    return resp.json().get("response", "")

                chat_payload = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }
                chat_resp = await client.post(f"{endpoint}/api/chat", json=chat_payload)
                if chat_resp.status_code == 200:
                    return chat_resp.json().get("message", {}).get("content", "")
        except Exception as e:
            logger.warning(f"[ollama] Direct HTTP request failed: {e}")
        return None

    async def _openai_call(self, prompt: str) -> str | None:
        """Direct REST fallback for OpenAI."""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            return None
        try:
            import httpx
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": self.model_name or "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": settings.MAX_TOKENS,
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"[openai] REST call failed: {e}")
        return None


def get_llm_client(provider: str | None = None, model: str | None = None) -> LLMClient:
    return LLMClient(provider, model)
