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
        kwargs = {
            "model": primary_model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": temperature,
        }
        if settings.llm_api_key:
            kwargs["api_key"] = settings.llm_api_key
        if settings.llm_api_base:
            kwargs["api_base"] = settings.llm_api_base
        response = await asyncio.wait_for(
            acompletion(**kwargs),
            timeout=timeout,
        )
        log.info("llm_primary_success", model=primary_model)
        return response
    except (asyncio.TimeoutError, Exception) as e:
        log.warning("llm_primary_failed", model=primary_model, error=str(e))
        fallback_kwargs = {
            "model": fallback_model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": temperature,
        }
        if settings.llm_api_key:
            fallback_kwargs["api_key"] = settings.llm_api_key
        if settings.llm_api_base:
            fallback_kwargs["api_base"] = settings.llm_api_base
        response = await acompletion(**fallback_kwargs)
        log.info("llm_fallback_success", model=fallback_model)
        return response


async def vision_completion(image_url: str, user_text: str) -> str:
    """Call a Vision LLM to understand an image in context of user text.

    Uses OpenAI Vision API format with image_url content type.
    Returns the model's text description/response.
    """
    settings = get_settings()
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text or "请描述这张图片的内容"},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]
    try:
        kwargs = {
            "model": settings.vision_model,
            "messages": messages,
            "stream": False,
            "max_tokens": 300,
        }
        if settings.llm_api_key:
            kwargs["api_key"] = settings.llm_api_key
        if settings.llm_api_base:
            kwargs["api_base"] = settings.llm_api_base

        response = await acompletion(**kwargs)
        return response.choices[0].message.content or ""
    except Exception as e:
        log.warning("vision_completion_failed", error=str(e))
        raise
