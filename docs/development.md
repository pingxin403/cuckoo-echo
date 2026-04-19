# Development Guide / 开发指南

## Prerequisites / 前置条件

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` or `brew install uv` |
| Docker | 24+ | [docker.com](https://docs.docker.com/get-docker/) |
| Docker Compose | v2+ | Included with Docker Desktop |

---

## Environment Setup / 环境搭建

### 1. Clone and install dependencies

```bash
git clone <repo-url> cuckoo-echo
cd cuckoo-echo
uv sync  # Installs all dependencies from pyproject.toml + uv.lock
```

### 2. Start infrastructure

```bash
docker compose up -d  # PostgreSQL, Redis, Milvus, MinIO
```

Verify services are running:

```bash
docker compose ps
# postgres   running  0.0.0.0:5432->5432/tcp
# redis      running  0.0.0.0:6379->6379/tcp
# milvus     running  0.0.0.0:19530->19530/tcp
# minio      running  0.0.0.0:9000->9000/tcp, 0.0.0.0:9001->9001/tcp
```

### 3. Run database migrations

```bash
make migrate
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your settings (defaults work for local development)
```

Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/cuckoo` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `MILVUS_URI` | `http://localhost:19530` | Milvus endpoint |
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO endpoint |
| `ENVIRONMENT` | `development` | App environment |
| `LOG_LEVEL` | `INFO` | Logging level |

### 5. Seed test data (optional)

```bash
make seed  # Creates a test tenant and prints the API key
```

### 6. Start development server

**Option A: Hybrid (recommended)** - Docker for infrastructure, local for services

```bash
# Windows PowerShell:
.\scripts\dev-local.ps1

# Or manually:
docker compose -f docker-compose.dev.yml up -d  # Only infrastructure
uv run alembic upgrade head                     # Migrations

# Then in separate terminals:
uvicorn api_gateway.main:app --reload --port 8000   # Terminal 1
uvicorn chat_service.main:app --reload --port 8001   # Terminal 2
python -m admin_service.main                           # Terminal 3
cd frontend && pnpm dev                              # Terminal 4 (optional)
```

Benefits:
- No Docker build issues (skip docker.io mirror problems)
- Fast iteration - code changes reflect immediately with uvicorn --reload
- Debug directly in IDE
- Full control over service logs

**Option B: Full Docker** - All services in containers

```bash
# Single service (API Gateway with hot-reload)
make dev

# All services with hot-reload
make dev-all
```

#### Hot-Reload 说明

`docker-compose.override.yml` 在 `docker compose up` 时自动加载，提供：
- 所有应用服务使用 `uvicorn --reload` 替代 `granian`（granian 不支持热重载）
- 源码目录通过 volume mount 映射到容器内 `/app/`
- 修改本地 Python 文件后，容器内 uvicorn 自动检测变更并重启服务

如果不需要热重载（如测试生产配置），使用：
```bash
docker compose -f docker-compose.yml up  # 仅加载主文件，使用 granian
```

---

## Running Tests / 运行测试

### Unit Tests / 单元测试

```bash
make test
# or
uv run pytest tests/unit/ -v
```

### Property-Based Tests / 属性测试

Uses [Hypothesis](https://hypothesis.readthedocs.io/) for property-based testing.

```bash
uv run pytest tests/pbt/ -v
```

### Integration Tests / 集成测试

Requires running Docker infrastructure (PostgreSQL, Milvus, Redis).

```bash
make test-integration
# or
uv run pytest tests/integration/ -m integration -v
```

### End-to-End Tests / 端到端测试

Requires full stack running via `docker compose up`.

```bash
make test-e2e
# or
uv run pytest tests/e2e/ -m e2e -v
```

### All Tests / 全部测试

```bash
uv run pytest tests/ -v
```

### Test Coverage

```bash
uv run pytest tests/unit/ tests/pbt/ --cov=. --cov-report=term-missing
```

---

## Code Style / 代码规范

### Ruff (Linter + Formatter)

The project uses [Ruff](https://docs.astral.sh/ruff/) for both linting and formatting.

Configuration in `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py311"
line-length = 120
```

```bash
# Check for lint errors
make lint
# or
uv run ruff check .

# Auto-format code
make format
# or
uv run ruff format .

# Auto-fix lint errors
uv run ruff check --fix .
```

### Pre-commit Hooks

Install pre-commit hooks to auto-check on every commit:

```bash
make pre-commit
# or
uv run pre-commit install
```

The `.pre-commit-config.yaml` runs ruff check + format on staged files.

### Conventions

- **Type hints**: Required for all public function signatures
- **Logging**: Use `structlog.get_logger()` — never `print()` or `logging.getLogger()`
- **JSON serialization**: Use `orjson` for performance-critical paths (SSE streaming)
- **Async**: All I/O operations must be async (`async/await`)
- **Imports**: Sorted by ruff (isort-compatible)

---

## IDE Setup / IDE 配置

### VS Code

Recommended extensions:

```json
{
  "recommendations": [
    "charliermarsh.ruff",
    "ms-python.python",
    "ms-python.vscode-pylance"
  ]
}
```

Settings (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "python.analysis.typeCheckingMode": "basic"
}
```

### PyCharm

1. Set project interpreter to `.venv/bin/python`
2. Install Ruff plugin from JetBrains Marketplace
3. Enable "Ruff" as external formatter: Settings → Tools → Ruff
4. Mark `tests/` as Test Sources Root
5. Configure pytest as default test runner: Settings → Tools → Python Integrated Tools → pytest

---

## Makefile Commands / 常用命令

```bash
make install        # uv sync
make test           # Unit tests
make test-integration  # Integration tests (requires Docker)
make test-e2e       # E2E tests (requires full stack)
make lint           # Ruff check
make format         # Ruff format
make pre-commit     # Install pre-commit hooks
make up             # docker compose up -d
make down           # docker compose down
make migrate        # Run SQL migrations
make dev            # Start API Gateway (uvicorn --reload)
make dev-all        # Start all services (hot-reload)
make seed           # Create test tenant
make logs           # View all service logs
make clean          # Remove all Docker volumes
```
