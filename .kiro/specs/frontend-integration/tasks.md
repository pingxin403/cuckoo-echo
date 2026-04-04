# 实施计划：Cuckoo-Echo 前后端联调

## 概述

将前端 MSW 模拟层替换为真实后端对接。按照"核心适配层 → 网络层改造 → 环境配置 → 基础设施 → 测试"的顺序递增实施，每一步都在前一步基础上构建，确保无孤立代码。

## 任务列表

- [x] 1. Field_Mapper 核心模块
  - [x] 1.1 创建 `frontend/src/network/fieldMapper.ts`，实现 `toCamelCase` / `toSnakeCase` 通用转换函数
    - 安装 `camelcase-keys` 和 `snakecase-keys` 依赖
    - 实现 `toCamelCase<T>(obj)` 和 `toSnakeCase<T>(obj)` 包装函数，启用 `deep: true`
    - 导出 `EXPLICIT_BACKEND_TO_FRONTEND` 和 `EXPLICIT_FRONTEND_TO_BACKEND` 显式规则表（覆盖 `doc_id→id`、`human_transfer_rate→humanEscalationRate`、`query_prefix→query`、`primaryModel→model` 等非标准映射）
    - 实现 `STRUCTURE_ADAPTERS` 结构适配器（overview 计算字段、missed-queries 解包、knowledge doc_id 映射）
    - 实现 `transformResponse(data, endpoint)` 和 `toSnakeCaseWithExplicit(data, endpoint)` 组合转换函数
    - _需求: 1.1, 1.4, 1.5, 7.1, 7.3, 7.4_

  - [x]* 1.2 属性测试：字段映射往返一致性
    - **Property 1: 字段映射往返一致性（Round-Trip）**
    - 创建 `frontend/src/__tests__/pbt/p1-field-mapper-roundtrip.test.ts`
    - 使用 fast-check 生成随机 snake_case 键值对象（1~50 键），验证 `keys(toSnakeCase(toCamelCase(R))) == keys(R)`
    - **验证: 需求 1.5**

  - [x]* 1.3 属性测试：API 响应结构映射完整性
    - **Property 3: API 响应结构映射完整性**
    - 创建 `frontend/src/__tests__/pbt/p3-api-structure-mapping.test.ts`
    - 为 overview、tokens、missed-queries、knowledge、hitl、config 端点生成随机后端响应，验证转换后满足前端类型必需字段
    - **验证: 需求 1.1, 1.4, 7.1, 7.3, 7.4**

  - [x]* 1.4 单元测试：Field_Mapper 显式映射与结构适配
    - 创建 `frontend/src/__tests__/network/fieldMapper.test.ts`
    - 测试显式映射规则、结构适配器、FormData 跳过、嵌套对象转换、边界条件
    - _需求: 1.1, 1.4_

- [x] 2. SSE 与 WebSocket 适配层
  - [x] 2.1 修改 `frontend/src/network/sseClient.ts`，实现 SSE 双格式解析
    - 新增 `extractTokenContent(parsed)` 函数：优先检测 `content` 字段（后端格式），回退到 `choices[0].delta.content`（OpenAI 格式）
    - 新增 `extractError(parsed)` 函数：检测 `CONCURRENT_REQUEST` 等 SSE 错误事件
    - 在 `parseStream` 中替换现有 Token 提取逻辑为 `extractTokenContent`
    - _需求: 4.2, 4.3_

  - [x]* 2.2 属性测试：SSE 双格式解析完整性
    - **Property 2: SSE 双格式解析完整性**
    - 创建 `frontend/src/__tests__/pbt/p2-sse-dual-format.test.ts`
    - 使用 fast-check 生成随机 Token 序列（含中文/英文/特殊字符），随机选择后端/OpenAI 格式编码，验证解析拼接结果一致
    - **验证: 需求 4.2**

  - [x] 2.3 修改 `frontend/src/network/wsClient.ts`，增加 queryParams 和 onOpen 支持
    - 在 `WSClientOptions` 接口中新增 `queryParams?: Record<string, string>` 和 `onOpen?: () => void`
    - `connect` 方法中使用 `URL` + `searchParams.set` 拼接查询参数
    - `ws.onopen` 中调用 `options.onOpen?.()` 回调
    - 处理 WS 关闭码（4001 不重连，1006 指数退避重连）
    - _需求: 5.1, 5.2, 5.5, 5.6_

  - [x]* 2.4 属性测试：指数退避延迟序列
    - **Property 6: 指数退避延迟序列**
    - 创建 `frontend/src/__tests__/pbt/p6-exponential-backoff.test.ts`
    - 使用 fast-check 生成随机连续失败次数（1~20），验证延迟 = `min(1000 * 2^(k-1), 30000)`，成功后重置为 1000ms
    - **验证: 需求 4.6**

