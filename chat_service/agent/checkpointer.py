"""LangGraph checkpointer and store initialization."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from chat_service.agent.graph import build_agent_graph
from shared.config import get_settings

log = structlog.get_logger()

# Try to import PostgresStore; it may not be available yet
try:
    from langgraph.store.postgres.aio import AsyncPostgresStore

    HAS_STORE = True
except ImportError:
    HAS_STORE = False
    log.info(
        "langgraph_store_not_available",
        msg="AsyncPostgresStore not installed, skipping cross-thread memory",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    conn_string = settings.database_url

    # Initialize checkpointer (v3 API: from_conn_string is an async context manager)
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        log.info("checkpointer_initialized")

        # Initialize store (optional)
        store = None
        if HAS_STORE:
            try:
                async with AsyncPostgresStore.from_conn_string(conn_string) as _store:
                    await _store.setup()
                    store = _store
                    log.info("store_initialized")
            except Exception as e:
                log.warning("store_init_failed", error=str(e))

        # Build and compile graph
        agent = build_agent_graph(checkpointer=checkpointer)
        app.state.agent = agent
        app.state.checkpointer = checkpointer
        app.state.store = store

        log.info("agent_graph_compiled")
        yield

    log.info("shutting_down_agent")
