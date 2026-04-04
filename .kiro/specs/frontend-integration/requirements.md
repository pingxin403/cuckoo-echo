# 需求文档：Cuckoo-Echo 前后端联调

## 简介

Cuckoo-Echo 后端已完成全部 10 个阶段的开发（303 测试，54 次提交），前端 UI 也已完成全部组件实现（136 测试）。当前前端通过 MSW（Mock Service Worker）模拟所有 API 调用，尚未与真实后端服务对接。

本需求文档定义前后端联调的功能范围，涵盖：API 契约验证（前端类型/MSW Handler 与后端真实响应的字段映射差异）、环境配置、认证流程对接、SSE/WebSocket 实时通信对接、文件上传对接、Admin API 对接、Docker Compose 全栈部署、以及基于真实服务的 E2E 测试。

**前置条件：** 后端服务（API Gateway :8000、Admin Service :8002、Chat Service :8001）可用且数据库已迁移。

---

## 词汇表

- **Integration_Layer**：前后端联调适配层，负责将前端类型定义与后端 API 响应进行字段映射转换
- **API_Contract**：前端 TypeScript 类型定义与后端 API 实际返回 JSON 之间的字段名称和结构约定
- **Field_Mapper**：字段映射转换函数，将后端 snake_case 响应转换为前端 camelCase 类型
- **MSW**：Mock Service Worker，前端开发阶段使用的 API 模拟工具
- **API_Gateway**：C 端 API 网关服务，运行于 :8000 端口，使用 API Key 鉴权
- **Admin_Service**：管理后台 API 服务，运行于 :8002 端口，使用 JWT 鉴权
- **Chat_Service**：聊天服务，运行于 :8001 端口，由 API_Gateway 内部转发
- **SSE_Endpoint**：`POST /v1/chat/completions`，后端 SSE 流式聊天接口
- **WS_Chat_Endpoint**：`WS /v1/chat/ws`，C 端 WebSocket 双向聊天接口
- **WS_HITL_Endpoint**：`WS /admin/v1/ws/hitl`，Admin 端 HITL 实时 WebSocket 接口
- **Vite_Proxy**：Vite 开发服务器的代理配置，将 API 请求转发至后端服务
- **Nginx_Proxy**：生产环境 Nginx 反向代理，统一前后端入口
- **E2E_Test**：端到端测试，基于 Playwright 在真实前后端服务上运行
- **Docker_Compose_Stack**：包含前端 + 后端全部服务的 Docker Compose 编排
- **Seed_Script**：数据库种子脚本，为 E2E 测试创建测试租户、API Key 和 Admin 用户

---

## 需求列表

### 需求 1：API 契约验证与字段映射

**用户故事：** 作为前端开发者，我希望前端类型定义与后端 API 实际响应保持一致，以避免联调时因字段名不匹配导致的运行时错误。

#### 验收标准

1. THE Integration_Layer SHALL 提供 Field_Mapper 模块，将后端 snake_case JSON 响应转换为前端 camelCase TypeScript 类型。以下字段映射 SHALL 被覆盖：

| 后端字段（snake_case） | 前端字段（camelCase） | 所属接口 |
|------------------------|----------------------|----------|
| `session_id` | `sessionId` | HITL 相关接口 |
| `thread_id` | `threadId` | 聊天/HITL 接口 |
| `admin_user_id` | `adminUserId` | HITL 接口 |
| `unresolved_turns` | `unresolvedTurns` | HITL 接口 |
| `created_at` | `createdAt` | 通用时间戳 |
| `updated_at` | `updatedAt` | 通用时间戳 |
| `chunk_count` | `chunkCount` | 知识库接口 |
| `error_msg` | `errorMsg` | 知识库接口 |
| `doc_id` | `id` | 知识库接口 |
| `system_prompt` | `systemPrompt` | 配置接口 |
| `persona_name` | `personaName` | 配置接口 |
| `tenant_rps` | `tenantRps` | 限流配置接口 |
| `user_rps` | `userRps` | 限流配置接口 |
| `total_conversations` | `totalConversations` | 指标接口 |
| `human_transfer_count` | `humanTransferCount` | 指标接口 |
| `human_transfer_rate` | `humanEscalationRate` | 指标接口 |
| `total_tokens` | `totalTokensUsed` | Token 指标接口 |
| `message_count` | `messageCount` | Token 指标接口 |
| `query_prefix` | `query` | 未命中查询接口 |

