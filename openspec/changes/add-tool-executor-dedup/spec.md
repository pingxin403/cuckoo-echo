# Add Tool Executor Deduplication

## Overview

Consolidate duplicate tool_executor.py files into single implementation.

## Motivation

Two tool_executor.py files exist:
- `chat_service/agent/tool_executor.py`
- `chat_service/agent/nodes/tool_executor.py`

This duplication causes maintenance burden and confusion.

## Specification

### Core Features

1. **Consolidate**
   - Keep `chat_service/agent/tool_executor.py` as canonical
   - Update imports in dependent files
   - Remove `chat_service/agent/nodes/tool_executor.py`

2. **Update Imports**
   - `chat_service/agent/graph.py`: Import from canonical location
   - `chat_service/agent/nodes/__init__.py`: Export from canonical
   - `chat_service/agent/nodes/guardrails.py`: Import from canonical

3. **Preserve History**
   - Git mv to preserve history
   - Update all import paths

### File Changes

- Delete: `chat_service/agent/nodes/tool_executor.py`
- Update: All files importing tool_executor

## Acceptance Criteria

- [ ] Single tool_executor.py implementation
- [ ] All imports updated
- [ ] No functional change
- [ ] Git history preserved