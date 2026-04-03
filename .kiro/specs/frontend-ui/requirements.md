# 需求文档：Cuckoo-Echo 前端 UI

## 简介

Cuckoo-Echo（布谷回响）后端已完成全部 10 个阶段的开发（303 测试，54 次提交），提供完整的 C 端对话 API 和 Admin 管理 API。当前系统缺少前端界面，这是投产交付的最大缺口。本需求文档定义前端 UI 的功能范围，涵盖 C 端用户聊天界面和 Admin 管理后台两大模块。

前端需对接后端已有的 REST API、SSE 流式接口和 WebSocket 双向通信接口，实现完整的用户交互体验。

---

## 前端技术栈

| 类别 | 推荐方案 | 选型理由 |
|------|----------|----------|
| 框架 | React 18 + TypeScript | 生态完善、类型安全、SSE/WS 处理成熟 |
| 状态管理 | Zustand | 轻量无 Provider 嵌套，适合跨组件状态共享（Auth/Chat/HITL） |
| UI 组件库 | Radix UI + Tailwind CSS | Radix 无障碍支持最佳（WCAG 2.1 AA），Tailwind 原子化高定制 |
| 构建工具 | Vite | 快速 HMR，ESM 原生支持 |
| HTTP 客户端 | Axios（Interceptor 统一鉴权/错误处理） | |
| Markdown 渲染 | react-markdown + remark-gfm + DOMPurify | 流式 Markdown 安全渲染，防 XSS |
| 图表 | Recharts 或 ECharts | 数据看板可视化 |
| 测试 | Vitest + Testing Library + Playwright | 单元 + E2E + PBT |
| 代码规范 | ESLint + Prettier + Husky | 团队协作一致性 |
| 包管理 | pnpm | 快速、磁盘高效 |

---

## 词汇表

- **Frontend**：Cuckoo-Echo 前端 Web 应用整体
- **Chat_Widget**：C 端用户聊天组件，可嵌入企业网站（Web Component）或独立页面
- **Admin_Dashboard**：管理后台 Web 应用，供 Admin_User 使用
- **Message_Bubble**：聊天界面中的单条消息气泡组件
- **Typing_Indicator**：打字机效果指示器，逐字展示 AI 回复（使用 requestAnimationFrame 防抖渲染）
- **Thread_List**：会话列表组件，展示历史对话
- **Media_Uploader**：媒体文件上传组件（图片/语音），含客户端预压缩
- **SSE_Client**：Server-Sent Events 客户端，接收流式 Token，含断线重连和消息补偿
- **WS_Client**：WebSocket 客户端，双向实时通信，含心跳和指数退避重连
- **HITL_Panel**：人工介入操作面板
- **Knowledge_Manager**：知识库管理界面
- **Metrics_Dashboard**：数据看板界面
- **Config_Panel**：租户配置面板（Persona、模型、限流）
- **Sandbox_Runner**：沙盒试运行界面
- **Auth_Module**：Admin 登录认证模块（access_token 内存存储 + refresh_token httpOnly cookie）
- **Toast**：轻量级通知提示组件
- **SessionContext**：全局会话状态上下文（单一数据源：active / hitl_pending / hitl_active / resolved）
- **Admin_User**：管理后台用户（运营人员）
- **End_User**：C 端最终用户
- **JWT**：JSON Web Token，Admin 认证令牌
- **API_Key**：C 端 API 密钥，用于 Chat_Widget 鉴权
- **Optimistic_UI**：乐观更新，用户消息发送后立即展示（使用 temp_id），后端确认后替换为真实 ID
- **Virtual_Scroll**：虚拟滚动，仅渲染可视区域内的消息 DOM 节点，支持长对话历史

---

## 需求列表


### 需求 1：C 端聊天界面 — 流式消息与打字机效果

**用户故事：** 作为 C 端用户，我希望在聊天界面中看到 AI 回复以打字机效果逐字展示，以减少等待焦虑并获得流畅的对话体验。

#### 验收标准

