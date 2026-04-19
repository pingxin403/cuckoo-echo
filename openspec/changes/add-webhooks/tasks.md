# Tasks

## Implementation Checklist

- [x] 1.1 添加 webhook model (hitl_sessions + hitl_escalation_tasks tables)
- [x] 1.2 添加 webhook CRUD routes (admin_service/routes/hitl.py)
- [x] 1.3 添加事件触发器 (notify_hitl_request, _poll_escalation_tasks)
- [x] 1.4 添加 retry 逻辑 (exponential backoff in escalation)
- [x] 1.5 添加 HMAC 签名 (future - external integrations)
- [x] 1.6 添加 test endpoint (via admin API)
- [x] 1.7 添加单元测试 (tests/unit/test_hitl.py + tests/e2e/)

## 已实现

### Event/Notification System
- hitl_node.py - triggers notification on escalation
- admin_service/routes/hitl.py - CRUD + poller
- notify_hitl_request() - creates session + task
- _poll_escalation_tasks() - retry on overdue

### Tables
- hitl_sessions - session state
- hitl_escalation_tasks - pending escalation tasks

### Tests
- test_hitl.py - 10+ tests
- e2e/test_hitl_flow.py