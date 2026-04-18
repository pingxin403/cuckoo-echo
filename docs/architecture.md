# System Architecture / 系统架构

## Overview / 概述

Cuckoo-Echo follows a microservices architecture with four application services backed by shared infrastructure. Multi-tenant data isolation is enforced at three layers: PostgreSQL RLS, Milvus PartitionKey, and Redis key prefixes.

Cuckoo-Echo 采用微服务架构，四个应用服务共享基础设施层。多租户数据隔离通过三层防御实现：PostgreSQL 行级安全（RLS）、Milvus PartitionKey、Redis Key 前缀。

---

## Overall System Architecture / 系统整体架构

```mermaid
graph TB
    subgraph Clients / 客户端
        WEB[Web App]
        APP[Mobile App]
        SDK[SDK / API]
    end

    subgraph Gateway Layer / 接入层
        GW[API Gateway :8000<br/>Auth · Rate Limit · Circuit Breaker<br/>tenant_id Resolution]
    end

    subgraph Application Layer / 应用层
        CS[Chat Service :8001<br/>FastAPI + LangGraph<br/>SSE Streaming]
        ADMIN[Admin Service :8002<br/>Knowledge · HITL · Config · Metrics]
        ASR[ASR Service<br/>Whisper STT]
        KP[Knowledge Pipeline<br/>PG Poll Worker<br/>Parse → Chunk → Embed]
    end

    subgraph Storage Layer / 存储层
        PG[(PostgreSQL 16<br/>RLS · Checkpointer<br/>knowledge_docs Queue)]
        MV[(Milvus 2.5+<br/>PartitionKey Isolation<br/>Dense + BM25 Hybrid)]
        REDIS[(Redis 7<br/>Distributed Locks<br/>Rate Limiting)]
        OSS[(MinIO / OSS<br/>Media · Documents)]
    end

    subgraph AI Model Pool / AI 模型服务
        AIGTW[AI Gateway / LiteLLM<br/>Fallback · Load Balance]
        LLM1[DeepSeek]
        LLM2[Qwen]
        LLM3[Llama Local]
        EMB[Embedding Service<br/>Sentence-Transformers]
        RERANK[BGE Reranker v2<br/>Cross-Encoder]
    end

    subgraph Observability / 可观测性
        LANGFUSE[Langfuse<br/>LLM Tracing + Feedback]
        PROM[Prometheus<br/>Metrics]
    end

    subgraph Feedback / 用户反馈
        FB[Feedback Service<br/>Storage + Stats]
    end

    WEB & APP & SDK --> GW
    GW --> CS & ASR
    CS --> PG & MV & REDIS & AIGTW & RERANK
    ADMIN --> PG & OSS
    KP --> PG & MV & EMB
    ASR --> OSS
    AIGTW --> LLM1 & LLM2 & LLM3
    CS -.-> LANGFUSE & PROM
    CS --> FB
    FB -.-> LANGFUSE
    ADMIN -.-> PROM
```

---

## Request Flow / 请求处理流程

```mermaid
sequenceDiagram
    participant U as End User
    participant GW as API Gateway
    participant CS as Chat Service
    participant AG as LangGraph Agent
    participant PG as PostgreSQL
    participant MV as Milvus
    participant AI as AI Gateway / LLM

    U->>GW: POST /v1/chat/completions<br/>Authorization: Bearer api_key
    GW->>GW: Resolve tenant_id from API key hash
    GW->>GW: Rate limit check (Redis INCR)
    GW->>GW: Circuit breaker check
    GW->>CS: Forward with X-Tenant-ID header

    CS->>CS: Acquire Redis lock (thread_id)
    CS->>AG: astream_events(config={thread_id, tenant_id})

    Note over AG,PG: Auto-restore State from PG Checkpointer

    AG->>AG: preprocess (ASR / image upload / summary)
    AG->>AG: router (rule engine → LLM fallback)

    alt Tool Intent / 工具意图
        AG->>AG: tool_executor (get_order_status, etc.)
    else Knowledge Query / 知识问答
        AG->>MV: hybrid_search (dense + BM25, RRF fusion)
        MV-->>AG: Top-5 chunks
        AG->>AG: Rerank → Top-3
    end

    AG->>AI: LLM call (stream=true)
    AI-->>CS: Token stream
    CS-->>U: SSE: data: {"delta":{"content":"..."}}

    AG->>AG: guardrails (NLI hallucination check)

    Note over AG,PG: Auto-save Checkpoint at node boundaries

    CS-->>U: SSE: data: [DONE]
    CS->>CS: Release Redis lock
```

---

## Multi-Tenant Data Isolation / 多租户数据隔离

```mermaid
flowchart LR
    REQ[HTTP Request<br/>Authorization: Bearer api_key]
    GW[Gateway<br/>Resolve tenant_id<br/>Inject X-Tenant-ID]
    CS[Chat Service<br/>request.state.tenant_id]

    subgraph PostgreSQL
        PG_CTX[SET LOCAL app.current_tenant]
        RLS[RLS Policy Auto-Filter]
    end

    subgraph Milvus
        MV_PK[partition_key = tenant_id]
    end

    subgraph Redis
        RD_PFX[Key: cuckoo:*:tenant_id:*]
    end

    TOOL[Tool Executor<br/>tenant_id in every request]

    REQ --> GW --> CS
    CS --> PG_CTX --> RLS
    CS --> MV_PK
    CS --> RD_PFX
    CS --> TOOL
```

