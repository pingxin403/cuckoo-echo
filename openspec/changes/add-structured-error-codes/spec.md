# Add Structured Error Codes

## Overview

Define standard error code taxonomy for consistent error handling and API responses.

## Motivation

Current error handling uses ad-hoc error messages. Need structured error codes for:
- Client error handling
- Error analytics
- User-facing localization
- API documentation

## Specification

### Error Code Taxonomy

```python
class ErrorCode(Enum):
    # Input Validation (1000-1999)
    INVALID_INPUT = 1001
    MISSING_REQUIRED_FIELD = 1002
    INVALID_TENANT_ID = 1003
    INVALID_THREAD_ID = 1004
    INPUT_TOO_LONG = 1005

    # RAG Errors (2000-2999)
    RAG_UNAVAILABLE = 2001
    RAG_TIMEOUT = 2002
    RAG_NO_RESULTS = 2003
    EMBEDDING_FAILED = 2004
    RERANK_FAILED = 2005

    # LLM Errors (3000-3999)
    LLM_TIMEOUT = 3001
    LLM_UNAVAILABLE = 3002
    LLM_RATE_LIMIT = 3003
    LLM_INVALID_RESPONSE = 3004

    # Auth Errors (4000-4999)
    UNAUTHORIZED = 4001
    FORBIDDEN = 4002
    INVALID_API_KEY = 4003
    TENANT_INACTIVE = 4004

    # Internal Errors (5000-5999)
    INTERNAL_ERROR = 5001
    DATABASE_ERROR = 5002
    REDIS_ERROR = 5003
    CIRCUIT_OPEN = 5004
```

### File Changes

- `shared/errors.py`: Error codes and exception classes
- Update all nodes to use structured errors

## Acceptance Criteria

- [ ] ErrorCode enum defined
- [ ] API returns structured error response
- [ ] All nodes use error codes
- [ ] Error docs generated