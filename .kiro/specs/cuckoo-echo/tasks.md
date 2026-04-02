# Tasks

## Implementation Plan

> **Phase 划分说明**：任务按最小可用原则分为 4 个 Phase，每个 Phase 有明确的验收标准。Phase 1-2 是 MVP 核心，Phase 3-4 是完整产品。

---

## Phase 1 — 最小可运行对话（Minimal Viable Chat）

**目标**：搭建基础设施，实现最简单的文本对话流程（无 RAG、无工具、无多模态），验证多租户隔离和 SSE 流式输出。

**验收标准**：
- 能通过 API Key 鉴权发送消息
- 收到 LLM 的 SSE 流式回复（打字机效果）
- 对话历史通过 AsyncPostgresSaver 持久化
- 多租户隔离测试通过（Property 1, 2, 3）
- 限流和熔断工作

**任务列表**：

- [x] 1. Project Scaffold & Infrastructure Setup
  - [x] 1.1 Initialize monorepo layout: `api_gateway/`, `chat_service/`, `asr_service/`, `admin_service/`, `knowledge_pipeline/`, `shared/`, `tests/`; use `uv` as package manager — run `uv init` to scaffold `pyproject.toml`, `uv venv` to create virtualenv, `uv lock` to generate lockfile; all subsequent dependency operations use `uv add`/`uv sync`/`uv run`，不使用 pip; add `shared/config.py` with `pydantic-settings` `BaseSettings` class for type-safe config loading; configure `structlog` JSON logging in `shared/logging.py`
  - [x] 1.2 Write `shared/db.py`: `create_asyncpg_pool()` reading DSN from `pydantic-settings` `Settings.database_url` with PgBouncer transaction-mode DSN and `statement_cache_size=0` (required: asyncpg caches prepared statements by default, but PgBouncer transaction mode switches backend connections per transaction, causing "prepared statement does not exist" errors — disabling the cache is mandatory); `tenant_db_context(conn, tenant_id)` async context manager that opens a transaction and executes `SET LOCAL app.current_tenant = $1`; `lock_key(thread_id)` and `ratelimit_key(tenant_id, user_id)` key-builder functions enforcing `cuckoo:` namespace prefix; use `structlog.get_logger()` for all logging
  - [x] 1.3 Apply PostgreSQL DDL via `migrations/001_initial.sql`: `tenants` (with `api_key_prefix`, `api_key_hash`, `llm_config`, `rate_limit`), `users`, `threads`, `messages`, `knowledge_docs`, `hitl_sessions` tables with all RLS policies, indexes, and `pgcrypto` extension; run with `psql -f migrations/001_initial.sql`
  - [x] 1.4 Write `shared/milvus_client.py`: `create_knowledge_chunks_collection()` with `CollectionSchema` (id, tenant_id PartitionKey, doc_id, chunk_text with `enable_analyzer=True` and `analyzer_params={"type": "chinese"}` — 使用 Milvus 2.5 内置 chinese analyzer 自动 jieba 分词 + 停用词 + 标点移除, dense_vector, sparse_vector), BM25 `Function`, HNSW index on `dense_vector`, `SPARSE_INVERTED_INDEX` on `sparse_vector`, `num_partitions=64`
  - [x] 1.5 Write `shared/redis_client.py`: `get_redis()` returning an `aioredis` client (single-node for local dev, Cluster DSN for production via env var `REDIS_URL`)
  - [x] 1.6 Add `docker-compose.yml` for local dev: PostgreSQL 16, Milvus 2.5, Redis 7 (single node — Cluster is production-only), MinIO; add `Makefile` with常用命令：`make install`（`uv sync`）、`make test`（`uv run pytest`）、`make lint`（`uv run ruff check`）、`make up`（`docker compose up -d`）；Dockerfile 中使用 `uv pip install` 替代 `pip install`
  - [x] 1.7 Add CI/CD configuration: `.github/workflows/ci.yml` (PR trigger → `uv sync` → `ruff check` → `ruff format --check` → `pytest tests/unit/`); `.pre-commit-config.yaml` with ruff lint + format hooks; optional `.github/workflows/integration.yml` for integration tests with docker compose services

