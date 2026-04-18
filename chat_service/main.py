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
from chat_service.routes.feedback import router as feedback_router
from chat_service.routes.ws_chat import router as ws_chat_router
from shared.metrics import setup_prometheus

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
    """Inject runtime dependencies into module-level placeholders.

    Handles graceful degradation: if embedding/reranker/milvus fail to init,
    log a warning but don't crash. Chat-only mode (no RAG) still works.
    """
    import chat_service.agent.nodes.rag_engine as rag_mod
    import chat_service.agent.nodes.preprocess as pre_mod
    import chat_service.agent.nodes.llm_generate as llm_mod
    import chat_service.agent.nodes.hitl_node as hitl_mod
    import chat_service.services.feedback as feedback_mod

    # DB pool for RAG soft-delete checks, LLM tenant config, and HITL session creation
    rag_mod.db_pool = app.state.db_pool
    llm_mod.db_pool = app.state.db_pool
    hitl_mod.db_pool = app.state.db_pool
    feedback_mod.db_pool = app.state.db_pool
    
    # Feedback service for routes
    app.state.feedback_service = feedback_mod

    # ASR client
    try:
        from shared.whisper_client import get_whisper_client
        pre_mod.asr_client = get_whisper_client()
    except Exception as e:
        log.warning("whisper_client_init_failed", error=str(e),
                    hint="ASR unavailable — voice input disabled")
        pre_mod.asr_client = None

    # Vision LLM client
    try:
        from ai_gateway import client as ai_client
        pre_mod.vision_client = ai_client
    except Exception as e:
        log.warning("vision_client_init_failed", error=str(e),
                    hint="Vision LLM unavailable — image understanding disabled")
        pre_mod.vision_client = None

    # LLM Summarizer for conversation compression
    try:
        from chat_service.agent.summarizer import LLMSummarizer
        pre_mod.llm_summarizer = LLMSummarizer()
        log.info("llm_summarizer_ready")
    except Exception as e:
        log.warning("llm_summarizer_init_failed", error=str(e),
                    hint="Summarizer unavailable — long conversations won't be compressed")
        pre_mod.llm_summarizer = None

    # Track RAG readiness
    rag_ready = True

    # Embedding service
    try:
        from shared.embedding_service import get_embedding_service
        emb = get_embedding_service()
        rag_mod.embedding_service = emb
    except Exception as e:
        log.warning("embedding_service_init_failed", error=str(e),
                    hint="RAG disabled — chat-only mode active")
        rag_mod.embedding_service = None
        rag_ready = False

    # BGE Reranker v2
    try:
        from FlagEmbedding import FlagReranker
        rag_mod.reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
    except Exception as e:
        log.warning("reranker_init_failed", error=str(e),
                    hint="Reranker unavailable — RAG will use RRF ranking only")
        rag_mod.reranker = None

    # Milvus collection
    try:
        from shared.milvus_client import get_milvus_client, COLLECTION_NAME
        client = get_milvus_client()
        # Verify collection exists
        if client.has_collection(COLLECTION_NAME):
            rag_mod.collection = client  # Pass MilvusClient directly
            log.info("milvus_collection_ready", collection=COLLECTION_NAME)
        else:
            log.warning("milvus_collection_not_found", collection=COLLECTION_NAME,
                        hint="Run 'python -m scripts.init_milvus' to create the collection")
            rag_mod.collection = None
            rag_ready = False
    except Exception as e:
        log.warning("milvus_collection_init_failed", error=str(e),
                    hint="Milvus unavailable — RAG disabled, chat-only mode active")
        rag_mod.collection = None
        rag_ready = False

    # OSS client for preprocess
    try:
        from shared.oss_client import get_oss_client
        pre_mod.oss_client = get_oss_client()
    except Exception as e:
        log.warning("oss_client_init_failed", error=str(e),
                    hint="OSS unavailable — file upload disabled")
        pre_mod.oss_client = None

    if rag_ready:
        log.info("rag_engine_ready", mode="full")
    else:
        log.warning("rag_engine_degraded", mode="chat-only",
                    hint="RAG features disabled due to missing dependencies")


app = FastAPI(title="Cuckoo-Echo Chat Service", lifespan=lifespan)
setup_prometheus(app, service_name="chat-service")

# Tenant auth middleware — validates API key and sets request.state.tenant_id
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402
import hashlib  # noqa: E402


class ChatTenantAuthMiddleware(BaseHTTPMiddleware):
    """Authenticate C-side requests via API key. Uses app.state.db_pool at request time."""

    async def dispatch(self, request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        api_key = auth.removeprefix("Bearer ")
        if not api_key:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        db_pool = request.app.state.db_pool

        async with db_pool.acquire() as conn:
            tenant = await conn.fetchrow(
                "SELECT id, status FROM tenants WHERE api_key_hash = $1", key_hash,
            )

        if not tenant or tenant["status"] != "active":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        request.state.tenant_id = str(tenant["id"])
        return await call_next(request)


app.add_middleware(ChatTenantAuthMiddleware)

app.include_router(chat_router)
app.include_router(feedback_router)
app.include_router(ws_chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
