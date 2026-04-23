# Startup Configuration Validation

## Problem / 问题

Currently services can start with invalid/missing configuration, only failing at runtime when the invalid config is actually used. This leads to:
- Confusing runtime errors
- Late failure discovery
- No centralized config validation

## Background / 背景

The app uses pydantic-settings for configuration:
- DATABASE_URL, REDIS_URL, MILVUS_*, OPENAI_*, etc.

Currently:
- Settings are loaded at import time
- Validation happens only when connections are attempted
- No pre-flight check at startup

## Requirements / 需求

1. **Required Environment Variables**
   - Validate DATABASE_URL format
   - Validate REDIS_URL format
   - Validate MILVUS_* settings
   - Validate AI API keys present

2. **Format Validation**
   - DATABASE_URL must be valid PostgreSQL DSN
   - REDIS_URL must be valid Redis DSN
   - MILVUS_ADDR must be host:port

3. **Dependency Reachability Check**
   - PostgreSQL connectivity check
   - Redis connectivity check
   - Milvus connectivity check (optional, warn-only)

4. **Startup Health Output**
   - Print connected services at startup
   - Print any warnings

## Implementation / 实现方案

```python
# shared/config.py
class Settings(BaseSettings):
    @field_validator("*")
    @classmethod
    def validate_all(cls, v, info):
        name = info.field_name
        if name == "database_url":
            if not valid_pg_dsn(v):
                raise ValueError(f"Invalid DATABASE_URL: {v}")
        # ...
    
    def check_startup(self) -> list[str]:
        """Run startup checks, return warnings."""
        warnings = []
        # Check PostgreSQL
        try:
            create_asyncpg_pool()
        except Exception as e:
            warnings.append(f"PostgreSQL: {e}")
        # ...
        return warnings
```

Or using lifespan:
```python
async def lifespan(app: FastAPI):
    warnings = get_settings().check_startup()
    for w in warnings:
        log.warning("startup", warning=w)
    yield
```

## Acceptance Criteria / 验收标准

- [ ] Invalid DATABASE_URL fails at startup
- [ ] Invalid REDIS_URL fails at startup
- [ ] Missing required vars fail at startup
- [ ] Startup logs show connected services
- [ ] Warnings for optional service failures
- [ ] Config validation tested via unit tests