1. WHEN End_User 发送文本消息时，THE Chat_Widget SHALL 立即以 Optimistic_UI 方式展示用户消息（使用本地 `temp_id`），同时通过 SSE 连接（`POST /v1/chat/completions`，`stream=true`）向后端发送请求。WHEN 后端 SSE 流返回第一帧（带有真实 Message ID）时，THE Chat_Widget SHALL 在状态管理器中将 `temp_id` 替换为真实 ID。
2. WHEN SSE_Client 接收到 Token 事件时，THE Typing_Indicator SHALL 使用 `requestAnimationFrame` 累积 16ms 内的 Token 后一次性追加渲染到当前 Message_Bubble 中，避免每个 Token 触发一次 React re-render 导致性能卡顿。LLM 返回的 Markdown 内容 SHALL 通过 `react-markdown` + `remark-gfm` 实时解析渲染，并使用 `DOMPurify` 清洗 HTML 标签，防止 XSS 攻击（包括不闭合的 Markdown 标签导致的 DOM 结构崩溃）。
3. WHEN SSE_Client 接收到 `[DONE]` 事件时，THE Chat_Widget SHALL 标记当前消息为完成状态，停止 Typing_Indicator 动画。WHEN SSE 连接意外关闭且未收到 `[DONE]` 事件时，THE Chat_Widget SHALL 展示"消息发送中断，请重试"提示。
4. WHILE AI 正在生成回复时，THE Chat_Widget SHALL 在输入区域展示"AI 正在思考…"状态提示，并禁用发送按钮以防止重复提交。输入框 SHALL 支持 `Shift + Enter` 换行、`Enter` 发送。
5. THE Chat_Widget SHALL 默认使用 SSE 协议进行对话；WHEN 会话状态为 `human_intervention`（需接收客服消息）时，THE Chat_Widget SHALL 自动切换至 WebSocket 协议。
6. WHEN SSE 或 WebSocket 连接断开时，THE Client SHALL 自动尝试重连（指数退避策略，初始 1 秒，最大间隔 30 秒），并在重连期间向用户展示"连接中…"提示。SSE 重连成功后，THE Chat_Widget SHALL 静默调用 `GET /v1/threads/{thread_id}` 拉取最新全量历史，与本地 Message 列表进行对比合并（Reconciliation），确保断线期间的消息不丢失。
7. IF SSE 或 WebSocket 连接发生错误，THEN THE Chat_Widget SHALL 向用户展示友好的错误提示（如"网络异常，请稍后重试"），并提供手动重试按钮。
8. THE Chat_Widget SHALL 在每条 AI 回复的 Message_Bubble 中展示该消息的完成时间戳。
9. THE Chat_Widget SHALL 使用 Virtual_Scroll（虚拟滚动）渲染消息列表，仅渲染可视区域内的 DOM 节点，确保 1000+ 条消息的对话历史不会导致性能问题。

---

### 需求 2：C 端聊天界面 — 多模态输入

**用户故事：** 作为 C 端用户，我希望能够在聊天中上传图片和语音，以便在无法打字时也能获得客服帮助。

#### 验收标准

1. THE Media_Uploader SHALL 提供图片上传入口（支持 jpg/png/webp 格式），允许 End_User 通过点击按钮或拖拽方式上传图片。上传前 SHALL 使用 Canvas API 对超过 2MB 的图片进行本地预压缩（转为 WebP 格式，质量 0.8），降低 OSS 存储成本并提升上传速度。
2. THE Media_Uploader SHALL 提供语音录制入口，包含：开始录制按钮（长按或点击触发）、录制时长计时器（最大 60 秒）、暂停/继续按钮、完成/取消按钮。录制完成后支持预览播放和重录。支持 wav/mp3/m4a 格式。
3. WHEN End_User 上传图片或语音时，THE Chat_Widget SHALL 在消息区域展示上传进度条，并在上传完成后展示缩略图（图片）或音频播放器（语音）。
4. WHEN 后端返回 `{"type": "processing", "stage": "asr"}` 状态事件时，THE Chat_Widget SHALL 展示"语音识别中…"过渡提示。
5. IF 上传的文件格式不受支持（后端返回 HTTP 415），THEN THE Chat_Widget SHALL 向用户展示"不支持该文件格式"的错误提示。
6. THE Media_Uploader SHALL 限制单个文件大小：图片 ≤ 10MB（压缩前），语音 ≤ 5MB。超过时在客户端拦截并提示"文件过大，最大支持 X MB"，不发送请求至后端。
7. THE Chat_Widget SHALL 在历史消息中正确渲染图片（可点击放大查看、支持懒加载）和语音（内嵌播放器），保持多模态消息的完整展示。
8. FOR 移动端场景，THE Chat_Widget SHALL 自动处理软键盘弹起遮挡输入框的视口（Viewport）问题，确保输入框始终可见。