2. THE Integration_Layer SHALL 在 Axios Response Interceptor 中自动执行 snake_case → camelCase 转换，确保所有 API 响应在到达 Zustand Store 之前已完成字段映射。
3. THE Integration_Layer SHALL 在 Axios Request Interceptor 中自动执行 camelCase → snake_case 转换，确保所有请求体在发送至后端之前已完成字段映射。
4. WHEN 后端 API 响应结构与前端 MSW Handler 模拟的结构存在差异时，THE Integration_Layer SHALL 在 Field_Mapper 中处理结构差异。已知差异包括：
   - 后端 `GET /admin/v1/metrics/overview` 返回 `{total_conversations, human_transfer_count, human_transfer_rate, range}`，前端 `MetricsOverview` 类型期望 `{totalConversations, aiResolutionRate, humanEscalationRate, avgTtftMs, totalTokensUsed, ...}`
   - 后端 `GET /admin/v1/metrics/missed-queries` 返回 `{missed_queries: [{query_prefix, count}]}` 包裹对象，前端期望直接数组 `[{query, count}]`
   - 后端 `GET /admin/v1/knowledge/docs/{id}` 返回 `{doc_id, status, chunk_count, error_msg}`，前端 `KnowledgeDoc` 类型期望 `{id, filename, status, chunkCount, errorMsg, createdAt, updatedAt}`
   - 后端 `POST /admin/v1/auth/login` 返回 `{access_token, token_type, expires_in}`，不包含用户信息；前端需从 JWT payload 中解码用户信息
   - 后端 `GET /v1/threads/{thread_id}` 返回 `{thread_id, messages: [LangGraph message objects]}`，前端期望 `{messages: Message[]}`（需转换 LangGraph 消息格式）
5. FOR ALL 后端 API 端点，Field_Mapper 的 snake_case → camelCase 转换 SHALL 满足往返一致性：对于任意后端响应 `R`，`toSnakeCase(toCamelCase(R))` 的键集合 SHALL 等于 `R` 的键集合。


---

### 需求 2：环境配置与代理

**用户故事：** 作为前端开发者，我希望通过环境变量和代理配置将前端请求路由到真实后端服务，以便在开发和生产环境中无缝切换。

#### 验收标准

1. THE Integration_Layer SHALL 支持通过 `VITE_API_BASE_URL` 环境变量配置 API 基础地址。WHEN 该变量未设置时，SHALL 默认使用相对路径（空字符串），依赖 Nginx 或 Vite Proxy 进行转发。
2. THE Integration_Layer SHALL 在 `vite.config.ts` 中配置开发代理，将以下路径转发至对应后端服务：

| 前端路径前缀 | 目标后端 | 说明 |
|-------------|---------|------|
| `/v1/` | `http://localhost:8000` | C 端 API（API_Gateway） |
| `/admin/v1/` | `http://localhost:8002` | Admin API（Admin_Service） |

3. THE Integration_Layer SHALL 配置 Vite Proxy 支持 WebSocket 升级（`ws: true`），确保 `WS /v1/chat/ws` 和 `WS /admin/v1/ws/hitl` 在开发环境中正常工作。
4. THE Integration_Layer SHALL 提供 `.env.integration` 环境变量文件，包含联调所需的全部配置项：
   - `VITE_API_BASE_URL`：API 基础地址（开发环境留空，生产环境为 Nginx 地址）
   - `VITE_WS_BASE_URL`：WebSocket 基础地址（开发环境为 `ws://localhost:8002`，生产环境由 Nginx 代理）
