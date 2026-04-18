# System Architecture

## Overview

Cuckoo-Echo is a multi-tenant AI Customer Service SaaS platform built with FastAPI + React.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + TypeScript |
| Backend | FastAPI + Python 3.11 |
| Database | PostgreSQL + Redis |
| LLM | OpenAI / Anthropic / Azure OpenAI |
| Vector DB | pgvector |
| Deployment | Docker + K8s |

## System Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   Gateway   │────▶│  AI Engine  │
│  (React)    │     │  (FastAPI) │     │   (LLM)     │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                    ┌──────┴──────┐     ┌──────┴──────┐
                    │  Knowledge  │     │   Tools    │
                    │    (RAG)    │     │ Executor  │
                    └─────────────┘     └─────────────┘
```

## Multi-Tenant Isolation

- **API Key**: Tenant-scoped `ck_xxx` prefix
- **Database**: Row-level security with `tenant_id`
- **Cache**: Redis namespace per tenant
- **LLM**: Separate model configurations

## Data Flow

1. Request → API Gateway (authentication, rate limiting)
2. Queue → Agent (async processing)
3. LLM → Tool Executor (function calling)
4. RAG → Knowledge Base (context retrieval)
5. Response → SSE/WebSocket stream

## Security

- API Key authentication
- JWT admin tokens
- Tenant isolation at all layers
- Input/output sanitization