---

### 需求 3：C 端聊天界面 — 会话管理

**用户故事：** 作为 C 端用户，我希望能够查看历史对话并发起新会话，以便在不同问题之间切换。

#### 验收标准

1. THE Chat_Widget SHALL 提供"新建会话"按钮，点击后生成新的 `thread_id`（客户端 uuidv4）并清空当前聊天区域。
2. THE Thread_List SHALL 通过 `GET /v1/threads/{thread_id}` 接口加载指定会话的历史消息，并按时间顺序展示。
3. WHEN End_User 切换到历史会话时，THE Chat_Widget SHALL 加载该会话的完整消息记录，并恢复到可继续对话的状态。
4. THE Chat_Widget SHALL 在消息列表中支持滚动加载（向上滚动加载更早的消息），避免一次性加载全部历史消息导致性能问题。
5. WHEN 新消息到达时，THE Chat_Widget SHALL 自动滚动到消息列表底部，除非用户正在浏览历史消息（此时展示"有新消息"浮动提示按钮，点击后滚动到底部）。
6. THE Chat_Widget SHALL 使用 IndexedDB 缓存最近 50 条消息和 20 个会话元数据，缓存有效期 7 天；当本地存储超过 10MB 时，按 LRU 策略淘汰最旧的会话。

---

### 需求 4：Admin 登录认证

**用户故事：** 作为运营人员，我希望通过安全的登录流程进入管理后台，以确保只有授权人员能访问管理功能。

#### 验收标准

1. THE Auth_Module SHALL 提供登录页面，包含邮箱和密码输入框，通过 `POST /admin/v1/auth/login` 接口进行认证。
2. WHEN 登录成功时，THE Auth_Module SHALL 将 JWT `access_token` 存储于内存（Zustand store）中，`refresh_token` 由后端通过 `Set-Cookie: HttpOnly; Secure; SameSite=Strict` 下发存储于 httpOnly cookie 中。前端代码不直接操作 refresh_token。跳转至 Admin_Dashboard 首页。
3. IF 登录失败（后端返回 HTTP 401），THEN THE Auth_Module SHALL 在登录页面展示"邮箱或密码错误"的提示。
4. WHEN JWT 即将过期（剩余有效期 < 1 小时）且存在用户活动时，THE Auth_Module SHALL 自动调用 `POST /admin/v1/auth/refresh` 接口刷新令牌，无需用户重新登录。WHEN 多个请求同时触发刷新时，THE Auth_Module SHALL 实现 Token Refresh Mutex：第一个请求触发刷新，后续请求等待第一个请求的结果，避免并发刷新冲突。
5. IF JWT 刷新失败（refresh_token 也过期），THEN THE Auth_Module SHALL 将用户重定向至登录页面，并展示"登录已过期，请重新登录"的提示。
6. THE Auth_Module SHALL 通过 Axios Request Interceptor 在所有 Admin API 请求的 `Authorization` Header 中自动附加 `Bearer {access_token}`。绝不允许在 console.log 中打印 Token，绝不允许在 URL 中传递 Token。
7. THE Admin_Dashboard SHALL 提供退出登录功能，清除内存中的 access_token 并调用后端清除 refresh_token cookie，跳转至登录页面。

---

### 需求 5：Admin 知识库管理

**用户故事：** 作为运营人员，我希望能够在管理后台上传、查看和删除知识文档，以确保 AI 回答基于最新的业务信息。

#### 验收标准