5. THE Nginx_Proxy 配置 SHALL 支持 SSE 长连接，设置 `proxy_buffering off` 和 `X-Accel-Buffering: no` 响应头，确保 SSE Token 流不被 Nginx 缓冲。
6. THE Nginx_Proxy 配置 SHALL 设置 WebSocket 连接超时为 300 秒（`proxy_read_timeout 300s`），避免 HITL 长连接被 Nginx 过早断开。
7. IF 后端服务不可用（连接拒绝），THEN THE Integration_Layer SHALL 在前端展示"后端服务不可用，请检查服务状态"的错误提示，而非显示空白页面。

---

### 需求 3：Admin 认证流程对接

**用户故事：** 作为运营人员，我希望使用真实的后端认证服务登录管理后台，以确保认证流程在真实环境中正常工作。

#### 验收标准

1. THE Integration_Layer SHALL 对接后端 `POST /admin/v1/auth/login` 接口，发送 `{email, password}` 请求体，接收 `{access_token, token_type, expires_in}` 响应。
2. WHEN 登录成功时，THE Integration_Layer SHALL 从 JWT access_token 的 payload 中解码用户信息（`admin_user_id`、`tenant_id`、`role`），并映射为前端 `AdminUser` 类型。后端 JWT payload 不包含 `email` 和 `tenant_name` 字段，THE Integration_Layer SHALL 处理这些缺失字段（使用 `admin_user_id` 作为显示名，`tenant_id` 作为租户名）。
3. THE Integration_Layer SHALL 对接后端 `POST /admin/v1/auth/refresh` 接口进行 Token 刷新。后端刷新接口需要有效的 JWT（通过 Authorization Header），THE Integration_Layer SHALL 确保在 Token 过期前（剩余有效期 < 1 小时）触发刷新。
4. WHEN 后端 JWT 鉴权中间件返回 `{"error": "Token expired"}` 或 `{"error": "Invalid token"}` 时，THE Integration_Layer SHALL 触发 Token 刷新流程；WHEN 刷新也失败时，SHALL 重定向至登录页面。
5. THE Integration_Layer SHALL 确保 Admin API 请求的 `Authorization: Bearer {token}` Header 中的 Token 是后端签发的真实 JWT（HS256 算法），而非 MSW 模拟的假 Token。
6. THE Integration_Layer SHALL 提供 Seed_Script，在测试数据库中创建至少一个 Admin 用户（包含 bcrypt 加密的密码），用于联调和 E2E 测试。

---

### 需求 4：SSE 流式聊天对接

**用户故事：** 作为 C 端用户，我希望通过真实的 SSE 接口与 AI 对话，以验证流式消息在真实网络环境下的完整性和稳定性。

#### 验收标准

1. THE Integration_Layer SHALL 对接后端 `POST /v1/chat/completions` SSE 端点。请求体 SHALL 包含 `{thread_id, user_id, messages: [{role, content}]}`，与后端期望的格式一致。
2. THE Integration_Layer SHALL 处理后端 SSE 流的实际格式。后端通过 `sse-starlette` 发送事件，每个 Token 的格式为 `data: {"content": "token_text"}`，流结束标记为 `data: [DONE]`。前端 SSE_Client 当前期望 OpenAI 格式 `data: {"id": "...", "choices": [{"delta": {"content": "..."}}]}`，THE Integration_Layer SHALL 适配两种格式或统一为后端实际格式。
3. WHEN 后端返回 `data: {"error": "CONCURRENT_REQUEST", "message": "AI is still processing"}` 时，THE Integration_Layer SHALL 在前端展示"AI 正在处理上一条消息，请稍候"的提示。
4. THE Integration_Layer SHALL 确保 SSE 请求携带正确的 C 端 API Key（`Authorization: Bearer {api_key}`），通过 API_Gateway 的 `TenantAuthMiddleware` 鉴权。
5. THE Integration_Layer SHALL 处理后端 `GET /v1/threads/{thread_id}` 返回的 LangGraph 消息格式，将其转换为前端 `Message[]` 类型。LangGraph 消息对象的结构与前端 `Message` 类型不同，需要进行字段映射。
6. WHEN SSE 连接因网络问题断开时，THE Integration_Layer SHALL 验证指数退避重连机制在真实网络环境下正常工作（初始 1 秒，最大 30 秒）。