- [x] 3. JWT 解码与认证适配
  - [x] 3.1 修改 `frontend/src/stores/authStore.ts`，适配后端 JWT payload
    - 新增 `BackendJWTPayload` 接口（`admin_user_id`、`tenant_id`、`role`、`exp`、`iat`）
    - 实现 `userFromBackendPayload(payload)` 转换函数，处理缺失的 `email` 和 `tenant_name`（使用 `admin_user_id` 和 `tenant_id` 作为回退值）
    - 修改 `login` action 使用 `transformResponse` 处理登录响应
    - 确保 Token 刷新逻辑对接 `POST /admin/v1/auth/refresh`
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x]* 3.2 属性测试：JWT Payload 解码与回退字段
    - **Property 4: JWT Payload 解码与回退字段**
    - 创建 `frontend/src/__tests__/pbt/p4-jwt-payload-decode.test.ts`
    - 使用 fast-check 生成随机 `admin_user_id`、`tenant_id`、`role`，验证转换后 `AdminUser` 所有必需字段非空
    - **验证: 需求 3.2**

  - [x] 3.3 实现 LangGraph 消息格式转换
    - 在 `frontend/src/network/fieldMapper.ts` 或新建 `frontend/src/lib/langGraphAdapter.ts` 中实现 `convertLangGraphMessage(msg, threadId)` 函数
    - 处理 `type` → `role` 映射（human→user, ai→assistant）
    - 处理 `tool_calls` 字段转换
    - 在 chatStore 的线程历史加载中集成此转换
    - _需求: 4.5, 1.4_

  - [x]* 3.4 属性测试：实时消息格式转换完整性
    - **Property 5: 实时消息格式转换完整性**
    - 创建 `frontend/src/__tests__/pbt/p5-realtime-message-convert.test.ts`
    - 使用 fast-check 生成随机 LangGraph 消息和 HITL WS 事件，验证转换后字段完整性和 role 映射正确性
    - **验证: 需求 4.5, 5.3**