1. THE Knowledge_Manager SHALL 提供文档上传界面，支持拖拽上传和文件选择器，通过 `POST /admin/v1/knowledge/docs` 接口上传文件。
2. THE Knowledge_Manager SHALL 展示文档列表，包含文件名、上传时间、处理状态（pending / processing / completed / failed）和分块数量。WHEN 文档列表为空时，SHALL 展示设计良好的空状态（Empty State）并提供"立即上传"的快捷引导按钮。
3. WHEN 文档处理状态为 `pending` 或 `processing` 时，THE Knowledge_Manager SHALL 以指数退避策略轮询 `GET /admin/v1/knowledge/docs/{id}` 接口更新状态（初始 3 秒，最大 15 秒），仅对 processing 状态文档轮询，completed/failed 停止轮询。
4. WHEN 文档处理状态为 `failed` 时，THE Knowledge_Manager SHALL 展示错误信息，并提供"重试"按钮（调用 `POST /admin/v1/knowledge/docs/{id}/retry`）。
5. THE Knowledge_Manager SHALL 提供文档删除功能，点击删除后弹出确认对话框，确认后调用 `DELETE /admin/v1/knowledge/docs/{id}` 接口。
6. IF 上传的文件超过 50MB，THEN THE Knowledge_Manager SHALL 在客户端拦截并提示"文件过大（最大 50MB）"，不发送请求至后端。
7. THE Knowledge_Manager SHALL 支持按文件名搜索和按状态筛选文档列表。

---

### 需求 6：Admin 人工介入（HITL）面板

**用户故事：** 作为运营人员，我希望在管理后台实时接收人工介入请求并接管对话，以保障用户体验。

#### 验收标准

1. THE HITL_Panel SHALL 通过 WebSocket（`WS /admin/v1/ws/hitl`）建立长连接，实时接收 `hitl_request` 事件。WebSocket SHALL 实现心跳机制（每 30 秒发送 ping），检测连接存活。
2. WHEN HITL_Panel 接收到 `hitl_request` 事件时，THE HITL_Panel SHALL 以视觉高亮（红色角标 + 消息提示）展示待处理的介入请求，包含会话 ID、触发原因和未解决轮次。声音提示 SHALL 仅在用户首次点击页面后启用（遵守浏览器自动播放策略），并提供静音开关。
3. WHEN Admin_User 点击"接管"按钮时，THE HITL_Panel SHALL 调用 `POST /admin/v1/hitl/{session_id}/take` 接口，并在成功后加载完整的对话历史。
4. WHILE Admin_User 正在处理人工介入会话时，THE HITL_Panel SHALL 提供消息输入框，允许 Admin_User 直接向 End_User 发送消息。
5. WHEN Admin_User 点击"结束介入"按钮时，THE HITL_Panel SHALL 调用 `POST /admin/v1/hitl/{session_id}/end` 接口，将会话恢复为 AI 自动处理状态。
6. THE HITL_Panel SHALL 通过 WebSocket 实时更新会话列表状态（无需轮询），展示当前所有待处理和进行中的介入会话，包含状态（pending / active / resolved / auto_escalated）和处理人信息。
7. IF WebSocket 连接断开，THEN THE HITL_Panel SHALL 自动重连（指数退避，最大 30 秒）并在界面展示"连接中…"状态提示。

---

### 需求 7：Admin 租户配置

**用户故事：** 作为运营人员，我希望能够在管理后台配置机器人人设、模型选择和限流策略，以定制 AI 客服的行为。

#### 验收标准

1. THE Config_Panel SHALL 提供 Persona 配置表单，包含系统提示词（多行文本框）和机器人名称输入框，通过 `PUT /admin/v1/config/persona` 接口保存。
2. THE Config_Panel SHALL 提供模型选择表单，包含主模型下拉选择器、备用模型下拉选择器和温度参数滑块（0.0 ~ 1.0），通过 `PUT /admin/v1/config/model` 接口保存。
3. THE Config_Panel SHALL 提供限流配置表单，包含租户级 RPS 和用户级 RPS 输入框，通过 `PUT /admin/v1/config/rate-limit` 接口保存。
4. WHEN Admin_User 提交配置变更时，THE Config_Panel SHALL 展示保存成功的 Toast 通知。配置修改立即生效，无需重启服务。
5. IF 配置保存失败（后端返回错误），THEN THE Config_Panel SHALL 展示错误信息并保留用户已填写的表单内容，不清空表单。
6. THE Config_Panel SHALL 提供"清除语义缓存"按钮，调用 `POST /admin/v1/cache/clear` 接口（后端已实现），并在成功后展示确认提示。
7. THE Config_Panel SHALL 在页面加载时从后端获取当前配置并回填到表单中，确保 Admin_User 看到的是最新的配置状态。