---

### 需求 5：WebSocket 对接

**用户故事：** 作为 C 端用户和运营人员，我希望 WebSocket 连接能够与真实后端服务正常通信，以确保 HITL 人工介入和实时聊天功能正常工作。

#### 验收标准

1. THE Integration_Layer SHALL 对接后端 `WS /v1/chat/ws` C 端 WebSocket 端点。消息格式 SHALL 与后端一致：发送 `{thread_id, tenant_id, messages: [...]}` 请求，接收 `{content: "token"}` Token 消息和 `{done: true}` 完成消息。
2. THE Integration_Layer SHALL 对接后端 `WS /admin/v1/ws/hitl` Admin 端 WebSocket 端点。连接建立后 SHALL 发送初始注册消息 `{tenant_id: "..."}` 以注册到对应租户的连接池。
3. WHEN 后端 HITL WebSocket 推送 `{type: "hitl_request", session_id, thread_id, reason, unresolved_turns}` 事件时，THE Integration_Layer SHALL 将其转换为前端 `HITLSession` 类型并更新 HITL_Panel。
4. THE Integration_Layer SHALL 确保 WebSocket 心跳机制（每 30 秒发送 `{type: "ping"}`）与后端的连接保活策略兼容。后端 HITL WebSocket 通过 `await websocket.receive_text()` 保持连接，前端心跳消息 SHALL 被后端正确接收。
5. IF WebSocket 连接被后端主动关闭（如 `code=4001, reason="tenant_id required"`），THEN THE Integration_Layer SHALL 在前端展示对应的错误信息，而非静默重连。
6. THE Integration_Layer SHALL 处理 C 端 WebSocket 与 Admin 端 WebSocket 的鉴权差异：C 端通过 URL 参数传递 `api_key`（`?api_key=xxx`），Admin 端通过初始消息传递 `tenant_id`。

---

### 需求 6：文件上传对接

**用户故事：** 作为运营人员，我希望知识库文档上传能够与真实后端服务正常工作，以验证文件上传、处理和存储的完整流程。

#### 验收标准

1. THE Integration_Layer SHALL 对接后端 `POST /admin/v1/knowledge/docs` 文件上传接口。请求 SHALL 使用 `multipart/form-data` 格式，文件字段名为 `file`（与后端 `UploadFile = File(...)` 参数名一致）。
2. THE Integration_Layer SHALL 处理后端上传响应的字段差异：后端返回 `{doc_id, status: "pending"}`，前端期望完整的 `KnowledgeDoc` 对象。THE Integration_Layer SHALL 在上传成功后重新调用 `GET /admin/v1/knowledge/docs` 获取完整文档列表。
3. THE Integration_Layer SHALL 对接后端 `GET /admin/v1/knowledge/docs/{doc_id}` 状态查询接口，处理响应字段映射：后端返回 `{doc_id, status, chunk_count, error_msg}`，需映射为前端 `KnowledgeDoc` 类型。
4. THE Integration_Layer SHALL 对接后端 `DELETE /admin/v1/knowledge/docs/{doc_id}` 删除接口，处理响应格式：后端返回 `{doc_id, deleted: true}`，前端期望 HTTP 204 No Content。THE Integration_Layer SHALL 兼容两种响应格式。
5. THE Integration_Layer SHALL 对接后端 `POST /admin/v1/knowledge/docs/{doc_id}/retry` 重试接口，处理响应格式：后端返回 `{doc_id, status: "pending"}`。
6. IF 后端返回 HTTP 413（文件过大，超过 50MB），THEN THE Integration_Layer SHALL 展示"文件过大（最大 50MB）"的错误提示。

