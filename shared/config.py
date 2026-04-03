"""Centralized configuration via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/cuckoo"

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
    llm_fallback_timeout: float = 3.0
    llm_api_key: str = ""  # e.g. "sk-..." for OpenAI, or DeepSeek/Qwen API key
    llm_api_base: str = ""  # e.g. "https://api.deepseek.com/v1" or empty for default

    # Langfuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    # Admin JWT
    admin_jwt_secret: str = "change-me-in-production"

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

    model_config = {"env_prefix": "", "env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