- [x] 2. API Gateway
  - [x] 2.1 Implement `TenantAuthMiddleware` in `api_gateway/middleware/auth.py`: extract Bearer token, compute `hashlib.sha256(api_key.encode()).hexdigest()`, query `tenants` table by `api_key_hash`, attach `request.state.tenant_id`; return 401 on miss
  - [x] 2.2 Implement `RateLimitMiddleware` in `api_gateway/middleware/rate_limit.py`: local `TokenBucket` coarse filter per `(tenant_id, user_id)`; Redis `INCR` + `EXPIRE 1` fixed-window precise check using key `cuckoo:ratelimit:{tenant_id}:{user_id}`; return 429 with `Retry-After: 1` on breach; load per-tenant threshold from `tenants.rate_limit` JSONB
  - [x] 2.3 Implement `CircuitBreakerMiddleware` in `api_gateway/middleware/circuit_breaker.py` using `circuitbreaker` library: `failure_threshold=50`, `recovery_timeout=30`; wrap `call_llm` and `call_tool_service`; return 503 degraded response when open
  - [x] 2.4 Implement `MediaFormatValidator` in `api_gateway/middleware/media_format.py`: read the first 16 bytes of the uploaded file to check magic numbers (e.g., `FF D8 FF` for JPEG, `89 50 4E 47` for PNG, `52 49 46 46` for WAV/WEBP) — do not rely solely on `Content-Type` header which is trivially spoofable; allowed audio: `wav/mp3/m4a`; allowed image: `jpg/png/webp`; return 415 on mismatch
  - [x] 2.5 Wire all middleware into `api_gateway/main.py` FastAPI app in order: `TenantAuthMiddleware` → `RateLimitMiddleware` → `CircuitBreakerMiddleware`; add `/health` endpoint; configure `structlog` JSON logging; production 启动命令使用 `granian --interface asgi api_gateway.main:app`，开发环境可用 `uvicorn api_gateway.main:app --reload`
  - [x] 2.6 Write unit tests in `tests/unit/test_gateway.py`: valid/invalid API key, rate-limit boundary (N-1, N, N+1), 415 for unsupported formats, circuit-breaker open/half-open/close transitions

- [x] 3. Multi-Tenant Isolation Integration Tests
  - [x] 3.1 Write integration tests in `tests/integration/test_tenant_isolation.py`: insert rows for two tenants, query with each `tenant_db_context`, assert zero cross-tenant rows in `users`, `threads`, `messages`
  - [x] 3.2 Write integration tests in `tests/integration/test_milvus_isolation.py`: insert vectors for two tenants, search with `partition_names=[tenant_a]`, assert all results have `tenant_id == tenant_a`

- [x] 4. LangGraph Agent Graph
  - [x] 4.1 Define `AgentState` TypedDict in `chat_service/agent/state.py` with all fields: `thread_id`, `tenant_id`, `user_id`, `messages`, `summary`, `user_intent`, `rag_context`, `tool_calls`, `media_urls`, `hitl_requested`, `tokens_used`, `llm_response`, `guardrails_passed`, `correction_message`, `unresolved_turns`
  - [x] 4.2 Implement stub node functions in `chat_service/agent/nodes.py`: `preprocess_node`, `router_node`, `rag_engine_node`, `tool_executor_node`, `llm_generate_node`, `guardrails_node`, `postprocess_node` — each accepting and returning `AgentState`
  - [x] 4.3 Implement `build_agent_graph(checkpointer)` in `chat_service/agent/graph.py`: wire all nodes, `set_entry_point("preprocess")`, conditional edges from `router` (`tool`/`rag`/`hitl`→END) and `guardrails` (`pass`/`hitl`→END), `compile(checkpointer=checkpointer, interrupt_before=["hitl"])`
  - [x] 4.4 Implement `get_checkpointer()` in `chat_service/agent/checkpointer.py`: create a single global `AsyncPostgresSaver` instance and `AsyncPostgresStore` instance (跨 Thread 长期记忆) from the asyncpg pool at app startup; expose `lifespan` context manager that calls `checkpointer.setup()` and `store.setup()`; compile graph with both `checkpointer` and `store`; store the compiled graph in `app.state.agent`
  - [x] 4.5 Write unit tests in `tests/unit/test_agent_graph.py`: verify graph topology (node names, edge targets), verify `compile()` succeeds with a mock checkpointer