- [x] 4. Axios Interceptor 集成与 Store 适配
  - [x] 4.1 修改 `frontend/src/network/axios.ts`，注入 Field_Mapper Interceptor
    - Request Interceptor：对非 FormData 请求体执行 `toSnakeCaseWithExplicit(data, endpoint)` 转换
    - Response Interceptor：执行 `transformResponse(data, endpoint)` 转换（显式映射 → 通用 snake→camel → 结构适配）
    - 扩展错误处理：增加 `ECONNREFUSED` / Network Error 检测，展示"后端服务不可用"Toast
    - 增加 HTTP 413、429 错误码处理
    - _需求: 1.2, 1.3, 2.7, 6.6_

  - [x] 4.2 修改 `frontend/src/stores/adminStore.ts`，适配后端实际响应和路径
    - 修正缓存清除路径：`/admin/v1/cache/clear` → `/admin/v1/config/cache/clear`
    - 修正沙盒路径：`/admin/v1/sandbox/run` → `/admin/v1/metrics/sandbox/run`
    - 处理配置接口 `{updated: true}` 响应（非 HTTP 204）
    - 处理删除文档 `{doc_id, deleted: true}` 响应（非 HTTP 204）
    - _需求: 7.5, 7.6, 7.7, 6.4_

  - [x] 4.3 修改 `frontend/src/stores/chatStore.ts`，集成 SSE 适配和线程历史转换
    - SSE 发送请求体格式对齐后端：`{thread_id, user_id, messages: [{role, content}]}`
    - 集成 `extractTokenContent` 双格式解析
    - 线程历史加载集成 `convertLangGraphMessage` 转换
    - _需求: 4.1, 4.5_

  - [x] 4.4 扩展错误码映射表
    - 修改 `frontend/src/lib/errorMap.ts`（或对应文件），增加 `ERROR_MAP`（401/404/409/413/415/429/500/503）
    - 增加 `SSE_ERROR_MAP`（CONCURRENT_REQUEST/STREAM_TIMEOUT/NETWORK_ERROR）
    - 增加 `WS_CLOSE_MAP`（1000/1006/4001 关闭码处理）
    - _需求: 4.3, 5.5, 2.7_

  - [x]* 4.5 单元测试：Interceptor 集成与 Store 适配
    - 创建 `frontend/src/__tests__/network/axios-interceptor.test.ts`
    - 测试 Request/Response Interceptor 转换、Token 注入、错误映射
    - 测试 adminStore 路径修正和响应处理
    - _需求: 1.2, 1.3, 7.5, 7.6_

- [x] 5. 检查点 — 核心适配层验证
  - 确保所有测试通过，ask the user if questions arise.

- [x] 6. 环境配置与 MSW 条件加载
  - [x] 6.1 修改 `frontend/src/main.tsx`，实现 MSW 条件加载
    - 根据 `import.meta.env.VITE_ENABLE_MSW` 决定是否启用 MSW
    - MSW 禁用时清理残留 Service Worker（`navigator.serviceWorker.getRegistrations` + `unregister`）
    - _需求: 8.1, 8.2, 8.3_

  - [x] 6.2 创建环境配置文件
    - 创建 `frontend/.env.integration`：`VITE_ENABLE_MSW=false`
    - 修改 `frontend/.env.development`（如存在）：确保 `VITE_ENABLE_MSW=true`
    - _需求: 8.4, 2.4_

  - [x] 6.3 修改 `frontend/vite.config.ts`，新增开发代理配置
    - 添加 `/admin/v1/` → `http://localhost:8002` 代理（含 `ws: true`）
    - 添加 `/v1/` → `http://localhost:8000` 代理（含 `ws: true`）
    - 确保 `/admin/v1/` 在 `/v1/` 之前声明（优先匹配）
    - _需求: 2.2, 2.3_

- [x] 7. Nginx 与 Docker Compose 基础设施
  - [x] 7.1 修改 `frontend/nginx.conf`，增加 SSE/WS 优化配置
    - SSE 端点 `/v1/chat/completions`：`proxy_buffering off` + `X-Accel-Buffering no` + `proxy_read_timeout 300s`
    - WS 端点 `/v1/chat/ws` 和 `/admin/v1/ws/`：`Upgrade` + `Connection "upgrade"` + `proxy_read_timeout 300s`
    - 健康检查端点 `/nginx-health`
    - 配置 API 代理路由（`/admin/v1/` → admin-service:8002，`/v1/` → api-gateway:8000）
    - _需求: 2.5, 2.6, 9.3_

  - [x] 7.2 修改 `docker-compose.yml`，新增 frontend 和 seed 服务
    - 新增 `frontend` 服务：构建 `./frontend`，暴露 80 端口，依赖 api-gateway 和 admin-service，健康检查 `/nginx-health`
    - 新增 `seed` 服务：运行 `python -m scripts.seed`，依赖 migrate 完成，幂等创建测试数据
    - _需求: 9.1, 9.2, 9.4, 9.5, 9.6_

  - [x] 7.3 创建 `scripts/seed.py` 幂等种子脚本
    - 创建测试租户（`test-tenant-001`，API Key `ck_test_integration_key`）
    - 创建 Admin 用户（`admin@test.com`，bcrypt 密码）
    - 初始化默认配置（LLM config、rate limit）
    - 所有操作使用 `IF NOT EXISTS` 保证幂等性
    - _需求: 3.6, 9.4, 10.2_

