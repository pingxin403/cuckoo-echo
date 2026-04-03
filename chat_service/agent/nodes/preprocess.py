"""Preprocess node — multimodal handling (ASR + image + Vision LLM) + summary compression."""
from __future__ import annotations

import time

import structlog

from chat_service.agent.state import AgentState

log = structlog.get_logger()

SUMMARIZE_THRESHOLD = 50

# Placeholder services — wired at startup
asr_client = None
oss_client = None
llm_summarizer = None
vision_client = None  # Wired at startup if vision model configured


async def _describe_image(signed_url: str, user_text: str) -> str | None:
    """Call Vision LLM to describe/understand an image in context of user text."""
    if not vision_client:
        return None
    try:
        description = await vision_client.vision_completion(signed_url, user_text)
        return description
    except Exception as e:
        log.warning("vision_llm_failed", error=str(e), hint="Falling back to text-only")
        return None


async def preprocess_node(state: AgentState) -> AgentState:
    """Preprocess: handle audio/image media, trigger summary compression if needed."""
    messages = list(state.get("messages", []))
    media_urls = list(state.get("media_urls", []))

    # Summary compression
    if len(messages) >= SUMMARIZE_THRESHOLD and llm_summarizer:
        summary = await llm_summarizer.summarize(messages)
        state = {**state, "messages": [], "summary": summary}
        messages = []
        log.info("summary_compressed", thread_id=state.get("thread_id"))

    # Process media if present in last message
    if messages:
        last_msg = messages[-1]
        media = last_msg.get("media", [])
        image_descriptions: list[str] = []

        for item in media:
            if item.get("type") == "audio" and asr_client:
                agent_start = time.monotonic()
                try:
                    result = await asr_client.transcribe(item["oss_url"])
                    asr_done = time.monotonic()
                    handoff_ms = (asr_done - agent_start) * 1000
                    log.info("asr_handoff", handoff_ms=handoff_ms)
                    if handoff_ms > 500:
                        log.warning("asr_handoff_slow", handoff_ms=handoff_ms)
                    # Replace message content with transcript
                    last_msg = {**last_msg, "content": result.get("text", "")}
                    media_urls.append({"type": "audio", "url": item["oss_url"]})
                except Exception as e:
                    log.error("asr_preprocess_failed", error=str(e))

            elif item.get("type") == "image":
                if oss_client:
                    signed_url = await oss_client.get_signed_url(item["oss_url"])
                else:
                    signed_url = item["oss_url"]
                media_urls.append({"type": "image", "url": signed_url})

                # Vision LLM: understand image content
                user_text = last_msg.get("content", "")
                description = await _describe_image(signed_url, user_text)
                if description:
                    image_descriptions.append(description)

        # Augment message content with image descriptions
        if image_descriptions:
            original_content = last_msg.get("content", "")
            augmented = original_content
            for desc in image_descriptions:
                augmented += f"\n[图片内容: {desc}]"
            last_msg = {**last_msg, "content": augmented}

        if media:
            messages = messages[:-1] + [last_msg]

    return {**state, "messages": messages, "media_urls": media_urls}
