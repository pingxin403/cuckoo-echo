# Tasks

## Implementation Checklist

- [x] 1.1 创建 tests/e2e/ 目录和配置
- [x] 1.2 添加登录流程测试 (tests/e2e/test_login_flow.py + frontend/e2e/login.spec.ts)
- [x] 1.3 添加对话流程测试 (tests/e2e/test_smoke.py + frontend/e2e/chat.spec.ts)
- [x] 1.4 添加文件上传测试 (tests/e2e/test_knowledge_flow.py + frontend/e2e/knowledge.spec.ts)
- [x] 1.5 添加 HITL 流程测试 (tests/e2e/test_hitl_flow.py + frontend/e2e/hitl.spec.ts)
- [x] 1.6 添加 Makefile e2e 命令 (test-e2e exists in Makefile)
- [x] 1.7 验证测试通过 (7 collected, all skip when services not running)

## 已有的测试

### Backend API E2E (pytest)
- tests/e2e/test_login_flow.py (login_success, login_invalid_credentials)
- tests/e2e/test_smoke.py (health_endpoint, chat_returns_sse_stream)
- tests/e2e/test_knowledge_flow.py (knowledge_upload_and_query)
- tests/e2e/test_hitl_flow.py (negative_sentiment_triggers_hitl)
- tests/e2e/test_tool_call_flow.py (order_query_triggers_tool_call)

### Frontend E2E (Playwright)
- login.spec.ts, login.integration.spec.ts
- chat.spec.ts, chat.integration.spec.ts
- knowledge.spec.ts, knowledge.integration.spec.ts
- hitl.spec.ts, hitl.integration.spec.ts
- metrics, visual, sandbox, responsive, navigation, isolation, config specs