- [x] 8. 检查点 — 基础设施验证
  - 确保所有测试通过，ask the user if questions arise.

- [x] 9. E2E 集成测试配置与场景
  - [x] 9.1 创建 `frontend/playwright.integration.config.ts`
    - `testMatch: '**/*.integration.spec.ts'`
    - `baseURL` 指向 `http://localhost`（Docker Compose 环境）
    - `webServer: undefined`（不启动 Vite dev server）
    - `timeout: 60_000`，`retries: 1`
    - _需求: 10.1, 10.4_

  - [x]* 9.2 创建 E2E 集成测试：Admin 登录
    - 创建 `frontend/e2e/login.integration.spec.ts`
    - 使用 Seed 数据中的 Admin 用户登录，验证真实 JWT 签发、页面跳转、用户信息展示
    - _需求: 10.3_

  - [x]* 9.3 创建 E2E 集成测试：聊天流程
    - 创建 `frontend/e2e/chat.integration.spec.ts`
    - 使用 Seed 数据中的 API Key 发送消息，验证 SSE 流式响应和 Token 拼接
    - _需求: 10.3_

  - [x]* 9.4 创建 E2E 集成测试：知识库上传
    - 创建 `frontend/e2e/knowledge.integration.spec.ts`
    - 上传测试文件，验证文件处理状态轮询和字段映射
    - _需求: 10.3_

  - [x]* 9.5 创建 E2E 集成测试：HITL 流程
    - 创建 `frontend/e2e/hitl.integration.spec.ts`
    - 验证 WebSocket 连接、HITL 事件接收、会话接管
    - _需求: 10.3_

- [x] 10. 最终检查点 — 全部测试通过
  - 确保所有测试通过，ask the user if questions arise.
  - **验证命令**：
    - 单元测试 + PBT：`pnpm test`
    - 构建验证：`pnpm build`
    - E2E 集成测试：`pnpm exec playwright test --config playwright.integration.config.ts`

- [ ] 11. 联调验证 Checklist
  - [ ] 11.1 验证 C 端 API Key 鉴权：使用 Seed 中的 API Key 发送消息
  - [ ] 11.2 验证 SSE 流式：观察逐字输出效果，确认 Token 实时推送
  - [ ] 11.3 验证 WebSocket HITL：触发人工介入，Admin 端接管会话
  - [ ] 11.4 验证文件上传：上传图片/文档，观察处理状态轮询
  - [ ] 11.5 验证 Admin 登录：JWT 签发、Token 刷新、过期重定向
  - [ ] 11.6 验证指标接口：数据看板展示正确（字段映射 + 计算字段）
  - [ ] 11.7 验证错误处理：后端不可用时前端展示"后端服务不可用"提示

- [ ] 12. 故障排查指南
  - [ ] 12.1 SSE 无输出：检查 Nginx `proxy_buffering off` 和 `X-Accel-Buffering: no`
  - [ ] 12.2 WS 连接失败：检查 Vite proxy `ws: true` 和 Nginx `Upgrade` 头
  - [ ] 12.3 字段映射错误：在 `transformResponse` 中添加 `console.debug` 日志，对比后端原始响应与转换结果
  - [ ] 12.4 认证失败：检查 JWT payload 字段名（`admin_user_id` vs `sub`）和 Token 过期时间

---

## 阶段二：SSE Token 流修复与 RAG 完整链路