---

### 需求 8：Admin 数据看板

**用户故事：** 作为运营人员，我希望在管理后台查看关键业务指标，以评估 AI 客服效果并优化配置。

#### 验收标准

1. THE Metrics_Dashboard SHALL 展示概览指标卡片，包含：总对话数、转人工次数、转人工率，数据来源为 `GET /admin/v1/metrics/overview` 接口。
2. THE Metrics_Dashboard SHALL 展示 Token 消耗统计，包含：总 Token 数和消息数量，数据来源为 `GET /admin/v1/metrics/tokens` 接口。
3. THE Metrics_Dashboard SHALL 提供时间范围选择器（最近 1 天 / 7 天 / 30 天），切换后重新加载对应时间段的数据。
4. THE Metrics_Dashboard SHALL 展示"高频未命中问题"列表，数据来源为 `GET /admin/v1/metrics/missed-queries` 接口，帮助运营人员识别知识库缺口。
5. THE Metrics_Dashboard SHALL 使用折线图展示 Token 消耗趋势（按天），使用柱状图展示对话数分布；提供手动刷新按钮，不自动轮询以避免后端压力。
6. WHEN 数据加载中时，THE Metrics_Dashboard SHALL 展示骨架屏（Skeleton）占位，避免页面闪烁。骨架屏 SHALL 同样应用于知识库列表（需求 5）和 HITL 面板（需求 6）的加载状态。

---

### 需求 9：Admin 沙盒试运行

**用户故事：** 作为运营人员，我希望在正式上线前测试当前机器人配置的回答质量，以避免低质量回复影响用户体验。

#### 验收标准

1. THE Sandbox_Runner SHALL 提供测试用例输入界面，允许 Admin_User 输入多组测试问题（query）、期望答案（reference）和检索上下文（contexts）。
2. WHEN Admin_User 点击"运行测试"按钮时，THE Sandbox_Runner SHALL 将测试用例通过 `POST /admin/v1/sandbox/run` 接口提交至后端执行 Ragas 质量评估。
3. WHEN 后端返回评估结果时，THE Sandbox_Runner SHALL 展示各项指标得分（Faithfulness、Context Precision、Context Recall、Answer Relevancy）及其对应的阈值。
4. THE Sandbox_Runner SHALL 以颜色编码区分通过（绿色）和未通过（红色）的指标，直观展示质量门禁结果。
5. IF 评估结果状态为 `failed`，THEN THE Sandbox_Runner SHALL 高亮展示未通过的指标及其得分，帮助 Admin_User 定位问题。
6. THE Sandbox_Runner SHALL 支持将测试用例集保存到 localStorage（最多 10 个用例集），支持按名称加载历史用例集。

---

### 需求 10：前端路由与布局

**用户故事：** 作为运营人员，我希望管理后台有清晰的导航结构，以便快速找到所需功能。

#### 验收标准

1. THE Admin_Dashboard SHALL 采用侧边栏导航布局，包含以下一级菜单项：数据看板、知识库管理、人工介入、配置中心、沙盒测试。
2. THE Frontend SHALL 实现客户端路由（React Router），Admin_Dashboard 各页面切换时不触发整页刷新。路由表：

| 路径 | 页面组件 | 权限 |
|------|----------|------|
| `/login` | LoginPage | 公开 |
| `/admin` | DashboardLayout（重定向到 /admin/metrics） | 需登录 |
| `/admin/metrics` | MetricsDashboard | 需登录 |
| `/admin/knowledge` | KnowledgeManager | 需登录 |
| `/admin/hitl` | HITLPanel | 需登录 |
| `/admin/config` | ConfigPanel | 需登录 |
| `/admin/sandbox` | SandboxRunner | 需登录 |
| `/chat` | ChatWidget（独立页面模式） | API Key |
| `/embed.js` | ChatWidget（嵌入脚本） | API Key |

