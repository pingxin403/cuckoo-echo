# 🚀 Cuckoo-Echo 本地快速启动指南

本指南帮助你在 5 分钟内启动完整的 Cuckoo-Echo 开发环境。

## 前置条件

| 工具 | 版本 | 安装方式 |
|------|------|---------|
| Docker Desktop | 4.x+ | [下载](https://www.docker.com/products/docker-desktop/) |
| Node.js | 20+ | [下载](https://nodejs.org/) |
| pnpm | 9+ | `npm install -g pnpm` |
| Python | 3.11+ | [下载](https://www.python.org/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Ollama (可选) | latest | [下载](https://ollama.com/) |

## 方式一：Docker Compose 全栈启动（推荐）

适合快速体验完整功能，无需本地安装 Python 依赖。

```bash
# 1. 克隆项目
git clone <repo-url> && cd cuckoo-echo

# 2. 配置环境变量
cp .env.example .env.docker
# 编辑 .env.docker，配置 LLM API Key（见下方"模型配置"）

# 3. 启动全部服务（首次构建约 3-5 分钟）
docker compose up -d

# 4. 查看服务状态
docker compose ps

# 5. 访问
#   前端管理后台: http://localhost/login
#   登录账号: admin@test.com / test123456
#   C端聊天: http://localhost/chat?api_key=ck_test_integration_key
```

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Frontend (Nginx) | 80 | 前端 + API 反向代理 |
| API Gateway | 8000 | C端 API 鉴权 + 限流 |
| Chat Service | 8001 | 聊天 + SSE 流式 |
| Admin Service | 8002 | 管理后台 API |
| PostgreSQL | 5432 | 主数据库 |
| Redis | 6379 | 缓存 + 分布式锁 |
| Milvus | 19530 | 向量数据库 |
| MinIO | 9000/9001 | 对象存储 |

## 方式二：本地开发模式

适合需要修改代码并热重载的开发场景。

```bash
# 1. 安装后端依赖
uv sync

# 2. 启动基础设施
docker compose up -d postgres redis milvus minio

# 3. 数据库迁移
make migrate

# 4. 创建测试数据
make seed

# 5. 启动后端服务（3 个终端）
uv run uvicorn api_gateway.main:app --reload --port 8000
uv run uvicorn chat_service.main:app --reload --port 8001
uv run uvicorn admin_service.main:app --reload --port 8002

# 6. 启动前端
cd frontend && pnpm install && pnpm dev
# 访问 http://localhost:5173
```

## 模型配置

### 使用本地 Ollama（推荐，免费）

```bash
# 安装模型
ollama pull qwen3:8b          # 聊天模型
ollama pull qwen3-embedding   # Embedding 模型（RAG 用）
ollama pull qwen3-vl          # 多模态模型（可选）
```

`.env.docker` 配置：
```env
LLM_PRIMARY_MODEL=ollama/qwen3:8b
LLM_FALLBACK_MODEL=ollama/qwen3:8b
LLM_API_BASE=http://host.docker.internal:11434
LLM_API_KEY=ollama
LLM_FALLBACK_TIMEOUT=120.0
EMBEDDING_MODEL=ollama/qwen3-embedding
VISION_MODEL=ollama/qwen3-vl
```

### 使用云端 API

```env
# DeepSeek
LLM_PRIMARY_MODEL=deepseek-chat
LLM_API_KEY=sk-xxx
LLM_API_BASE=https://api.deepseek.com/v1

# OpenAI
LLM_PRIMARY_MODEL=gpt-4o-mini
LLM_API_KEY=sk-xxx
```

## 运行测试

```bash
# 后端单元测试
make test

# 后端属性测试 (Hypothesis PBT)
uv run pytest tests/pbt/ -v

# 前端单元测试 + PBT
cd frontend && pnpm test

# 前端 E2E 集成测试（需要 Docker Compose 运行中）
cd frontend && pnpm exec playwright test --config playwright.integration.config.ts

# RAG 质量评估 (Ragas)
make quality-gate
```

## 常见问题

### Docker 构建失败
```bash
# 清理重建
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### Milvus 镜像拉取失败（中国网络）
使用镜像加速：
```bash
# 在 docker-compose.yml 中替换镜像前缀
# milvusdb/milvus:v2.5.6 → docker.1ms.run/milvusdb/milvus:v2.5.6
```

### chat-service 启动失败
查看日志：`docker compose logs chat-service --tail=30`
常见原因：缺少 `psycopg[binary]`、LangGraph 版本不兼容。

### 登录后跳回登录页
检查 Axios 拦截器是否正确处理 `access_token` → `accessToken` 字段转换。