- [x] 5. Chat_Service SSE Endpoint
  - [x] 5.1 Implement `event_generator()` in `chat_service/routes/chat.py`: acquire Redis lock (`cuckoo:lock:{thread_id}`, TTL 90s, `blocking=False`) inside the generator; yield `{"error": "CONCURRENT_REQUEST"}` SSE event and return if lock not acquired (409 semantics)
  - [x] 5.2 Inside `event_generator()`, call `asyncio.shield(agent.astream_events(payload, config, version="v2"))`; handle `on_chat_model_stream` events to yield `data: {"content": token}` SSE frames using `orjson.dumps().decode()` for high-frequency serialization; yield `data: [DONE]` on completion
  - [x] 5.3 In the `finally` block of `event_generator()`: release the Redis lock; call `billing_service.record_usage(thread_id, tenant_id, tokens_used)` if `tokens_used > 0`; write `interrupted` status to `messages` table on `asyncio.CancelledError`
  - [x] 5.4 Implement `POST /v1/chat/completions` endpoint returning `EventSourceResponse(event_generator(), ping=15)`; add `GET /v1/threads/{thread_id}` to fetch conversation history via `AsyncPostgresSaver`
  - [x] 5.5 Write unit tests in `tests/unit/test_chat_service.py`: lock-acquired path yields tokens, lock-not-acquired path yields error event, `[DONE]` is last event, `billing_service.record_usage` called in finally