- [ ] 13. SSE Token 流修复
  - [ ] 13.1 调试 LangGraph `astream_events` 在 Ollama 模型下的 token 输出格式
    - 检查 `on_chat_model_stream` 事件的 `chunk.content` 是否为空（qwen3 thinking 模式可能将 token 放在 `additional_kwargs`）
    - 在 `chat_service/routes/chat.py` 的 `event_generator` 中添加调试日志，记录每个 chunk 的完整结构
    - 确认 LiteLLM `acompletion(stream=True)` 对 Ollama 模型的 chunk 格式
  - [ ] 13.2 修复 `event_generator` 确保 token 正确提取并通过 SSE 推送
    - 如果 `chunk.content` 为空但 `chunk.additional_kwargs` 有内容，提取 thinking token
    - 对 Ollama 模型添加 `stream_options` 兼容处理（Ollama 可能不支持 `include_usage`）
    - 确保 `[DONE]` 标记在所有 token 发送完毕后才发出
  - [ ] 13.3 前端验证：确认 ChatWidget 能显示逐字流式效果
    - 通过 Chrome DevTools 或 E2E 测试验证 SSE token 实时显示
    - 验证 `appendToken` → `finishStreaming` 完整链路
    - 更新 E2E chat 测试：验证 assistant 消息 bubble 出现且包含文本内容

- [ ] 14. 知识库完整 RAG 链路
  - [ ] 14.1 初始化 Milvus collection 和索引
    - 创建 `scripts/init_milvus.py`：创建 `knowledge_chunks` collection（dense_vector COSINE + sparse_vector BM25 + doc_id + tenant_id + chunk_text 字段）
    - 在 Docker Compose 中添加 `init-milvus` 服务（依赖 milvus healthy）
    - 确保 collection 创建幂等（`has_collection` 检查）
  - [ ] 14.2 配置 Embedding 服务连接
    - 验证 `shared/embedding_service.py` 能通过 `ollama/qwen3-embedding` 模型生成向量
    - 在 `chat_service/main.py` 的 `_wire_dependencies` 中确认 embedding_service 初始化成功
    - 测试：`curl` 调用 Ollama embedding API 确认返回向量维度
  - [ ] 14.3 验证文档上传→处理→向量化完整流程
    - 通过 Admin 界面上传测试文档（TXT/PDF）
    - 检查 `knowledge_pipeline` worker 日志：parse → chunk → embed → insert
    - 验证 Milvus 中有对应的向量数据（`pymilvus` query 检查）
    - 验证文档状态从 `pending` → `processing` → `completed`
  - [ ] 14.4 验证 RAG 检索链路
    - 发送与上传文档内容相关的聊天消息
    - 检查 chat-service 日志：`rag_engine_node` 是否返回 `rag_context`
    - 验证 LLM 回复中包含知识库内容（非纯 chitchat 回复）
  - [ ]* 14.5 E2E 测试：知识库上传后 RAG 检索
    - 上传测试文档 → 等待处理完成 → 发送相关问题 → 验证回复包含文档内容

- [ ] 15. HITL 完整流程
  - [ ] 15.1 验证 chat-service router 节点的 `human_transfer` 意图触发条件
    - 检查 `chat_service/agent/nodes/router.py` 的路由逻辑
    - 确认哪些用户输入会触发 `human_transfer`（如"转人工"、"人工客服"）
    - 如果 router 不支持，添加关键词匹配规则
  - [ ] 15.2 验证 HITL WebSocket 事件推送
    - 在 C 端发送"转人工"消息
    - 检查 Admin HITL WebSocket 是否收到 `hitl_request` 事件
    - 验证 HITLPanel 显示待处理会话
  - [ ] 15.3 验证会话接管和消息发送
    - Admin 点击"接管"按钮
    - 验证会话状态变为 `active`
    - Admin 发送消息，验证 C 端收到
  - [ ] 15.4 验证结束介入
    - Admin 点击"结束介入"
    - 验证会话状态恢复，C 端回到 AI 对话模式
  - [ ]* 15.5 E2E 测试：HITL 完整流程
    - C 端发送"转人工" → Admin 接管 → Admin 发消息 → Admin 结束介入

