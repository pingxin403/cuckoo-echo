"""AI Gateway client — LiteLLM wrapper with fallback and observability."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import structlog
from litellm import acompletion

from shared.config import get_settings

log = structlog.get_logger()


async def stream_chat_completion(
    messages: list[dict],
    tenant_llm_config: dict | None = None,
    thread_id: str | None = None,
    callbacks: list | None = None,
) -> AsyncIterator:
    """Stream chat completion with primary/fallback model routing.

    Args:
        messages: Chat messages in OpenAI format.
        tenant_llm_config: Per-tenant LLM config from tenants.llm_config JSONB,
            e.g. {"model": "deepseek-chat", "fallback_model": "qwen-plus", "temperature": 0.7}.
        thread_id: For Langfuse trace correlation.
        callbacks: LangChain/Langfuse callbacks.
    """
    settings = get_settings()
    config = tenant_llm_config or {}
    primary_model = config.get("model", settings.llm_primary_model)
    fallback_model = config.get("fallback_model", settings.llm_fallback_model)
    temperature = config.get("temperature", 0.7)
    timeout = settings.llm_fallback_timeout  # 3.0s

    try:
        response = await asyncio.wait_for(
            acompletion(
                model=primary_model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                temperature=temperature,
            ),
            timeout=timeout,
        )
        log.info("llm_primary_success", model=primary_model)
        return response
    except (asyncio.TimeoutError, Exception) as e:
        log.warning("llm_primary_failed", model=primary_model, error=str(e))
        response = await acompletion(
            model=fallback_model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            temperature=temperature,
        )
        log.info("llm_fallback_success", model=fallback_model)
        return response
