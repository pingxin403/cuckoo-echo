"""Cuckoo-Echo Chat Service — FastAPI app entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from shared.config import get_settings
from shared.logging import setup_logging
from shared.db import create_asyncpg_pool
from shared.redis_client import get_redis, close_redis
from chat_service.agent.checkpointer import lifespan as agent_lifespan
from chat_service.routes.chat import router as chat_router
from chat_service.routes.ws_chat import router as ws_chat_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    log.info("chat_service_starting", environment=settings.environment)

    # DB + Redis
    app.state.db_pool = await create_asyncpg_pool()
    app.state.redis = get_redis()

    # Agent (checkpointer + graph) — delegate to agent_lifespan
    async with agent_lifespan(app):
        # Wire dependencies into module-level placeholders
        _wire_dependencies(app)
        log.info("chat_service_ready")
        yield

    await app.state.db_pool.close()
    await close_redis()
    log.info("chat_service_stopped")


def _wire_dependencies(app: FastAPI):
    """Inject runtime dependencies into module-level placeholders."""
    import chat_service.agent.nodes.rag_engine as rag_mod
    import chat_service.agent.nodes.preprocess as pre_mod
    import chat_service.agent.nodes.llm_generate as llm_mod

    # DB pool for RAG soft-delete checks and LLM tenant config
    rag_mod.db_pool = app.state.db_pool
    llm_mod.db_pool = app.state.db_pool

    # ASR client placeholder (wired when ASR service is available)
    pre_mod.asr_client = None

    # Embedding service
    try:
        from shared.embedding_service import get_embedding_service
        emb = get_embedding_service()
        rag_mod.embedding_service = emb
    except Exception as e:
        log.warning("embedding_service_init_failed", error=str(e))

    # BGE Reranker v2
    try:
        from FlagEmbedding import FlagReranker
        rag_mod.reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
    except Exception as e:
        log.warning("reranker_init_failed", error=str(e))

    # Milvus collection
    try:
        from shared.milvus_client import get_milvus_client, COLLECTION_NAME
        from pymilvus import Collection
        client = get_milvus_client()
        rag_mod.collection = Collection(COLLECTION_NAME)
    except Exception as e:
        log.warning("milvus_collection_init_failed", error=str(e))

    # OSS client for preprocess
    try:
        from shared.oss_client import get_oss_client
        pre_mod.oss_client = get_oss_client()
    except Exception as e:
        log.warning("oss_client_init_failed", error=str(e))


app = FastAPI(title="Cuckoo-Echo Chat Service", lifespan=lifespan)
app.include_router(chat_router)
app.include_router(ws_chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