| Layer | Mechanism | Isolation Level |
|-------|-----------|----------------|
| PostgreSQL | RLS (`SET LOCAL app.current_tenant`) | Row-level, automatic |
| Milvus | PartitionKey = tenant_id | Partition-level, physical |
| Redis | Key prefix `cuckoo:{scope}:{tenant_id}:` | Key-level, logical |

---

## LangGraph State Machine / Agent 状态机

```mermaid
stateDiagram-v2
    [*] --> preprocess : Message received
    preprocess --> router : Preprocessed (ASR/image/summary)

    router --> tool_executor : Tool intent (rule match or LLM)
    router --> rag_engine : Knowledge query intent
    router --> hitl_interrupt : Negative sentiment or 3+ unresolved

    tool_executor --> llm_generate : Tool result ready
    rag_engine --> llm_generate : Retrieval + Rerank done

    llm_generate --> guardrails : LLM generation complete
    guardrails --> postprocess : Passed safety check
    guardrails --> hitl_interrupt : Hallucination detected (NLI)

    postprocess --> [*] : Update state, push SSE
    hitl_interrupt --> [*] : Pause graph, await human
    hitl_interrupt --> router : Admin ends intervention
```

**Node Responsibilities:**

| Node | Description |
|------|-------------|
| `preprocess` | ASR transcription, image upload to OSS, summary compression (>50 turns) |
| `router` | Rule engine (regex/keyword) → LLM fallback intent classification |
| `rag_engine` | Milvus hybrid search (dense + BM25) → BGE Reranker → Top-3 |
| `tool_executor` | Business tool calls (order status, address update) with tenant_id |
| `llm_generate` | LLM streaming generation via AI Gateway |
| `guardrails` | NLI hallucination detection (cross-encoder/nli-deberta-v3-small) |
| `postprocess` | Push correction message if needed, update state |

---

## User Feedback Loop / 用户反馈环

```mermaid
sequenceDiagram
    participant U as User
    participant CS as Chat Service
    participant FB as Feedback Service
    participant PG as PostgreSQL
    participant REDIS as Redis Cache
    participant LANGFUSE as Langfuse

    U->>CS: Message with feedback buttons
    CS->>FB: POST /v1/feedback
    FB->>PG: INSERT/UPDATE feedback
    PG-->>FB: Confirm
    FB->>REDIS: Invalidate cache
    FB->>LANGFUSE: Send feedback event (async)
    CS-->>U: Return success + feedback_state
```

**Data Flow:**

1. User clicks 👍/👎 on AI response
2. Frontend calls `POST /v1/feedback` with `feedback_type`
3. Backend stores/updates feedback in PostgreSQL (RLS enforced)
4. Redis cache invalidated (TTL: 60s)
5. Async feedback event sent to Langfuse for tracing

---

## Knowledge Pipeline / 知识处理管道

```mermaid
flowchart LR
    UPLOAD[Admin uploads doc] --> PG_INSERT[INSERT knowledge_docs<br/>status = pending]
    PG_INSERT --> WORKER[Pipeline Worker<br/>SELECT FOR UPDATE SKIP LOCKED]
    WORKER --> PARSER[Docling Parser<br/>PDF / Word / HTML / TXT]
    PARSER --> CHUNKER[Recursive Chunker<br/>512 chars, 64 overlap]
    CHUNKER --> EMB[Embedding Service<br/>Batch vectorize]
    EMB --> MILVUS[Milvus INSERT<br/>dense + sparse vectors]
    EMB --> PG_OK[UPDATE status = completed]
    PARSER -- Error --> PG_FAIL[UPDATE status = failed<br/>Record error_msg]
```

---

## Deployment Topology / 部署拓扑

### MVP: Single Region

```
┌─────────────────────────────────────────────┐
│  Kubernetes Cluster                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ Gateway  │ │  Chat    │ │  Admin   │    │
│  │ (HPA)   │ │ (HPA)   │ │ (HPA)   │    │
│  └──────────┘ └──────────┘ └──────────┘    │
│  ┌──────────────────┐                       │
│  │ Knowledge Worker │                       │
│  └──────────────────┘                       │
│                                             │
│  ┌────────┐ ┌───────┐ ┌────────┐ ┌──────┐  │
│  │ PG 16  │ │ Redis │ │ Milvus │ │ MinIO│  │
│  └────────┘ └───────┘ └────────┘ └──────┘  │
└─────────────────────────────────────────────┘
```

### Phase 2: Multi-Region (planned)

- GSLB for geo-routing
- PostgreSQL primary (center) + read replicas (edge, <500ms lag)
- Milvus primary (center) + Kafka-synced replicas (edge, <10s lag)
- Independent Redis clusters per region (no cross-region sync)
- 30s failover via GSLB health checks