---

### 需求 7：Admin API 对接

**用户故事：** 作为运营人员，我希望管理后台的所有功能（指标、配置、沙盒）都能与真实后端服务正常工作。

#### 验收标准

1. THE Integration_Layer SHALL 对接后端 `GET /admin/v1/metrics/overview?range={period}` 指标接口。后端响应 `{total_conversations, human_transfer_count, human_transfer_rate, range}` SHALL 被映射为前端 `MetricsOverview` 类型。后端不返回 `ai_resolution_rate`、`avg_ttft_ms`、`total_tokens_used` 等字段，THE Integration_Layer SHALL 从 `human_transfer_rate` 计算 `aiResolutionRate`（`1 - humanEscalationRate`），其余缺失字段使用默认值 0。
2. THE Integration_Layer SHALL 对接后端 `GET /admin/v1/metrics/tokens?range={period}` Token 指标接口。后端响应 `{total_tokens, message_count, range}` SHALL 被映射为前端期望的格式。
3. THE Integration_Layer SHALL 对接后端 `GET /admin/v1/metrics/missed-queries?range={period}` 未命中查询接口。后端响应 `{missed_queries: [{query_prefix, count}], range}` SHALL 被解包为前端期望的数组格式 `[{query, count}]`。
4. THE Integration_Layer SHALL 对接后端配置接口，处理请求体字段映射：
   - `PUT /admin/v1/config/persona`：前端发送 `{systemPrompt, personaName}`，需转换为后端期望的 `{system_prompt, persona_name}`
   - `PUT /admin/v1/config/model`：前端发送 `{primaryModel, fallbackModel, temperature}`，需转换为后端期望的 `{model, fallback_model, temperature}`（注意 `primaryModel` → `model` 的字段名差异）
   - `PUT /admin/v1/config/rate-limit`：前端发送 `{tenantRps, userRps}`，需转换为后端期望的 `{tenant_rps, user_rps}`
5. THE Integration_Layer SHALL 对接后端 `POST /admin/v1/config/cache/clear` 缓存清除接口（注意路径为 `/admin/v1/config/cache/clear`，非 `/admin/v1/cache/clear`）。前端当前请求路径 SHALL 与后端实际路径保持一致。
6. THE Integration_Layer SHALL 对接后端 `POST /admin/v1/metrics/sandbox/run` 沙盒接口（注意：后端沙盒端点注册在 metrics router 下，路径为 `/admin/v1/metrics/sandbox/run`，非 `/admin/v1/sandbox/run`）。请求体字段 SHALL 从前端 `{testCases: [{query, reference, contexts}]}` 转换为后端期望的 `{test_cases: [{query, reference, contexts, response}]}`。
7. WHEN 后端配置接口返回 `{updated: true}` 时，THE Integration_Layer SHALL 将其视为成功响应并展示 Toast 通知。后端不返回 HTTP 204，而是返回 HTTP 200 + JSON body。

---

### 需求 8：MSW 条件加载

**用户故事：** 作为前端开发者，我希望在联调环境中禁用 MSW，在纯前端开发环境中启用 MSW，以便灵活切换开发模式。

#### 验收标准

1. THE Integration_Layer SHALL 通过环境变量 `VITE_ENABLE_MSW` 控制 MSW 的启用/禁用。WHEN `VITE_ENABLE_MSW=true` 时启用 MSW 拦截；WHEN 未设置或为 `false` 时禁用 MSW，所有请求直接发送至真实后端。
2. THE Integration_Layer SHALL 确保 MSW 禁用后，前端所有 API 调用路径（Axios baseURL、SSE URL、WebSocket URL）正确指向真实后端服务。
3. THE Integration_Layer SHALL 在 MSW 禁用时移除 MSW 的 Service Worker 注册，避免残留的 Service Worker 拦截真实 API 请求。
4. THE Integration_Layer SHALL 提供两套环境配置文件：
   - `.env.development`：`VITE_ENABLE_MSW=true`（纯前端开发模式）
   - `.env.integration`：`VITE_ENABLE_MSW=false`（联调模式）