3. WHEN Admin_User 未登录时，THE Frontend SHALL 将所有 `/admin/*` 路由重定向至 `/login` 页面。
4. THE Admin_Dashboard SHALL 在侧边栏顶部展示当前登录用户的信息（邮箱或用户名）和租户名称。
5. THE Chat_Widget SHALL 作为独立的可嵌入 Web Component，支持通过 `<script src="/embed.js">` 标签集成到企业网站中，实现样式隔离（Shadow DOM）。
6. THE Frontend SHALL 支持响应式布局，Admin_Dashboard 在桌面端（≥1024px）和平板端（≥768px）均可正常使用。
7. THE Frontend SHALL 遵循 WCAG 2.1 AA 级无障碍标准，包括键盘导航支持、屏幕阅读器兼容（aria-label）和足够的颜色对比度（≥4.5:1）。

---

### 需求 11：错误处理与网络状态

**用户故事：** 作为用户（C 端或 Admin），我希望在网络异常或服务不可用时获得清晰的反馈，而不是面对空白页面或无响应的界面。

#### 验收标准

1. WHEN 后端返回 HTTP 429（限流）时，THE Frontend SHALL 展示"请求过于频繁，请稍后重试"的提示，并根据 `Retry-After` 响应头自动延迟重试。
2. WHEN 后端返回 HTTP 503（服务不可用）时，THE Frontend SHALL 展示"系统繁忙，请稍后重试"的提示。
3. WHEN 后端返回 HTTP 409（并发冲突，AI 仍在处理）时，THE Chat_Widget SHALL 展示"AI 正在处理上一条消息，请稍候"的提示。
4. IF 网络完全断开，THEN THE Frontend SHALL 展示全局的离线状态横幅，并在网络恢复后自动隐藏。
5. THE Frontend SHALL 对所有 API 请求实施统一的超时处理（默认 30 秒），超时后展示"请求超时，请重试"的提示。
6. THE Frontend SHALL 通过 Axios Response Interceptor 对 API 错误响应进行统一拦截和格式化，避免将原始错误信息（如堆栈跟踪）暴露给用户。错误状态码映射表：

| HTTP 状态码 | 用户提示 |
|-------------|---------|
| 401 | "登录已过期，请重新登录" |
| 409 | "AI 正在处理上一条消息，请稍候" |
| 415 | "不支持该文件格式" |
| 429 | "请求过于频繁，请稍后重试" |
| 500 | "服务器内部错误，请稍后重试" |
| 503 | "系统繁忙，请稍后重试" |

---

### 需求 12：C 端聊天界面 — 人工介入交互

**用户故事：** 作为 C 端用户，我希望在 AI 无法解决问题时能够顺畅地转接人工客服，并在等待过程中获得明确的状态反馈。

#### 验收标准

1. WHEN 会话状态变为 `human_intervention` 时，THE Chat_Widget SHALL 展示"已转接人工客服，请稍候"的状态提示，并隐藏 AI 思考指示器。THE SessionContext SHALL 更新为 `hitl_active` 状态，作为全局单一数据源驱动所有组件的状态切换。
2. WHILE 会话处于 `human_intervention` 状态时，THE Chat_Widget SHALL 继续接收并展示来自 Admin_User 的消息，消息气泡标记为"人工客服"（不同颜色/图标区分）。
3. WHEN 会话状态从 `human_intervention` 恢复为 `active` 时，THE Chat_Widget SHALL 展示"已恢复 AI 客服"的状态提示，SessionContext 更新为 `active`。
4. IF 人工介入请求超时（60 秒无人响应）且系统自动创建工单，THEN THE Chat_Widget SHALL 向 End_User 展示"当前无客服在线，已为您创建工单，将在工作时间内回复"的提示。

---

## 正确性属性（用于 Property-Based Testing）

