# Tech Debt: Python 3.9 Compatibility Specification

## Overview

Fix Python 3.9 compatibility issues by replacing `str.removeprefix()` and other Python 3.11+ only features.

## Background

Current code uses Python 3.11+ features but `pyproject.toml` may need to support 3.9-3.10. Found `str.removeprefix()` usage in:

- `chat_service/agent/tool_executor.py:21` - `user_intent.removeprefix("tool:")`
- `chat_service/main.py:216` - `auth.removeprefix("Bearer ")`

## Technical Approach

Replace with `startswith()` + `slice`:

```python
# Before (Python 3.11+)
tool_name = user_intent.removeprefix("tool:")

# After (Python 3.9+)
tool_name = user_intent[5:] if user_intent.startswith("tool:") else user_intent
```

## Files to Fix

1. `chat_service/agent/tool_executor.py` - Line 21
2. `chat_service/main.py` - Line 216

## Acceptance Criteria

- [x] Replace all `removeprefix()` calls with compatible alternatives
- [x] Verify tests still pass
- [x] No functional changes to behavior