- [ ] 16. 检查点 — 核心功能验证
  - 确保 SSE 流式、RAG 检索、HITL 流程均可正常工作
  - **验证命令**：
    - 前端测试：`cd frontend && pnpm test`
    - E2E 测试：`cd frontend && pnpm exec playwright test --config playwright.integration.config.ts`

---

## 阶段三：产品化与 CI/CD

- [ ] 17. 性能优化
  - [ ] 17.1 SSE 首 token 延迟优化
    - 测量当前 SSE 首 token 延迟（从发送到第一个 token 到达前端的时间）
    - 如果 > 5s，检查 Ollama 模型加载时间、LangGraph 图执行开销
    - 考虑添加 SSE `ping` 事件让前端知道连接已建立
  - [ ] 17.2 Nginx 静态资源缓存策略
    - 验证 `/assets/` 路径的 `Cache-Control: immutable` 生效
    - 添加 gzip 压缩配置（`gzip on; gzip_types text/plain application/json application/javascript text/css;`）
  - [ ]* 17.3 前端 bundle 分析
    - 运行 `vite-bundle-visualizer` 分析 chunk 大小
    - 确认 vendor 分包合理（react、recharts、radix 独立 chunk）

- [ ] 18. 多租户隔离 E2E 验证
  - [ ] 18.1 创建第二个测试租户（seed.py 扩展）
    - 新增 tenant-002 + 独立 API Key + 独立 Admin 用户
  - [ ] 18.2 E2E 测试：租户 A 的数据对租户 B 不可见
    - 租户 A 上传文档 → 租户 B 查询知识库 → 验证看不到租户 A 的文档
    - 租户 A 的聊天历史对租户 B 不可见
  - [ ]* 18.3 E2E 测试：API Key 隔离
    - 使用租户 A 的 API Key 无法访问租户 B 的数据

- [ ] 19. CI/CD 集成
  - [ ] 19.1 创建 `.github/workflows/ci.yml` GitHub Actions 工作流
    - 后端：`uv sync` → `make test` → `make test-pbt`
    - 前端：`pnpm install` → `pnpm test` → `pnpm build`
    - 触发条件：push to main、PR
  - [ ] 19.2 创建 `.github/workflows/e2e.yml` E2E 测试工作流
    - `docker compose up -d` → 等待健康检查 → `pnpm exec playwright test --config playwright.integration.config.ts`
    - 上传 Playwright 报告为 artifact
    - 触发条件：PR（手动触发或 label 触发）
  - [ ] 19.3 Ragas 质量门禁集成
    - 在 CI 中运行 `make quality-gate`
    - 阈值不通过时 CI 失败
    - 生成质量报告并上传为 artifact

- [ ] 20. 最终检查点 — 产品化验证
  - 确保所有测试通过，CI/CD 流水线正常运行
  - **验证命令**：
    - 全部后端测试：`make test-all`
    - 全部前端测试：`cd frontend && pnpm test`
    - E2E 集成测试：`cd frontend && pnpm exec playwright test --config playwright.integration.config.ts`
    - Ragas 质量门禁：`make quality-gate`

## 备注

- 标记 `*` 的子任务为可选，可跳过以加速 MVP
- 每个任务引用具体需求编号，确保可追溯性
- 属性测试验证设计文档中的正确性属性（P1-P6）
- 现有 PBT 文件（`p1-sse-token-roundtrip.test.ts` 等）属于 frontend-ui spec，本 spec 的 PBT 使用独立文件名（`p1-field-mapper-roundtrip.test.ts` 等）避免冲突
- Seed 脚本已有 `scripts/seed_tenant.py`，新建 `scripts/seed.py` 整合完整测试数据创建
- 阶段一（Task 1-12）：前后端联调适配层 — 已完成核心实现
- 阶段二（Task 13-16）：SSE Token 流修复 + RAG 完整链路 + HITL 完整流程
- 阶段三（Task 17-20）：性能优化 + 多租户隔离验证 + CI/CD 集成