---

### 需求 9：Docker Compose 全栈部署

**用户故事：** 作为开发者，我希望通过一条命令启动前端 + 后端全部服务，以便快速搭建联调环境。

#### 验收标准

1. THE Docker_Compose_Stack SHALL 在现有 `docker-compose.yml` 中新增 `frontend` 服务，使用 `frontend/Dockerfile` 构建，暴露 80 端口。
2. THE Docker_Compose_Stack SHALL 配置 `frontend` 服务依赖 `api-gateway` 和 `admin-service`，确保后端服务就绪后前端才启动。
3. THE Docker_Compose_Stack SHALL 通过 Nginx 反向代理统一入口，前端静态资源和 API 请求通过同一个 80 端口访问，避免跨域问题。
4. THE Docker_Compose_Stack SHALL 提供 Seed_Script 服务（`seed` 容器），在数据库迁移完成后自动创建测试数据：
   - 一个测试租户（含 API Key）
   - 一个 Admin 用户（邮箱 + bcrypt 密码）
   - 必要的初始配置数据
5. WHEN 运行 `docker compose up` 时，THE Docker_Compose_Stack SHALL 在所有服务启动后，前端可通过 `http://localhost` 访问，API 请求通过 Nginx 代理转发至后端。
6. THE Docker_Compose_Stack SHALL 提供健康检查配置，前端 Nginx 服务 SHALL 包含 `curl -f http://localhost/` 健康检查。

---

### 需求 10：E2E 测试运行环境

**用户故事：** 作为开发者，我希望 E2E 测试能够在真实前后端服务上运行，以验证完整的用户流程在真实环境中正常工作。

#### 验收标准

1. THE E2E_Test 环境 SHALL 提供 Playwright 配置文件（`playwright.integration.config.ts`），指向真实服务地址（`http://localhost` 或 Docker Compose 网络地址）。
2. THE E2E_Test 环境 SHALL 在测试运行前通过 Seed_Script 初始化测试数据，确保测试所需的租户、API Key 和 Admin 用户存在。
3. THE E2E_Test 环境 SHALL 提供以下集成测试场景：
   - Admin 登录：使用 Seed 数据中的 Admin 用户登录，验证 JWT 签发和页面跳转
   - 聊天流程：使用 Seed 数据中的 API Key 发送消息，验证 SSE 流式响应
   - 知识库上传：上传测试文件，验证文件处理状态轮询
   - HITL 流程：触发人工介入，验证 WebSocket 实时通知
4. THE E2E_Test 环境 SHALL 与现有 MSW 模式的 E2E 测试共存，通过不同的 Playwright 配置文件区分：
   - `playwright.config.ts`：MSW 模式（现有，用于纯前端测试）
   - `playwright.integration.config.ts`：联调模式（新增，用于真实服务测试）
5. IF E2E 测试因后端服务不可用而失败，THEN THE E2E_Test 环境 SHALL 在测试报告中明确标注"后端服务不可用"，而非显示模糊的超时错误。
6. THE E2E_Test 环境 SHALL 支持通过 `docker compose --profile e2e up` 启动包含 E2E 测试运行器的完整环境，测试完成后自动退出并返回退出码。

---

## 正确性属性（用于 Property-Based Testing）

### P1：字段映射往返一致性（Round-Trip）

**对应需求：** 需求 1

**属性描述：**
对于任意合法的后端 JSON 响应对象 `R`（键为 snake_case），经过 `toCamelCase` 转换后再经过 `toSnakeCase` 转换，结果的键集合应等于原始对象 `R` 的键集合：

```
∀ R (valid backend JSON response):
  keys(toSnakeCase(toCamelCase(R))) == keys(R)
```

