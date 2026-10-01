"""LLM and Ollama runtime configuration endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config.settings import settings
from utils.ollama_client import OllamaClient, OllamaConnection, endpoint_from_host
from utils.runtime_config import update_runtime_config

router = APIRouter()


class OllamaConnectionRequest(BaseModel):
    host: str = Field(min_length=1, max_length=253)
    port: int = Field(default=11434, ge=1, le=65535)
    model: str = Field(min_length=1, max_length=200)


class OllamaChatRequest(BaseModel):
    endpoint: str | None = None
    model: str | None = None
    messages: list[dict[str, str]] = Field(min_length=1, max_length=100)
    num_ctx: int = Field(default=32768, ge=4096, le=131072)
    temperature: float = Field(default=0.2, ge=0, le=2)
    think: bool = False


class LlmConfigUpdate(BaseModel):
    context_window: int | None = Field(default=None, ge=4096, le=131072)
    max_tokens: int | None = Field(default=None, ge=512, le=32768)
    claude_api_key: str | None = Field(default=None, max_length=500)
    gemini_api_key: str | None = Field(default=None, max_length=500)
    openai_api_key: str | None = Field(default=None, max_length=500)
    nvidia_api_key: str | None = Field(default=None, max_length=500)


@router.get("/llm")
async def get_llm_config() -> dict:
    return {
        "active_provider": settings.ACTIVE_LLM,
        "ollama_endpoint": settings.OLLAMA_ENDPOINT,
        "ollama_model": settings.OLLAMA_MODEL,
        "claude_model": settings.CLAUDE_MODEL,
        "gemini_model": settings.GEMINI_MODEL,
        "openai_model": settings.OPENAI_MODEL,
        "max_tokens": settings.MAX_TOKENS,
        "context_window": settings.CONTEXT_WINDOW,
        "claude_key_configured": bool(settings.CLAUDE_API_KEY),
        "gemini_key_configured": bool(settings.GEMINI_API_KEY),
        "openai_key_configured": bool(settings.OPENAI_API_KEY),
        "nvidia_key_configured": bool(settings.NVIDIA_API_KEY),
    }


@router.put("/llm")
async def update_llm_config(request: LlmConfigUpdate) -> dict:
    if request.context_window is not None:
        settings.CONTEXT_WINDOW = request.context_window
        update_runtime_config(context_window=request.context_window)
    if request.max_tokens is not None:
        settings.MAX_TOKENS = request.max_tokens
        update_runtime_config(max_tokens=request.max_tokens)
    for field, setting_name in {
        "claude_api_key": "CLAUDE_API_KEY",
        "gemini_api_key": "GEMINI_API_KEY",
        "openai_api_key": "OPENAI_API_KEY",
        "nvidia_api_key": "NVIDIA_API_KEY",
    }.items():
        value = getattr(request, field)
        if value:
            setattr(settings, setting_name, value)
    return await get_llm_config()


@router.post("/ollama/test")
async def test_ollama_connection(request: OllamaConnectionRequest) -> dict:
    try:
        connection = OllamaConnection(
            endpoint=endpoint_from_host(request.host, request.port),
            model=request.model,
        )
        return await OllamaClient(connection).health()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Ollama connection failed: {exc}") from exc


@router.put("/ollama")
async def update_ollama_connection(request: OllamaConnectionRequest) -> dict:
    try:
        endpoint = endpoint_from_host(request.host, request.port)
        connection = OllamaConnection(endpoint=endpoint, model=request.model)
        update_runtime_config(ollama_endpoint=connection.endpoint, ollama_model=connection.model)
        settings.OLLAMA_ENDPOINT = connection.endpoint
        settings.OLLAMA_MODEL = connection.model
        return {
            "status": "saved",
            "ollama_endpoint": connection.endpoint,
            "ollama_model": connection.model,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Ollama connection: {exc}") from exc


@router.get("/ollama/models")
async def list_ollama_models(endpoint: str | None = None) -> dict:
    try:
        connection = OllamaConnection(
            endpoint=endpoint or settings.OLLAMA_ENDPOINT,
            model=settings.OLLAMA_MODEL,
        )
        return {"models": await OllamaClient(connection).models()}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama model discovery failed: {exc}") from exc


@router.post("/ollama/chat")
async def ollama_chat(request: OllamaChatRequest) -> dict:
    try:
        connection = OllamaConnection(
            endpoint=request.endpoint or settings.OLLAMA_ENDPOINT,
            model=request.model or settings.OLLAMA_MODEL,
        )
        return await OllamaClient(connection).chat(
            request.messages,
            options={"num_ctx": request.num_ctx, "temperature": request.temperature},
            think=request.think,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama request failed: {exc}") from exc
