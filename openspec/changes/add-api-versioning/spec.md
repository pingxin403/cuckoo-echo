# API Versioning Strategy

## Problem / 问题

Current API lacks explicit versioning strategy:
- All endpoints under `/v1/`
- No deprecation policy
- No backwards compatibility guarantees
- Breaking changes would affect all clients

Enterprise customers need:
- Stable API contracts
- Deprecation timeline
- Migration path

## Background / 背景

Current endpoints:
- `/v1/chat/completions` (SSE)
- `/v1/chat/ws` (WebSocket)
- `/admin/v1/*` (Admin APIs)

Best practices:
- URL versioning (/v1/, /v2/)
- Header versioning (Accept: application/vnd.cuckoo.v1+json)
- Deprecation warnings via headers

## Requirements / 需求

1. **Version Header Support**
   - `Accept: application/vnd.cuckoo.v1+json`
   - `Accept: application/vnd.cuckoo.v2+json`
   - Default to v1 if not specified

2. **Deprecation Policy**
   - 6 months minimum no deprecation
   - Deprecation header on sunsetting endpoints
   - Migration guide for each breaking change

3. **Version Discovery**
   - `GET /versions` endpoint listing available versions
   - `GET /v1/changelog`

4. **Breaking Change Protocol**
   - New version number for breaking changes
   - Parallel support for old versions
   - Clear migration documentation

## Implementation / 实现方案

```python
# api versioning middleware
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

API_VERSION = "v1"
DEPRECATED_VERSIONS = {
    "v1": {"sunset": "2026-12-31", "replacement": "v2"}
}

@app.middleware("http")
async def version_check(request: Request, call_next):
    version = request.headers.get("accept", "").split("v")[-1].split("+")[0]
    
    if version in DEPRECATED_VERSIONS:
        response.headers["Deprecation"] = DEPRECATED_VERSIONS[version]["sunset"]
        response.headers["Link"] = "</v2/changelog>; rel="deprecation""
    
    return await call_next(request)
```

## Acceptance Criteria / 验收标准

- [ ] Accept version header in requests
- [ ] Return API version in response header
- [ ] Document deprecation policy
- [ ] Create /versions endpoint
- [ ] Add deprecation warnings
- [ ] Version-specific OpenAPI specs