- [x] 6. LLM Gateway Integration
  - [x] 6.1 Implement `ai_gateway/client.py`: wrap LiteLLM `acompletion` with `stream=True` and `stream_usage=True`; configure primary and fallback model backends from `tenants.llm_config`; implement 3s fallback timeout using `asyncio.wait_for`
  - [x] 6.2 Integrate Langfuse: add `LangfuseCallbackHandler` to all LLM calls; record `trace_id = thread_id`, `span` per node, `usage_metadata` for token counting; configure via env vars `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
  - [x] 6.3 Implement `billing_service.record_usage(thread_id, tenant_id, tokens_used)` in `shared/billing.py`: `UPDATE messages SET tokens_used = $1 WHERE thread_id = $2` within `tenant_db_context`; also update multimodal Credits for audio/image consumption
  - [x] 6.4 Write unit tests in `tests/unit/test_llm_gateway.py`: primary backend success, primary timeout triggers fallback within 3s, `stream_usage=True` captures token counts, Langfuse callback invoked

- [x] 7. Router Node
  - [x] 7.1 Implement `RULE_PATTERNS` dict in `chat_service/agent/nodes/router.py` with compiled regex patterns for `get_order_status` and `update_shipping_address` (Chinese + English variants)
  - [x] 7.2 Implement `detect_negative_sentiment(state)` in `chat_service/agent/nodes/router.py`: keyword/pattern-based negative-emotion detection; return `True` if matched or `state["unresolved_turns"] >= 3`
  - [x] 7.3 Implement `llm_classify_intent(text, tenant_id)` in `chat_service/agent/nodes/router.py`: call AI Gateway with a classification prompt; return one of `"tool:{name}"`, `"rag"`, `"hitl"`, `"chitchat"`
  - [x] 7.4 Implement `router_node(state)`: rule engine first → sentiment/HITL check → LLM fallback; return updated `AgentState` with `user_intent` set
  - [x] 7.5 Implement `route_decision(state)` conditional edge function returning `"tool"`, `"rag"`, or `"hitl"`
  - [x] 7.6 Write unit tests in `tests/unit/test_router.py`: rule-engine patterns hit correctly, HITL triggers on negative sentiment and `unresolved_turns >= 3`, LLM fallback called only when rules miss

---

## Phase 2 — RAG 知识问答（Knowledge Q&A）

**目标**：实现知识库上传、向量检索、Rerank 和幻觉检测，让 AI 能基于企业文档回答问题。

**验收标准**：
- 上传 PDF/Word/TXT 文档后，能通过对话检索到相关内容
- RAG 检索结果经过 Rerank，Top-3 切片传入 LLM
- Guardrails NLI 检测工作，幻觉时推送纠正消息
- 知识库往返一致性测试通过（Property 11）
- 软删除后文档内容不再出现在检索结果中

**任务列表**：

- [x] 8. RAG Engine Node
  - [x] 8.1 Implement `rag_engine_node(state)` in `chat_service/agent/nodes/rag_engine.py`: embed query via `embedding_service.embed()`; build `AnnSearchRequest` for `dense_vector` (COSINE, ef=100, limit=10) and `sparse_vector` (BM25, limit=10), both with `expr=f"tenant_id == '{tenant_id}'"` and `partition_names=[tenant_id]`
  - [x] 8.2 Call `collection.hybrid_search(reqs=[dense_req, sparse_req], rerank=RRFRanker(k=60), limit=5, output_fields=["chunk_text","doc_id"], partition_names=[tenant_id])`; handle empty results by returning `user_intent="no_answer"`
  - [x] 8.3 Implement soft-delete filtering: extract `doc_id` list from results, call `get_active_doc_ids(doc_ids, tenant_id)` (queries PG `knowledge_docs WHERE deleted_at IS NULL`), filter chunks to active docs only
  - [x] 8.4 Implement reranker using `FlagEmbedding` library with `BAAI/bge-reranker-v2-m3` model; call `reranker.compute_score(pairs)` via `asyncio.get_running_loop().run_in_executor()` wrapped with `asyncio.wait_for(..., timeout=0.5)`; on `TimeoutError` log warning (structlog) and fall back to RRF Top-3; always return `rag_context` as list of ≤ 3 strings
  - [x] 8.5 Write unit tests in `tests/unit/test_rag_engine.py`: Top-K ≤ 5 from Milvus, Top-3 after rerank, soft-deleted docs filtered out, rerank timeout falls back gracefully

- [x] 9. Guardrails Node
  - [x] 9.1 Load `CrossEncoder("cross-encoder/nli-deberta-v3-small")` as a module-level singleton in `chat_service/agent/nodes/guardrails.py`; document label order: `contradiction=0, entailment=1, neutral=2`
  - [x] 9.2 Implement `guardrails_node(state)`: skip if `rag_context` is empty (non-RAG path); build `pairs = [(ctx, response) for ctx in rag_context]`; run `nli_model.predict(pairs, apply_softmax=True)` via `asyncio.get_running_loop().run_in_executor(None, ...)` — CrossEncoder inference is CPU-bound and will block the event loop if called directly; wrap with `asyncio.wait_for(..., timeout=0.3)`
  - [x] 9.3 If `max_entailment < 0.5`: set `guardrails_passed=False`, `correction_message="⚠️ 抱歉，刚才的回答可能有误，已为您转接人工客服核实。"`, `hitl_requested=True`; on `TimeoutError` log warning and pass through
  - [x] 9.4 Implement `postprocess_node(state)`: if `correction_message` is set, yield it as an SSE event; append current turn to `messages`; increment `unresolved_turns` if `guardrails_passed=False`
  - [x] 9.5 Implement `guardrails_decision(state)` returning `"hitl"` or `"pass"`
  - [x] 9.6 Write unit tests in `tests/unit/test_guardrails.py`: entailment ≥ 0.5 passes, entailment < 0.5 sets correction_message and hitl_requested, non-RAG path skips NLI, timeout degrades gracefully

- [x] 10. Knowledge Pipeline Worker
  - [x] 10.1 Implement `KnowledgePipelineWorker.run()` in `knowledge_pipeline/worker.py`: poll loop with `SELECT id, tenant_id, oss_path FROM knowledge_docs WHERE status = 'pending' ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED`; sleep 2s when no rows found
  - [x] 10.2 Implement `document_parser.parse(file_path)` in `knowledge_pipeline/parser.py`: use Docling `DocumentConverter` as unified parser for PDF, Word, HTML, plain text; call `converter.convert(file_path)` → `result.document.export_to_markdown()` to get structured Markdown output preserving headings/tables/lists; raise `ParseError` on failure; Docling 内置 OCR（EasyOCR），扫描件 PDF 也能处理
  - [x] 10.3 Implement `chunker.split(docling_doc)` in `knowledge_pipeline/chunker.py`: 优先使用 Docling 内置的 `HierarchicalChunker`（按文档结构标题/段落/表格智能分块，保留层级上下文），配置 `max_tokens=512`, `merge_peers=True`; 对于纯文本回退到 `RecursiveCharacterTextSplitter` with `separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]`, `chunk_size=512`, `chunk_overlap=64`; return `list[str]` with at least one non-empty chunk for any valid input
  - [x] 10.4 Implement `process_document(doc_id, tenant_id, file_path)`: update status to `processing` → parse → chunk → `embedding_service.embed_batch(chunks)` → `milvus_client.insert(partition_name=tenant_id)` → update status to `completed`; on any exception update status to `failed` with `error_msg` and increment `knowledge_pipeline.failed` metric
  - [x] 10.5 Write unit tests in `tests/unit/test_knowledge_pipeline.py`: Docling parses each format (PDF/Word/HTML/TXT) to non-empty Markdown, chunker produces ≤ 512-char chunks with overlap, failed parse sets status=failed, SKIP LOCKED prevents double-processing

---

## Phase 3 — 完整客服能力（Full Customer Service）

**目标**：实现工具调用（查订单/改地址）、语音/图片多模态输入、人工介入（HITL）和 Admin 后台基础功能。

**验收标准**：
- 用户说"查询订单 12345"能触发工具调用并返回结果
- 发送语音文件能转写后进入对话流程
- 负面情绪或 3 轮未解决时触发 HITL，Admin 能接管对话
- 60s 无人响应自动升级并创建工单
- 并发安全测试通过（Property 23）

**任务列表**：

- [ ] 11. Tool Executor Node
  - [ ] 11.1 Implement `get_order_status(order_id, tenant_id)` and `update_shipping_address(order_id, address, tenant_id)` in `chat_service/agent/tools/order_tools.py`; each function must include `tenant_id` in every outbound request/query
  - [ ] 11.2 Implement `tool_executor_node(state)` in `chat_service/agent/nodes/tool_executor.py`: parse `user_intent` to extract tool name and args; call `safe_tool_call(tool_name, args, tenant_id)` with `asyncio.wait_for(..., timeout=5.0)`; on `TimeoutError` return friendly error dict
  - [ ] 11.3 Persist tool call record: after each call append `{"name": tool_name, "args": args, "result": result}` to `state["tool_calls"]`; the AsyncPostgresSaver Checkpoint already persists the full State including `tool_calls` — no separate DB write needed here
  - [ ] 11.4 Write unit tests in `tests/unit/test_tool_executor.py`: successful call returns result, 5s timeout returns error dict, `tenant_id` present in every outbound call

- [ ] 12. ASR Service & Multimodal Preprocess
  - [ ] 11.1 Implement `POST /v1/asr/transcribe` in `asr_service/main.py`: validate `content_type in SUPPORTED_AUDIO_TYPES`; upload to OSS with prefix `{tenant_id}/audio/`; call `whisper_client.transcribe(oss_path)`; return `{"text": ..., "oss_path": ...}`; raise 500 on `WhisperError`
  - [ ] 11.2 Implement `preprocess_node` multimodal handling in `chat_service/agent/nodes/preprocess.py`: if `media` contains audio, call ASR service and replace content with transcript; if `media` contains image, upload to OSS and append signed URL to message; push `{"status": "processing"}` SSE event during preprocessing
  - [ ] 11.3 Measure ASR-to-Agent handoff latency: record `asr_done_at` timestamp after transcription; compute `handoff_ms = (agent_start_at - asr_done_at).total_seconds() * 1000`; emit `metrics.histogram("asr_handoff_ms", handoff_ms)` and log warning if `handoff_ms > 500`; also emit `metrics.histogram("asr_processing_ms", processing_ms)` for Whisper inference duration — this is the key signal for GPU scaling decisions
  - [ ] 11.4 Write unit tests in `tests/unit/test_asr_service.py`: successful transcription returns text, unsupported format returns 415, WhisperError returns 500, OSS path includes tenant prefix

- [ ] 12. Admin Service — Knowledge Management
  - [ ] 12.1 Implement `POST /admin/v1/knowledge/docs` in `admin_service/routes/knowledge.py`: accept multipart upload ≤ 50MB; write OSS path and `status=pending` row to `knowledge_docs`; return `doc_id`
  - [ ] 12.2 Implement `GET /admin/v1/knowledge/docs/{id}`: query `knowledge_docs` for `status`, `chunk_count`, `error_msg`; return progress object
  - [ ] 12.3 Implement `DELETE /admin/v1/knowledge/docs/{id}`: set `deleted_at = NOW()` immediately (soft delete); enqueue async Milvus cleanup task (`delete expr=f"doc_id == '{doc_id}'"`) with retry (max 3 attempts, exponential backoff); Milvus physical delete must complete within 5 minutes
  - [ ] 12.4 Implement `POST /admin/v1/knowledge/docs/{id}/retry`: reset `status=pending`, clear `error_msg`; the polling worker will pick it up on next cycle
  - [ ] 12.5 Write unit tests in `tests/unit/test_admin_knowledge.py`: upload creates pending row, delete sets deleted_at, retry resets status, progress endpoint returns correct status

- [ ] 13. Admin Service — HITL
  - [ ] 13.1 Implement `WS /admin/v1/ws/hitl` in `admin_service/routes/hitl.py`: maintain per-tenant WebSocket connection registry; push `{"type": "hitl_request", "thread_id": ..., "reason": ..., "unresolved_turns": ...}` when Agent sets `hitl_requested=True`
  - [ ] 13.2 Implement `POST /admin/v1/hitl/{session_id}/take`: update `threads.status = 'human_intervention'`; update `hitl_sessions.admin_user_id` and `status = 'active'`; stop Agent auto-reply for that thread
  - [ ] 13.3 Implement `POST /admin/v1/hitl/{session_id}/end`: update `threads.status = 'active'`; update `hitl_sessions.ended_at` and `status = 'resolved'`; allow Agent to resume
  - [ ] 13.4 Implement 60s escalation timer using a persistent delayed task: on HITL request, insert a row into a `hitl_escalation_tasks` table with `execute_at = NOW() + INTERVAL '60 seconds'`; a background polling loop (similar to Knowledge Pipeline Worker, using `SELECT FOR UPDATE SKIP LOCKED`) checks for overdue rows and triggers escalation — do NOT use `asyncio.sleep(60)` which is lost on Pod restart; on escalation: push wait-message SSE to end-user, set `hitl_sessions.status = 'auto_escalated'`, create ticket row, send ticket-confirmation SSE
  - [ ] 13.5 Write unit tests in `tests/unit/test_hitl.py`: take sets thread to human_intervention, end restores to active, 60s timeout triggers escalation and ticket creation; verify escalation task row is inserted on HITL request and deleted after escalation fires

- [ ] 14. Admin Service — Config & Metrics
  - [ ] 14.1 Implement `PUT /admin/v1/config/persona`, `PUT /admin/v1/config/model`, `PUT /admin/v1/config/rate-limit` in `admin_service/routes/config.py`: update `tenants.llm_config` and `tenants.rate_limit` JSONB fields; invalidate cached rate-limit values in Redis
  - [ ] 14.2 Implement `GET /admin/v1/metrics/overview` and `GET /admin/v1/metrics/tokens` in `admin_service/routes/metrics.py`: query PostgreSQL read-replica (`PG_RO`); support `range` query param (`1d`, `7d`, `30d`); aggregate total conversations, AI resolution rate, human-transfer rate, avg TTFT, token consumption
  - [ ] 14.3 Implement `GET /admin/v1/metrics/missed-queries`: query `messages` where `hitl_requested=True` or RAG returned `user_intent="no_answer"`; group by `content` prefix (first 50 chars) and count frequency; return top-20 most frequent unanswered questions sorted by count — no ML clustering needed at MVP stage
  - [ ] 14.4 Implement `POST /admin/v1/sandbox/run`: run `run_rag_quality_gate(tenant_id, test_cases)` using Ragas metrics (`Faithfulness ≥ 0.85`, `ContextPrecision ≥ 0.80`, `ContextRecall ≥ 0.75`, `AnswerRelevancy ≥ 0.85`); return pass/fail with per-metric scores
  - [ ] 14.5 Write unit tests in `tests/unit/test_admin_config.py`: persona update persists to DB, rate-limit update invalidates Redis cache, metrics endpoint uses read-replica DSN

---

## Phase 4 — 生产就绪（Production Ready）

**目标**：完善指标看板、沙盒测试、属性测试全覆盖，以及可选的 K8s 部署配置。

**验收标准**：
- Admin 指标看板展示对话数、解决率、TTFT、Token 消耗
- 沙盒 Ragas 质量门禁通过（Faithfulness ≥ 0.85）
- 所有 9 个 Hypothesis 属性测试全绿（100 次迭代）
- 限流不变量测试通过（Property 30）

**任务列表**：

- [ ]* 16. Kubernetes Deployment
  - [ ]* 16.1 Write `k8s/api-gateway-deployment.yaml`: `Deployment` + `HPA` (CPU target 70%, min 2 / max 20 replicas); `readinessProbe` on `/health`; `livenessProbe` on `/health`; env vars for Redis, PG DSN; Dockerfile 使用 `COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv` 多阶段构建，`uv pip install --system` 安装依赖
  - [ ]* 16.2 Write `k8s/chat-service-deployment.yaml`: same HPA pattern; mount `CHECKPOINTER_PG_DSN` secret; `terminationGracePeriodSeconds: 120` to allow in-flight SSE streams to complete
  - [ ]* 16.3 Write `k8s/pgbouncer-configmap.yaml`: `pool_mode = transaction`, `max_client_conn = 1000`, `default_pool_size = 20`; document why transaction mode is required for `SET LOCAL` RLS activation
  - [ ]* 16.4 Write `k8s/knowledge-pipeline-deployment.yaml`: single-replica `Deployment` (SKIP LOCKED handles multi-worker safety); env vars for PG, Milvus, OSS, Embedding Service
  - [ ]* 16.5 Write `k8s/admin-service-deployment.yaml`: separate `PG_RO_DSN` env var pointing to read-replica; HPA min 1 / max 5

- [ ] 17. Property-Based Tests (Hypothesis)
  > **Hypothesis + asyncio 注意事项**：Hypothesis 原生不支持 `async def` 测试函数（会返回 coroutine 而非 None）。所有 PBT 测试必须是同步函数，在内部用 `asyncio.get_event_loop().run_until_complete()` 或 `anyio.from_thread.run_sync()` 调用异步代码；或者使用 `hypothesis[asyncio]` 扩展配合 `@given` + `@pytest.mark.asyncio`（需 pytest-asyncio >= 0.21 且 `asyncio_mode = "auto"`）。推荐方案：每个 PBT 文件顶部加 `@settings(suppress_health_check=[HealthCheck.too_slow])` 并用同步包装器。
  - [ ] 17.1 Implement Property 1 test `test_rls_tenant_isolation` in `tests/pbt/test_p1_tenant_isolation.py`: `@given(tenant_a_id=st.uuids(), tenant_b_id=st.uuids(), row_count=st.integers(1,20))`; `assume(tenant_a_id != tenant_b_id)`; seed both tenants; query with `tenant_a` context; assert all rows have `tenant_id == tenant_a_id` for `users`, `threads`, `messages` tables. **Validates: Requirements 1.3, 1.4, 1.7**
  - [ ] 17.2 Implement Property 2 test `test_milvus_partition_isolation` in `tests/pbt/test_p2_milvus_isolation.py`: `@given(tenant_a=st.uuids(), tenant_b=st.uuids(), n_vectors=st.integers(1,10))`; insert semantically similar vectors for both tenants; search with `partition_names=[tenant_a]`; assert all results have `tenant_id == tenant_a`. **Validates: Requirements 1.5, 1.8**
  - [ ] 17.3 Implement Property 3 test `test_redis_key_prefix` in `tests/pbt/test_p3_redis_prefix.py`: `@given(tenant_id=st.uuids(), user_id=st.uuids())`; call `ratelimit_key(tenant_id, user_id)` and `lock_key(thread_id)`; assert every generated key starts with `"cuckoo:"` and contains the tenant/thread id — this test is pure-sync, no async needed. **Validates: Requirements 1.6**
  - [ ] 17.4 Implement Property 4 test `test_invalid_api_key_rejected` in `tests/pbt/test_p4_api_key.py`: `@given(api_key=st.one_of(st.just(""), st.text(min_size=1, max_size=64), st.binary().map(lambda b: b.hex())))`; send request with unregistered key; assert HTTP 401. **Validates: Requirements 1.2**
  - [ ] 17.5 Implement Property 5 test `test_unsupported_media_format_rejected` in `tests/pbt/test_p5_media_format.py`: `@given(mime=st.sampled_from(["video/mp4","application/pdf","image/gif","audio/ogg","text/plain"]))`; POST to `/v1/media/upload` with unsupported MIME; assert HTTP 415. **Validates: Requirements 2.5**
  - [ ] 17.6 Implement Property 11 test `test_rag_round_trip` in `tests/pbt/test_p11_rag_round_trip.py`: `@given(doc=st.text(min_size=100, max_size=2000, alphabet=st.characters(whitelist_categories=("L","N","P","Z"))))`; run full pipeline (parse → chunk → embed → insert); query with key sentence; assert at least one result with similarity ≥ 0.7. **Validates: Requirements 3.8**
  - [ ] 17.7 Implement Property 19 test `test_checkpointer_round_trip` in `tests/pbt/test_p19_checkpointer.py`: `@given(message_count=st.integers(1,50))`; build `AgentState` with random messages; `aput` via `AsyncPostgresSaver`; `aget` and compare `messages`, `user_intent`, `tool_calls` field-by-field. **Validates: Requirements 6.3**
  - [ ] 17.8 Implement Property 23 test `test_concurrent_thread_safety` in `tests/pbt/test_p23_concurrency.py`: `@given(initial_count=st.integers(0,10), concurrent_n=st.integers(2,10))`; seed thread; `asyncio.gather` N concurrent `send_message` calls; assert `success_count + conflict_409_count == concurrent_n`; assert `final_message_count == initial_count + success_count`; assert no duplicate message IDs. **Validates: Requirements 6.8**
  - [ ] 17.9 Implement Property 30 test `test_rate_limit_window` in `tests/pbt/test_p30_rate_limit.py`: `@given(limit=st.integers(1,20), extra=st.integers(1,10))`; configure tenant with `user_rps=limit`; send `limit + extra` requests in < 1s; assert first `limit` return 200, remaining `extra` return 429 with `Retry-After` header; sleep 1s; assert next `limit` requests return 200. **Validates: Requirements 11.1, 11.2, 11.3**
