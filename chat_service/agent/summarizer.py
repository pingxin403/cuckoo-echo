"""LLM Summarizer — compresses long conversation history into concise summaries."""
from __future__ import annotations

import structlog

log = structlog.get_logger()

SUMMARIZE_SYSTEM_PROMPT = (
    "请将以下对话历史压缩为简洁的摘要，保留关键信息和用户意图。"
    "摘要应包含：用户的核心问题、已解决的事项、待处理的事项、重要的上下文信息。"
    "用中文输出，不超过 500 字。"
)


class LLMSummarizer:
    """Summarizes conversation history using LLM."""

    async def summarize(self, messages: list[dict]) -> str:
        """Compress messages into a concise summary.

        Returns empty string on failure (degrades to no compression).
        """
        try:
            from ai_gateway.client import stream_chat_completion

            # Build the summarization prompt
            conversation = "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')}"
                for m in messages
                if m.get("content")
            )
            llm_messages = [
                {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
                {"role": "user", "content": conversation},
            ]

            response = await stream_chat_completion(
                messages=llm_messages,
                tenant_llm_config={"temperature": 0.3},
            )

            # Collect full response
            result = ""
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    result += delta.content

            log.info("summary_generated", original_count=len(messages), summary_len=len(result))
            return result.strip()
        except Exception as e:
            log.warning("summarizer_failed", error=str(e), hint="Degrading to no compression")
            return ""