**测试策略：**
- 生成随机 snake_case 键值对象（1~50 个键，键名包含 1~3 个下划线分隔的单词）
- 执行 toCamelCase → toSnakeCase 往返转换
- 断言转换后的键集合与原始键集合完全一致

---

### P2：SSE 格式适配完整性

**对应需求：** 需求 4

**属性描述：**
对于任意后端 SSE Token 序列（格式为 `data: {"content": "token_text"}`），经过 SSE_Client 解析后，最终拼接的完整消息文本应等于所有 Token 的 `content` 字段拼接结果：

```
∀ token_sequence [{content: t1}, {content: t2}, ..., {content: tn}] followed by [DONE]:
  parsed_text == concat(t1, t2, ..., tn)
```

**测试策略：**
- 生成随机 Token 序列（1~200 个 Token，包含中文、英文、特殊字符）
- 构造后端实际 SSE 格式的事件流
- 通过 SSE_Client 解析
- 断言解析结果与原始 Token 拼接一致

---

### P3：API 响应结构映射完整性

**对应需求：** 需求 1、需求 7

**属性描述：**
对于任意后端 API 端点返回的响应对象，经过 Field_Mapper 转换后，结果对象的所有必需字段（根据前端 TypeScript 类型定义）均存在且类型正确：

```
∀ endpoint ∈ {overview, tokens, missed-queries, knowledge, hitl, config}:
  ∀ response from endpoint:
    mapped = fieldMapper(response)
    mapped satisfies FrontendType[endpoint]
```

**测试策略：**
- 为每个后端端点生成符合后端 schema 的随机响应对象
- 通过 Field_Mapper 转换
- 断言转换结果满足前端 TypeScript 类型的所有必需字段


---

## 补充说明（来自专家评审）

> **Field_Mapper 工具选型**（需求 1 补充）：评估引入 `camelcase-keys` / `snakecase-keys` 等成熟库替代手写转换函数，减少转换代码量。对于 `primaryModel` → `model` 等非标准映射，在 Field_Mapper 中建立显式规则，不依赖通用命名风格转换。

> **SSE 格式适配层**（需求 4 补充）：在 SSE_Client 中增加格式检测逻辑，优先检测 `content` 字段（后端实际格式），若无则回退到 OpenAI `choices[0].delta.content` 格式解析。确保两种格式均可正确解析。

> **WebSocket 连接参数**（需求 5 补充）：在 `wsClient.ts` 中增加 `queryParams` 连接选项，支持动态拼接 URL 参数（如 `?api_key=xxx`）。Admin WS 连接建立后需发送初始注册消息 `{tenant_id: "..."}`。

> **Docker Compose 健康检查**（需求 9 补充）：`depends_on` 仅控制启动顺序，不保证服务就绪。建议增加 `healthcheck` 配置和 `condition: service_healthy` 依赖条件。Seed Script 应支持幂等性（`IF NOT EXISTS`），避免重复运行报错。

> **Nginx SSE 关键配置**（需求 2 补充）：`proxy_buffering off` 和 `X-Accel-Buffering: no` 是 SSE 流式接口在生产环境稳定运行的关键配置。Nginx 默认缓冲会累积 Token 直到流结束才一次性返回，导致前端完全收不到逐字效果。

> **MSW Service Worker 清理**（需求 8 补充）：禁用 MSW 时需主动调用 `navigator.serviceWorker.getRegistrations()` 并 `unregister()` 残留的 Service Worker，避免之前的注册持续拦截真实 API 请求。

> **E2E 测试数据清理**（需求 10 补充）：E2E 测试完成后应清理测试数据，避免污染联调环境。建议在 `afterAll` 中调用清理 API 或使用事务回滚。

> **错误码枚举文档**（全局补充）：建议补充后端错误码与前端提示的完整映射表，覆盖后端自定义错误码（如 `CONCURRENT_REQUEST`、`TENANT_NOT_FOUND`、`RATE_LIMITED` 等）。
