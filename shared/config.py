"""Centralized configuration via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/cuckoo"
    database_ro_url: str = ""  # Read-replica DSN for Admin queries; empty = fallback to primary

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Milvus
    milvus_uri: str = "http://localhost:19530"

    # MinIO / OSS
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "cuckoo-echo"

    # LLM
    llm_primary_model: str = "deepseek-chat"
    llm_fallback_model: str = "qwen-plus"
    llm_fallback_timeout: float = 30.0
    llm_api_key: str = ""  # e.g. "sk-..." for OpenAI, "ollama" for local Ollama
    llm_api_base: str = ""  # e.g. "http://host.docker.internal:11434" for Ollama

    # Langfuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    # Admin JWT
    admin_jwt_secret: str = "change-me-in-production"

    def validate_jwt_secret(self) -> None:
        """Raise if JWT secret is still the default value in non-dev environments."""
        if self.environment != "development" and self.admin_jwt_secret == "change-me-in-production":
            raise ValueError("ADMIN_JWT_SECRET must be changed from default in non-development environments")

    # App
    environment: str = "development"
    log_level: str = "INFO"

    # Tool Service
    tool_mock_mode: bool = True
    tool_order_service_url: str = ""

    # ASR (Speech-to-Text)
    asr_mode: str = "remote"  # "local" (faster-whisper) or "remote" (OpenAI-compatible API)
    asr_api_url: str = "http://localhost:9000"
    asr_model: str = "whisper-1"

    # Embedding
    embedding_model: str = "text-embedding-3-small"  # e.g. "ollama/qwen3-embedding" for local Ollama
    embedding_dim: int = 4096  # Vector dimension (qwen3-embedding=4096, OpenAI=1536)

    # Vision LLM
    vision_model: str = "gpt-4o-mini"  # Model supporting image input (OpenAI Vision API format)

    # RAG quality thresholds
    ragas_faithfulness_min: float = 0.85
    ragas_context_precision_min: float = 0.80
    ragas_context_recall_min: float = 0.75
    ragas_answer_relevancy_min: float = 0.85

    model_config = {"env_prefix": "", "env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
