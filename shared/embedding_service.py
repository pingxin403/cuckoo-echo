"""Embedding Service wrapper (LiteLLM — supports OpenAI, Ollama, etc.)."""
from __future__ import annotations

import structlog

from shared.config import get_settings

log = structlog.get_logger()


class EmbeddingService:
    """Async embedding service using LiteLLM's OpenAI-compatible API."""

    def __init__(self, model: str | None = None):
        settings = get_settings()
        self.model = model or settings.embedding_model
        # LiteLLM needs api_base for Ollama routing
        self.api_base = settings.llm_api_base or None
        self.api_key = settings.llm_api_key or None

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        try:
            from litellm import aembedding

            kwargs: dict = {"model": self.model, "input": [text]}
            if self.api_base:
                kwargs["api_base"] = self.api_base
            if self.api_key:
                kwargs["api_key"] = self.api_key
            response = await aembedding(**kwargs)
            return response.data[0]["embedding"]
        except Exception as e:
            log.error("embedding_failed", model=self.model, error=str(e))
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        try:
            from litellm import aembedding

            kwargs: dict = {"model": self.model, "input": texts}
            if self.api_base:
                kwargs["api_base"] = self.api_base
            if self.api_key:
                kwargs["api_key"] = self.api_key
            response = await aembedding(**kwargs)
            return [item["embedding"] for item in response.data]
        except Exception as e:
            log.error("embedding_batch_failed", model=self.model, error=str(e))
            raise


def get_embedding_service() -> EmbeddingService:
    """Return a new EmbeddingService instance."""
    return EmbeddingService()