以下属性描述了前端在任意合法输入下必须满足的不变量，可用于 Property-Based Testing（Playwright + fast-check）。

### P1：SSE Token 流渲染完整性（Round-Trip）

**对应需求：** 需求 1

**属性描述：**
对于任意合法的 SSE Token 序列，Chat_Widget 最终渲染的完整消息文本等于所有 Token 的拼接结果：

```
∀ token_sequence [t1, t2, ..., tn] followed by [DONE]:
  rendered_text(Message_Bubble) == concat(t1, t2, ..., tn)
```

**测试策略：**
- 生成随机长度（1~500 个 Token）的 Token 序列，包含中文、英文、特殊字符、空格、Markdown 标记
- 模拟 SSE 事件流逐个推送 Token
- 断言最终 Message_Bubble 的文本内容等于所有 Token 的拼接（Markdown 渲染后的纯文本）

---

### P2：消息顺序不变量

**对应需求：** 需求 1、需求 3

**属性描述：**
对于任意会话中的消息序列，Chat_Widget 展示的消息顺序与后端返回的时间戳顺序一致：

```
∀ messages [m1, m2, ..., mn] in a thread:
  display_order(Chat_Widget) == sort_by_timestamp(messages)
```

**测试策略：**
- 生成随机数量（1~100 条）的消息，带有随机时间戳
- 加载到 Chat_Widget 中
- 断言 DOM 中消息的渲染顺序与时间戳升序排列一致

---

### P3：JWT 令牌生命周期不变量

**对应需求：** 需求 4

**属性描述：**
对于任意时刻，Auth_Module 发出的 API 请求要么携带有效的 JWT，要么用户已被重定向至登录页面：

```
∀ api_request from Admin_Dashboard:
  (request.headers["Authorization"] contains valid JWT)
  ∨ (user is on login page)
```

**测试策略：**
- 模拟 JWT 过期、刷新成功、刷新失败、refresh_token 同时过期等场景
- 断言在 JWT 有效期内所有请求携带有效令牌
- 断言在 JWT 过期且刷新失败后用户被重定向至登录页
- 断言并发请求触发 Token Refresh Mutex，不会并发刷新

---

### P4：文件上传客户端校验幂等性

**对应需求：** 需求 2、需求 5

**属性描述：**
对于任意文件，客户端校验（格式、大小）的结果是确定性的，多次校验同一文件产生相同结果：

```
∀ file:
  validate(file) == validate(file)  （多次调用结果相同）
```

**测试策略：**
- 生成随机大小和格式的文件对象
- 对同一文件执行两次客户端校验
- 断言两次校验结果完全一致（通过/拒绝及错误信息）

---

### P5：错误状态码映射完整性

**对应需求：** 需求 11

**属性描述：**
对于后端返回的任意 HTTP 错误状态码，Frontend 展示的用户提示信息与状态码的映射关系保持一致：

```
∀ status_code ∈ {401, 409, 415, 429, 500, 503}:
  error_message(status_code) == predefined_message_map[status_code]
  且 error_message 不包含原始技术细节（如堆栈跟踪）
```

**测试策略：**
- 遍历所有已知错误状态码
- 模拟后端返回对应状态码
- 断言 Frontend 展示的提示信息与预定义映射一致
- 断言提示信息中不包含技术术语或堆栈信息

---

### P6：流式 Markdown 渲染 XSS 防御不变量

**对应需求：** 需求 1

**属性描述：**
对于任意包含恶意 HTML/JavaScript 标签的流式输入序列，渲染后的 DOM 结构不应执行任何 JavaScript 脚本：

```
∀ token_sequence containing <script>, onclick=, javascript:, onerror=, etc.:
  rendered_DOM(Message_Bubble) does NOT contain executable script elements
  且 rendered_DOM 不包含 on* 事件处理器属性
```

**测试策略：**
- 生成包含 `<script>alert(1)</script>`、`<img onerror="alert(1)">`、`[link](javascript:alert(1))` 等恶意 payload 的 Token 序列
- 模拟 SSE 推送
- 断言渲染后的 DOM 中不存在 `<script>` 标签、`on*` 属性或 `javascript:` 协议链接
