# Architecture & Technical Documentation Improvement Specification

## Overview

Comprehensive architecture and technical documentation to support development, onboarding, and operations.

## Goals

- Complete system architecture diagrams
- Comprehensive API documentation
- Data architecture specification
- Security architecture documentation
- Developer onboarding guides

## Technical Design

### 1. System Architecture Diagrams

#### High-Level Architecture
```yaml
# Architecture Components
components:
  frontend:
    - React SPA (Vite)
    - WebSocket client
    - State management (Zustand)

  api_gateway:
    - FastAPI application
    - Authentication (API Key + JWT)
    - Rate limiting
    - Request routing

  services:
    - chat_service: Conversation handling
    - ai_gateway: LLM orchestration
    - admin_service: User management
    - billing_service: Subscription management
    - asr_service: Speech recognition
    - knowledge_pipeline: RAG processing

  data:
    - PostgreSQL: Primary data
    - Redis: Cache and sessions
    - pgvector: Semantic search
    - S3: File storage
```

#### Service Communication
```yaml
# Service Mesh
services:
  chat_service:
    depends_on: [ai_gateway, knowledge_pipeline]
    ports: [8001]
    protocols: [gRPC, HTTP]

  ai_gateway:
    depends_on: [shared]
    ports: [8002]
    protocols: [HTTP, WebSocket]

  knowledge_pipeline:
    depends_on: [shared]
    ports: [8003]
    protocols: [gRPC]
```

### 2. API Documentation

#### OpenAPI Specification Structure
```yaml
openapi: 3.0.0
info:
  title: Cuckoo-Echo API
  version: 1.0.0
  description: Enterprise AI Customer Service API

servers:
  - url: https://api.cuckoo-echo.com
    description: Production
  - url: https://staging.cuckoo-echo.com
    description: Staging

securitySchemes:
  ApiKeyAuth:
    type: apiKey
    in: header
    name: X-API-Key

paths:
  /v1/chat/completions:
    post:
      summary: Create chat completion
      security: [ApiKeyAuth]
      requestBody:
        content:
          application/json:
            schema: ChatCompletionRequest
      responses:
        200:
          description: Streaming response
```

#### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| /v1/chat/completions | POST | Stream chat responses |
| /v1/chat/history | GET | Get conversation history |
| /v1/knowledge/search | POST | Search knowledge base |
| /v1/agents | GET | List AI agents |
| /v1/admin/users | GET | List users (admin) |

### 3. Data Architecture

#### Database Schema
```sql
-- Core Tables
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    agent_id UUID REFERENCES agents(id),
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vector Search
CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Data Flow Diagram
```
┌──────────┐     ┌──────────────┐     ┌─────────────┐
│  Client  │────▶│  API Gateway │────▶│ Chat Service│
└──────────┘     └──────────────┘     └──────┬──────┘
                                             │
                    ┌──────────────┐          │
                    │  AI Gateway  │◀─────────┘
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌─────▼────┐      ┌─────▼─────┐
   │   RAG   │       │  Tools   │      │  Memory   │
   └─────────┘       └──────────┘      └───────────┘
```

### 4. Security Architecture

#### Authentication Flow
```yaml
# API Key Authentication
auth_flow:
  - Client sends X-API-Key header
  - Gateway validates key against database
  - Extract tenant_id and user_id
  - Attach to request context
  - Forward to service

# JWT Admin Authentication
admin_auth:
  - Login with email/password
  - Issue JWT with role claims
  - Validate JWT on each request
  - Check role permissions
```

#### Security Layers
```yaml
security_layers:
  - API Gateway: Rate limiting, IP blocking
  - Application: Input validation, XSS protection
  - Database: Row-level security, parameterized queries
  - Encryption: TLS 1.3, field-level encryption for sensitive data
  - Audit: Request logging, access logs
```

### 5. Infrastructure Architecture

#### Kubernetes Deployment
```yaml
# Deployment Structure
k8s:
  namespace: cuckoo-echo

  services:
    - name: api-gateway
      replicas: 3
      resources:
        cpu: "500m"
        memory: "512Mi"

    - name: chat-service
      replicas: 5
      resources:
        cpu: "1000m"
        memory: "1Gi"

    - name: ai-gateway
      replicas: 3
      resources:
        cpu: "2000m"
        memory: "4Gi"
        nvidia: "1"

  ingress:
    - host: api.cuckoo-echo.com
      paths:
        - /v1/*

  monitoring:
    - prometheus: metrics
    - grafana: dashboards
    - loki: logs
```

### 6. Developer Documentation

#### Getting Started Guide
```yaml
# Development Setup
prerequisites:
  - Docker Desktop
  - Node.js 18+
  - Python 3.11+
  - PostgreSQL 15+
  - Redis 7+

setup_steps:
  - Clone repository
  - Copy .env.example to .env
  - Run docker-compose up -d
  - Run migrations
  - Start development servers
```

#### Coding Standards
```yaml
standards:
  python:
    formatter: ruff
    linter: ruff
    type_checker: pyright
    max_line_length: 100

  typescript:
    formatter: prettier
    linter: eslint
    type_checker: tsc

  commit_messages:
    format: "type(scope): description"
    types: [feat, fix, docs, refactor, test, chore]
```

## Implementation Plan

### Phase 1: Architecture Diagrams
- [ ] 1.1 High-level architecture diagram
- [ ] 1.2 Service communication diagram
- [ ] 1.3 Data flow diagram
- [ ] 1.4 Deployment diagram

### Phase 2: API Documentation
- [ ] 2.1 OpenAPI spec generation
- [ ] 2.2 API reference documentation
- [ ] 2.3 Request/response examples
- [ ] 2.4 Error code documentation

### Phase 3: Data Documentation
- [ ] 3.1 Database schema documentation
- [ ] 3.2 Data model diagrams
- [ ] 3.3 Migration guides
- [ ] 3.4 Data dictionary

### Phase 4: Security & Infrastructure
- [ ] 4.1 Security architecture docs
- [ ] 4.2 Kubernetes deployment docs
- [ ] 4.3 Monitoring setup docs
- [ ] 4.4 Incident response guide

## Acceptance Criteria

- [ ] All architecture diagrams complete
- [ ] API documentation covers all endpoints
- [ ] Database schema documented
- [ ] Security architecture documented
- [ ] Developer onboarding guide complete
- [ ] Infrastructure docs up to date