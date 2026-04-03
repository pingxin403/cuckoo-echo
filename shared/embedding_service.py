"""Embedding Service wrapper (OpenAI Compatible API)."""
from __future__ import annotations

import structlog

log = structlog.get_logger()


class EmbeddingService:
    """Async embedding service using LiteLLM's OpenAI-compatible API."""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        try:
            from litellm import aembedding

            response = await aembedding(model=self.model, input=[text])
            return response.data[0]["embedding"]
        except Exception as e:
            log.error("embedding_failed", error=str(e))
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        try:
            from litellm import aembedding

            response = await aembedding(model=self.model, input=texts)
            return [item["embedding"] for item in response.data]
        except Exception as e:
            log.error("embedding_batch_failed", error=str(e))
            raise


def get_embedding_service() -> EmbeddingService:
    """Return a new EmbeddingService instance."""
    return EmbeddingService()
