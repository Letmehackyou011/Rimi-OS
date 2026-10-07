"""
Multi-Agent LLM Router with per-agent model assignment and automatic cascading fallback.
Each agent (Reconnaissance, Vulnerability Analysis, Exploitation, Reporting)
has an optimized model preference and cascading fallback chain.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from config.settings import settings
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

# Default priority fallback chains per agent
# Format: List of (provider, model_name)
DEFAULT_AGENT_CHAINS: Dict[str, List[Tuple[str, str]]] = {
    "reconnaissance": [
        ("gemini", "gemini-3-flash-preview"),
        ("gemini", "gemini-2.0-flash"),
        ("gemini", "gemini-3.5-flash"),
        ("ollama", "mistral"),
        ("ollama", "llama3"),
        ("openai", "gpt-4o-mini"),
    ],
    "vulnerability_analysis": [
        ("claude", "claude-3-5-sonnet-20241022"),
        ("gemini", "gemini-2.0-flash"),
        ("gemini", "gemini-3-flash-preview"),
        ("ollama", "mistral"),
        ("openai", "gpt-4o"),
    ],
    "exploitation": [
        ("openai", "gpt-4o"),
        ("claude", "claude-3-5-sonnet-20241022"),
        ("gemini", "gemini-2.0-flash"),
        ("gemini", "gemini-3-flash-preview"),
        ("ollama", "mistral"),
    ],
    "reporting": [
        ("gemini", "gemini-3-flash-preview"),
        ("claude", "claude-3-5-sonnet-20241022"),
        ("ollama", "mistral"),
        ("openai", "gpt-4o-mini"),
    ],
}


class AgentLLMRouter:
    """
    Routes agent prompt generation requests with resilient cascading fallback.
    If the requested or primary model fails, shifts to secondary and tertiary models automatically.
    """

    def __init__(self):
        self._cached_clients: Dict[Tuple[str, str], LLMClient] = {}

    def get_client(self, provider: str, model: str) -> LLMClient:
        key = (provider.lower(), model)
        if key not in self._cached_clients:
            self._cached_clients[key] = LLMClient(provider=provider, model=model)
        return self._cached_clients[key]

    def get_chain_for_agent(
        self,
        agent_name: str,
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
    ) -> List[Tuple[str, str]]:
        """
        Build an ordered fallback chain for an agent.
        If user explicitly selected a provider/model, it is prioritized at index 0.
        """
        base_chain = DEFAULT_AGENT_CHAINS.get(agent_name, [
            (settings.ACTIVE_LLM, settings.OLLAMA_MODEL),
            ("ollama", "mistral"),
        ])

        chain: List[Tuple[str, str]] = []

        if preferred_provider:
            pref_mod = preferred_model or settings.OLLAMA_MODEL
            chain.append((preferred_provider.lower(), pref_mod))

        for prov, mod in base_chain:
            if (prov.lower(), mod) not in chain:
                chain.append((prov.lower(), mod))

        return chain

    async def generate_for_agent(
        self,
        agent_name: str,
        prompt: str,
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
        on_fallback: Any | None = None,
    ) -> Dict[str, Any]:
        """
        Execute LLM generation across the agent's fallback chain.
        Returns:
            {
                "content": str,
                "provider_used": str,
                "model_used": str,
                "fallback_count": int,
                "attempts": List[Dict[str, Any]]
            }
        """
        chain = self.get_chain_for_agent(agent_name, preferred_provider, preferred_model)
        attempts = []

        for idx, (provider, model) in enumerate(chain):
            try:
                logger.info(f"[{agent_name}] Attempting model #{idx + 1}: {provider}/{model}")
                client = self.get_client(provider, model)
                content = await client.generate(prompt)

                # Check if response is valid non-empty text
                if content and len(content.strip()) > 0:
                    logger.info(f"[{agent_name}] Successfully generated with {provider}/{model}")
                    return {
                        "content": content,
                        "provider_used": provider,
                        "model_used": model,
                        "fallback_count": idx,
                        "attempts": attempts,
                    }
                else:
                    attempts.append({"provider": provider, "model": model, "error": "Empty response"})
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                logger.warning(f"[{agent_name}] {provider}/{model} failed: {err_msg}. Shifting to next model...")
                attempts.append({"provider": provider, "model": model, "error": err_msg})
                if on_fallback:
                    try:
                        on_fallback(agent_name, provider, model, err_msg)
                    except Exception:
                        pass

        # Final resilient template fallback if entire chain is exhausted
        logger.warning(f"[{agent_name}] All models in chain exhausted. Using resilient security template.")
        fallback_client = self.get_client("ollama", "template")
        template_content = await fallback_client.generate(prompt)
        return {
            "content": template_content,
            "provider_used": "offline_template",
            "model_used": "rule_based",
            "fallback_count": len(chain),
            "attempts": attempts,
        }


# Global router singleton
router = AgentLLMRouter()

def get_llm_router() -> AgentLLMRouter:
    return router
