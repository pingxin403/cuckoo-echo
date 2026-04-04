# 实施计划：Cuckoo-Echo 前端 UI

## 概述

基于 React 18 + TypeScript + Zustand + Radix UI + Tailwind CSS + Vite + pnpm 技术栈，按模块递增交付前端两大模块（Chat_Widget + Admin_Dashboard）。任务按 8 个阶段组织，每个阶段结束设置检查点，确保增量验证。

## 任务列表

- [x] 1. 项目脚手架与基础设施
  - [x] 1.1 初始化前端项目结构
    - 使用 `pnpm create vite frontend --template react-ts` 创建项目
    - 安装核心依赖：`zustand`, `@radix-ui/react-*`, `tailwindcss`, `axios`, `react-router-dom`, `react-markdown`, `remark-gfm`, `dompurify`, `react-virtuoso`, `recharts`, `idb-keyval`, `uuid`
    - 安装开发依赖：`vitest`, `@testing-library/react`, `fast-check`, `msw`, `fake-indexeddb`, `@types/dompurify`, `playwright`, `@playwright/test`, `jsdom`, `@testing-library/jest-dom`
    - 配置 `tailwind.config.ts`、`tsconfig.json`、`vite.config.ts`（含双入口 main + embed）
    - 创建目录结构：`src/components/`, `src/pages/chat/`, `src/pages/admin/`, `src/stores/`, `src/network/`, `src/hooks/`, `src/lib/`, `src/types/`, `src/styles/`
    - 创建 `src/styles/globals.css`（Tailwind 入口 + CSS 变量 `--ce-primary-color`, `--ce-bg-color`）
    - _需求: 10.2, 10.5, 10.7_

  - [x] 1.2 定义 TypeScript 类型系统
    - 创建 `src/types/index.ts`，定义所有核心接口：`Message`, `MediaAttachment`, `ToolCall`, `ThreadMeta`, `AdminUser`, `KnowledgeDoc`, `HITLSession`, `PersonaConfig`, `ModelConfig`, `RateLimitConfig`, `MetricsOverview`, `TestCase`, `SandboxResult`, `ChatWidgetProps`, `CacheConfig`, `CachedThread`, `SSEClientOptions`, `WSClientOptions`, `WSMessage`, `SSEError`
    - 定义联合类型：`SessionStatus`, `ConnectionStatus`, `DocStatus`, `MessageRole`
    - _需求: 1.1, 2.1, 3.1, 4.2, 5.2, 6.1, 7.1, 8.1, 9.1_

  - [x] 1.3 实现共享 UI 组件
    - 创建 `src/components/Toast.tsx`：基于 Radix UI Toast 的通知组件，支持 success/error/info 类型
    - 创建 `src/components/Skeleton.tsx`：骨架屏组件（卡片/列表/文本三种变体）
    - 创建 `src/components/OfflineBanner.tsx`：监听 `navigator.onLine` + `online/offline` 事件的全局离线横幅，网络恢复后自动隐藏
    - 创建 `src/components/ErrorBoundary.tsx`：React Error Boundary，降级 UI + 刷新按钮
    - 创建 `src/components/ConfirmDialog.tsx`：基于 Radix UI AlertDialog 的确认对话框
    - 所有组件须包含 `aria-label`、键盘导航支持，满足 WCAG 2.1 AA
    - _需求: 8.6, 11.4, 11.6, 10.7_

- [x] 2. 检查点 — 项目基础设施验证
  - 确保 `pnpm build` 成功，`pnpm test` 框架可运行，所有类型定义无编译错误。如有问题请向用户确认。

- [x] 3. 网络层与工具函数
  - [x] 3.1 实现 Axios 实例与拦截器
    - 创建 `src/network/axios.ts`：配置 baseURL（`import.meta.env.VITE_API_BASE_URL`）、timeout 30s、withCredentials
    - 实现 Request Interceptor：从 AuthStore 读取 accessToken 注入 `Authorization: Bearer {token}` Header
    - 实现 Response Interceptor：401 触发 Token Refresh Mutex → 重试/跳转登录；429 读取 Retry-After 自动延迟重试；其他错误码通过 `ERROR_MAP` 映射为用户友好提示（Toast）
    - 禁止在 console.log 中打印 Token，禁止在 URL 中传递 Token
    - _需求: 4.6, 11.1, 11.2, 11.3, 11.5, 11.6_

  - [x] 3.2 实现 Token Refresh Mutex
    - 创建 `src/lib/tokenRefresh.ts`：单例 Promise 模式，并发刷新请求只发出一次实际 `POST /admin/v1/auth/refresh` 请求
    - 刷新成功更新 AuthStore.setAccessToken，刷新失败调用 logout 并跳转 `/login`
    - _需求: 4.4, 4.5_

  - [x] 3.3 实现 SSE 客户端
    - 创建 `src/network/sseClient.ts`：基于 fetch + ReadableStream 的 SSE 客户端
    - 实现 POST 方式 SSE 连接（`POST /v1/chat/completions`，`stream=true`）
    - 实现 SSE `data:` 行解析、`[DONE]` 检测、AbortController 断开
    - 实现 60 秒超时保护：60s 内未收到任何 Token 或 `[DONE]` 则主动断开并触发 onError
    - 实现指数退避重连（初始 1s，最大 30s）
    - _需求: 1.1, 1.3, 1.6, 设计补充-SSE超时保护_

  - [x] 3.4 实现 WebSocket 客户端
    - 创建 `src/network/wsClient.ts`：WebSocket 封装类
    - 实现连接/断开/重连（指数退避，初始 1s，最大 30s）
    - 实现心跳机制（每 30s 发送 `{ type: 'ping' }`）
    - 实现消息分发（onMessage 回调，JSON 解析）
    - 重连成功后重置退避延迟
    - _需求: 1.5, 6.1, 6.7_

  - [x] 3.5 实现工具函数库
    - 创建 `src/lib/sanitize.ts`：DOMPurify 封装，配置允许的标签/属性白名单，过滤 `<script>`、`on*` 事件、`javascript:` 协议
    - 创建 `src/lib/errorMap.ts`：HTTP 状态码 → 用户提示映射表（401/409/415/429/500/503）
    - 创建 `src/lib/fileValidation.ts`：文件格式/大小校验函数 `validateFile(file, category)`，支持 image/audio/document 三类
    - 创建 `src/lib/imageCompress.ts`：Canvas API 图片预压缩（>2MB 转 WebP，质量 0.8）
    - 创建 `src/lib/analytics.ts`：统一埋点接口 `analytics.track(event, params)`，非生产环境禁用，隐私政策同意后才上报
    - _需求: 1.2, 2.1, 2.6, 5.6, 11.6, 13.1, 13.2, 13.3, 13.4_

  - [x]* 3.6 编写网络层与工具函数单元测试
    - 测试 Axios Interceptor：Token 注入、401 刷新重试、错误码映射
    - 测试 SSE 客户端：流解析、[DONE] 检测、60s 超时断开、断线处理
    - 测试 WebSocket 客户端：连接/断开/重连/心跳
    - 测试 Token Refresh Mutex：并发刷新只发一次请求
    - 测试 fileValidation：格式/大小校验、边界值
    - 测试 errorMap：状态码映射完整性
    - 测试 sanitize：恶意 HTML 过滤
    - _需求: 1.6, 4.4, 11.6_

  - [x]* 3.7 编写属性测试 — P4: 文件校验幂等性
    - **Property 4: 文件上传客户端校验幂等性**
    - 使用 fast-check 生成随机文件大小（0~100MB）+ 随机 MIME 类型
    - 断言对同一文件多次调用 `validateFile` 返回完全相同的 `{ isValid, error }` 结果
    - 断言文件大小超限时 `isValid=false`，文件类型不在允许列表时 `isValid=false`
    - **验证: 需求 2.1, 2.6, 5.6**

  - [x]* 3.8 编写属性测试 — P5: 错误状态码映射完整性
    - **Property 5: 错误状态码映射完整性**
    - 使用 fast-check 枚举所有已知状态码 `{401, 409, 415, 429, 500, 503}` + 随机错误响应体
    - 断言 Axios Response Interceptor 展示的提示信息与 `ERROR_MAP[statusCode]` 一致
    - 断言提示信息中不包含原始技术细节（堆栈跟踪、JSON 错误体、URL 路径）
    - **验证: 需求 11.1, 11.2, 11.3, 11.6**

- [x] 4. 检查点 — 网络层验证
  - 确保所有网络层测试通过，属性测试 P4/P5 通过。如有问题请向用户确认。

- [x] 5. Zustand 状态管理
  - [x] 5.1 实现 AuthStore
    - 创建 `src/stores/authStore.ts`
    - 实现 `login(email, password)` → 调用 `POST /admin/v1/auth/login`，存储 accessToken 到内存
    - 实现 `logout()` → 清除 accessToken，调用后端清除 cookie，跳转 `/login`
    - 实现 `setAccessToken(token)` 和 `checkTokenExpiry()` → 解析 JWT exp 字段，剩余 < 1h 返回 true
    - _需求: 4.1, 4.2, 4.5, 4.7_

  - [x] 5.2 实现 ChatStore
    - 创建 `src/stores/chatStore.ts`
    - 实现消息管理：`sendMessage`（Optimistic UI，生成 temp_id 立即展示）、`appendToken`（rAF 批量累积 streamingContent）、`finishStreaming`、`replaceTempId`
    - 实现 `loadThread(threadId)` → 调用 `GET /v1/threads/{thread_id}` 加载历史
    - 实现 `reconcileMessages(serverMessages)` → 本地/服务端消息合并：(1) 包含所有 server_msgs；(2) 保留未确认 optimistic 消息；(3) 按 createdAt 升序；(4) 去重
    - 实现 `setConnectionStatus` 管理连接状态
    - _需求: 1.1, 1.2, 1.6, 3.2, 3.3_

  - [x] 5.3 实现 SessionStore
    - 创建 `src/stores/sessionStore.ts`
    - 实现会话状态机：`active` ↔ `hitl_pending` ↔ `hitl_active` ↔ `resolved`
    - 实现 `createThread()` → 生成 uuidv4
    - 实现 `switchThread(threadId)` 和 `switchProtocol('sse' | 'websocket')`
    - 实现 `threads: ThreadMeta[]` 管理，支持按 lastMessageAt 排序
    - _需求: 3.1, 3.3, 12.1, 12.3_

  - [x] 5.4 实现 AdminStore（5 个 Slice）
    - 创建 `src/stores/adminStore.ts`，按设计文档拆分为 5 个独立 Slice Store：
    - `knowledgeStore`：`fetchDocuments`, `uploadDocument`, `deleteDocument`, `docFilter`（搜索 + 状态筛选）
    - `hitlStore`：`hitlSessions`, `activeHitlSession`, `takeHitlSession`, `endHitlSession`
    - `configStore`：`savePersona`, `saveModelConfig`, `saveRateLimitConfig`，页面加载时回填当前配置
    - `metricsStore`：`fetchMetrics(period)`, `metricsPeriod`（1d/7d/30d）
    - `sandboxStore`：`runSandbox(testCases)`, `sandboxResults`
    - _需求: 5.1, 5.2, 5.5, 5.7, 6.3, 6.5, 7.1, 7.2, 7.3, 7.7, 8.1, 8.2, 8.3, 9.2_

  - [x] 5.5 实现 IndexedDB 缓存层
    - 创建 `src/lib/cache.ts`：基于 idb-keyval 的 LRU 缓存
    - 实现 `CacheConfig`：maxSizeBytes=10MB, maxMessages=50/会话, maxThreads=20, ttlDays=7
    - 实现写入时总大小检查 → 超限按 `cachedAt` 升序淘汰最旧会话
    - 实现 TTL 过期自动清除（cachedAt + ttlDays < now）
    - 集成到 ChatStore：persist 中间件 hydrate/dehydrate
    - _需求: 3.6_

  - [x]* 5.6 编写 Store 单元测试
    - 测试 AuthStore：登录/登出状态切换、Token 过期检测、setAccessToken
    - 测试 ChatStore：消息添加、temp_id 替换、流式内容累积、reconcileMessages
    - 测试 SessionStore：会话状态机转换（active → hitl_pending → hitl_active → resolved）
    - 测试 AdminStore 各 Slice：CRUD 操作状态更新
    - _需求: 4.2, 1.1, 3.1, 12.1_

  - [x]* 5.7 编写属性测试 — P2: 消息顺序不变量
    - **Property 2: 消息顺序不变量**
    - 使用 fast-check 生成随机消息数组（1~100 条，随机时间戳）
    - 断言 ChatStore 中消息按 `createdAt` 时间戳升序排列
    - **验证: 需求 1.8, 3.2**

  - [x]* 5.8 编写属性测试 — P7: 消息 Reconciliation 合并正确性
    - **Property 7: 消息 Reconciliation 合并正确性**
    - 使用 fast-check 生成随机本地消息列表 + 随机服务端消息列表（含重叠/temp_id）
    - 断言合并结果：(1) 包含所有 server_msgs；(2) 保留未确认的 optimistic 消息；(3) 按 createdAt 升序；(4) 无重复消息
    - **验证: 需求 1.6**

  - [x]* 5.9 编写属性测试 — P8: IndexedDB 缓存 LRU 不变量
    - **Property 8: IndexedDB 缓存 LRU 不变量**
    - 使用 fast-check + fake-indexeddb 生成随机缓存写入序列（随机大小 1KB~5MB）
    - 断言写入后总缓存大小 ≤ 10MB
    - 断言超限时按 cachedAt 升序淘汰最旧会话
    - 断言读取缓存数据与写入数据一致（Round-Trip）
    - **验证: 需求 3.6**

  - [x]* 5.10 编写属性测试 — P3: JWT 令牌生命周期不变量
    - **Property 3: JWT 令牌生命周期不变量**
    - 使用 fast-check 生成随机 JWT 过期时间 + 并发请求数（1~10）
    - 断言有效期内所有请求携带有效 Token
    - 断言过期且刷新失败后用户被重定向至 `/login`
    - 断言并发刷新时实际发出的刷新请求恰好为 1 次
    - **验证: 需求 4.2, 4.4, 4.6**

- [x] 6. 检查点 — 状态管理验证
  - 确保所有 Store 单元测试通过，属性测试 P2/P3/P7/P8 通过。如有问题请向用户确认。

- [x] 7. 认证模块与路由布局
  - [x] 7.1 实现 LoginPage
    - 创建 `src/pages/LoginPage.tsx`
    - 邮箱 + 密码输入框，表单校验（非空、邮箱格式）
    - 调用 AuthStore.login()，成功后跳转 `/admin/metrics`
    - 登录失败展示"邮箱或密码错误"Toast
    - 键盘导航支持 + aria-label
    - _需求: 4.1, 4.3_

  - [x] 7.2 实现路由系统与 ProtectedRoute
    - 创建 `src/App.tsx`：React Router 路由配置
    - 实现 `ProtectedRoute` 组件：检查 AuthStore.isAuthenticated，未登录重定向 `/login`
    - 配置路由表：`/login`（公开）、`/chat`（API Key）、`/admin/*`（需登录）
    - `/admin` 默认重定向到 `/admin/metrics`
    - _需求: 10.2, 10.3_

  - [x] 7.3 实现 DashboardLayout
    - 创建 `src/pages/admin/DashboardLayout.tsx`
    - 侧边栏导航：数据看板、知识库管理、人工介入、配置中心、沙盒测试
    - 顶部展示当前用户邮箱 + 租户名称（从 AuthStore 读取）
    - 退出登录按钮 → 调用 AuthStore.logout()
    - 响应式：桌面端（≥1024px）侧边栏固定，平板端（≥768px）可折叠
    - 使用 React Router `<Outlet />` 渲染子路由
    - _需求: 10.1, 10.4, 10.6, 4.7_

  - [x] 7.4 实现自定义 Hooks
    - 创建 `src/hooks/useSSE.ts`：管理 SSE 连接生命周期，Token 累积 + rAF 批量更新 ChatStore
    - 创建 `src/hooks/useWebSocket.ts`：管理 WS 连接、心跳、重连、消息分发
    - 创建 `src/hooks/useTokenRefresh.ts`：监听 JWT 过期时间，剩余 < 1h 触发静默刷新
    - 创建 `src/hooks/useFileValidation.ts`：文件格式/大小校验，返回 `{ isValid, error }`
    - 创建 `src/hooks/useVirtualScroll.ts`：react-virtuoso 配置封装，动态高度 + 自动滚动
    - 创建 `src/hooks/useAnalytics.ts`：埋点事件上报封装
    - _需求: 1.2, 1.5, 1.9, 2.6, 4.4, 13.1_

  - [x]* 7.5 编写认证与路由单元测试
    - 测试 LoginPage：表单提交、登录成功跳转、登录失败提示
    - 测试 ProtectedRoute：未登录重定向、已登录正常渲染
    - 测试 DashboardLayout：导航菜单渲染、退出登录
    - _需求: 4.1, 4.3, 10.3_

- [x] 8. 检查点 — 认证与路由验证
  - 确保登录流程、路由守卫、DashboardLayout 渲染正常。如有问题请向用户确认。

- [x] 9. Chat_Widget 核心功能
  - [x] 9.1 实现 ChatWidget 主组件
    - 创建 `src/pages/chat/ChatWidget.tsx`
    - 接收 `ChatWidgetProps`（apiKey, theme, position, lang, primaryColor, bgColor, logoUrl）
    - 管理 SSE ↔ WebSocket 协议切换（基于 SessionStore.status），切换时保持消息列表滚动位置不变
    - 集成 useSSE / useWebSocket hooks
    - API Key 无效时（401）展示"配置错误，请联系管理员"提示，不展示聊天界面
    - _需求: 1.5, 14.1, 14.2, 14.4_

  - [x] 9.2 实现 MessageList 与虚拟滚动
    - 创建 `src/pages/chat/MessageList.tsx`：基于 react-virtuoso 的虚拟滚动消息列表
    - 开启动态高度测量模式，结合 ResizeObserver 监听气泡高度变化
    - 新消息到达时自动滚动到底部；用户浏览历史时展示"有新消息"浮动按钮
    - 向上滚动加载更早消息（分页加载）
    - 确保 1000+ 条消息无卡顿
    - _需求: 1.9, 3.4, 3.5_

  - [x] 9.3 实现 MessageBubble
    - 创建 `src/pages/chat/MessageBubble.tsx`
    - user 消息：右对齐，品牌色背景
    - assistant 消息：左对齐，react-markdown + remark-gfm 渲染，DOMPurify 清洗
    - human_agent 消息：左对齐，不同颜色/图标标记"人工客服"
    - 流式渲染：`isStreaming` 时展示 Typing_Indicator 动画
    - 底部：时间戳 + 反馈按钮（仅 assistant 消息，Thumb Up / Thumb Down）
    - 图片设置预设宽高比（16:9 Aspect Ratio Box）+ Skeleton 占位符，防止布局偏移
    - _需求: 1.2, 1.8, 12.2, 15.1, 设计补充-图片占位符_

  - [x] 9.4 实现 ChatInput
    - 创建 `src/pages/chat/ChatInput.tsx`
    - 文本输入框：`Shift + Enter` 换行、`Enter` 发送
    - AI 生成中禁用发送按钮，展示"AI 正在思考…"状态
    - 集成 Media_Uploader 入口（图片/语音按钮）
    - 移动端：使用 `window.visualViewport` API 处理软键盘弹起遮挡问题
    - _需求: 1.4, 2.8, 补充-iOS视口兼容_

  - [x] 9.5 实现 TypingIndicator
    - 创建 `src/pages/chat/TypingIndicator.tsx`
    - 流式接收时展示打字机动画效果
    - rAF 批量渲染：16ms 内累积 Token 后一次性追加，rAF 回调中 try-catch 包裹，错误通过 ChatStore.setError() 抛出
    - _需求: 1.2, 1.3, 设计补充-rAF与ErrorBoundary协调_

  - [x] 9.6 实现 ThreadList
    - 创建 `src/pages/chat/ThreadList.tsx`
    - 展示历史会话列表（标题 = 首条消息摘要，最后消息时间，消息数量）
    - "新建会话"按钮 → SessionStore.createThread()
    - 点击会话 → SessionStore.switchThread() + ChatStore.loadThread()
    - _需求: 3.1, 3.2, 3.3_

  - [x] 9.7 实现用户反馈组件
    - 在 MessageBubble 中集成 Thumb Up / Thumb Down 按钮
    - 点击 Thumb Down 展示反馈原因选择（"回答不准确"、"没有回答我的问题"、"回答太慢"、"其他"）+ 自由文本输入
    - 将反馈数据（thread_id, message_id, rating, reason）上报后端
    - _需求: 15.1, 15.2, 15.3_

  - [x]* 9.8 编写 Chat_Widget 组件测试
    - 测试 MessageBubble：不同 role 渲染、Markdown 渲染、反馈按钮交互
    - 测试 ChatInput：Enter 发送、Shift+Enter 换行、禁用状态
    - 测试 ThreadList：会话列表渲染、新建/切换会话
    - 测试 MessageList：虚拟滚动渲染、新消息自动滚动
    - _需求: 1.2, 1.4, 3.1, 15.1_

- [x] 10. 检查点 — Chat_Widget 核心验证
  - 确保 Chat_Widget 核心组件渲染正常，SSE 流式消息、虚拟滚动、反馈功能可用。如有问题请向用户确认。

- [x] 11. Chat_Widget 高级功能
  - [x] 11.1 实现 MediaUploader
    - 创建 `src/pages/chat/MediaUploader.tsx`
    - 图片上传：点击按钮 / 拖拽 / 粘贴（Ctrl+V / Cmd+V）上传，支持 jpg/png/webp
    - 上传前调用 imageCompress（>2MB 转 WebP，质量 0.8）
    - 语音录制：开始/暂停/继续/完成/取消按钮，最大 60 秒计时器，完成后预览播放和重录
    - 上传进度条展示，完成后展示缩略图（图片）或音频播放器（语音）
    - 客户端校验：图片 ≤ 10MB，语音 ≤ 5MB，格式不符时 Toast 提示
    - _需求: 2.1, 2.2, 2.3, 2.5, 2.6, 2.7, 补充-图片粘贴上传_

  - [x] 11.2 实现 HITL 交互（C 端）
    - 在 ChatWidget 中监听 SessionStore.status 变化
    - `hitl_active` 状态：展示"已转接人工客服，请稍候"提示，隐藏 AI 思考指示器
    - 接收并展示 human_agent 消息（不同颜色/图标）
    - 恢复 `active` 状态：展示"已恢复 AI 客服"提示
    - 超时 60s 无人响应：展示"当前无客服在线，已为您创建工单"提示
    - _需求: 12.1, 12.2, 12.3, 12.4_

  - [x] 11.3 实现会话管理增强
    - 集成 IndexedDB 缓存：切换会话时优先从缓存加载，后台静默拉取最新数据
    - SSE 重连后调用 reconcileMessages 进行消息补偿
    - 语音识别阶段展示"语音识别中…"+ 波形指示器动画
    - 历史消息中图片支持点击放大查看 + 懒加载
    - _需求: 1.6, 2.4, 2.7, 3.6, 补充-语音波形指示器_

  - [x]* 11.4 编写 Chat_Widget 高级功能测试
    - 测试 MediaUploader：文件校验、上传进度、预览
    - 测试 HITL 交互：状态切换、消息展示
    - 测试会话缓存：IndexedDB 读写、缓存命中
    - _需求: 2.1, 2.6, 12.1, 3.6_

- [x] 12. 检查点 — Chat_Widget 完整验证
  - 确保多模态上传、HITL 交互、会话缓存功能正常。如有问题请向用户确认。

- [x] 13. Admin_Dashboard 页面
  - [x] 13.1 实现 MetricsDashboard
    - 创建 `src/pages/admin/MetricsDashboard.tsx`
    - 概览指标卡片：总对话数、转人工次数、转人工率（`GET /admin/v1/metrics/overview`）
    - Token 消耗统计：总 Token 数、消息数量（`GET /admin/v1/metrics/tokens`）
    - 用户满意度指标：Thumb Up 率
    - 时间范围选择器（1d / 7d / 30d），切换后重新加载
    - 折线图（Token 消耗趋势/天）+ 柱状图（对话数分布），使用 Recharts
    - "高频未命中问题"列表（`GET /admin/v1/metrics/missed-queries`）
    - 手动刷新按钮，不自动轮询
    - 数据加载中展示 Skeleton 骨架屏
    - _需求: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 15.4_

  - [x] 13.2 实现 KnowledgeManager
    - 创建 `src/pages/admin/KnowledgeManager.tsx`
    - 文档上传：拖拽 + 文件选择器，客户端校验 ≤ 50MB（`POST /admin/v1/knowledge/docs`）
    - 文档列表：文件名、上传时间、处理状态（pending/processing/completed/failed）、分块数量
    - 空状态设计 + "立即上传"引导按钮
    - processing 状态文档指数退避轮询（初始 3s，最大 15s），completed/failed 停止轮询
    - failed 状态展示错误信息 + "重试"按钮（`POST /admin/v1/knowledge/docs/{id}/retry`）
    - 删除功能：ConfirmDialog 确认后调用 `DELETE /admin/v1/knowledge/docs/{id}`
    - 按文件名搜索 + 按状态筛选
    - 数据加载中展示 Skeleton 骨架屏
    - _需求: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 8.6_

  - [x] 13.3 实现 HITLPanel
    - 创建 `src/pages/admin/HITLPanel.tsx`
    - WebSocket 长连接（`WS /admin/v1/ws/hitl`），实时接收 `hitl_request` 事件
    - 待处理请求：红色角标 + 消息提示，展示会话 ID、触发原因、未解决轮次
    - 声音提示：用户首次点击页面后启用（浏览器自动播放策略），提供静音开关
    - "接管"按钮 → `POST /admin/v1/hitl/{session_id}/take`，成功后加载完整对话历史
    - 消息输入框：Admin_User 直接向 End_User 发送消息
    - "结束介入"按钮 → `POST /admin/v1/hitl/{session_id}/end`，恢复 AI 自动处理
    - 实时更新会话列表状态（pending/active/resolved/auto_escalated + 处理人信息）
    - WebSocket 断开时展示"连接中…"状态 + 自动重连
    - 数据加载中展示 Skeleton 骨架屏
    - _需求: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 8.6_

  - [x] 13.4 实现 ConfigPanel
    - 创建 `src/pages/admin/ConfigPanel.tsx`
    - Persona 配置：系统提示词（多行文本框）+ 机器人名称 + 问候语（`PUT /admin/v1/config/persona`）
    - 模型选择：主模型/备用模型下拉选择器 + 温度滑块 0.0~1.0（`PUT /admin/v1/config/model`）
    - 限流配置：租户级 RPS + 用户级 RPS 输入框（`PUT /admin/v1/config/rate-limit`）
    - "清除语义缓存"按钮（`POST /admin/v1/cache/clear`）+ 确认提示
    - 页面加载时从后端获取当前配置并回填表单
    - 保存成功 Toast 通知；保存失败展示错误信息，保留表单内容不清空
    - "嵌入代码生成器"：选择配置后自动生成可复制的 `<script>` 代码片段
    - _需求: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 14.3_

  - [x] 13.5 实现 SandboxRunner
    - 创建 `src/pages/admin/SandboxRunner.tsx`
    - 测试用例输入：query + reference + contexts 多组输入
    - "运行测试"按钮 → `POST /admin/v1/sandbox/run`
    - 结果展示：Faithfulness / Context Precision / Context Recall / Answer Relevancy 得分 + 阈值
    - 颜色编码：通过（绿色）/ 未通过（红色），failed 时高亮未通过指标
    - 对比视图：左侧旧配置得分 vs 右侧新配置得分，点击差异项对比回答
    - 测试用例集保存到 localStorage（最多 10 个），按名称加载历史用例集
    - _需求: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 补充-沙盒对比视图_

  - [x]* 13.6 编写 Admin_Dashboard 页面测试
    - 测试 MetricsDashboard：指标卡片渲染、时间范围切换、图表渲染
    - 测试 KnowledgeManager：上传流程、列表渲染、删除确认、搜索筛选
    - 测试 HITLPanel：WebSocket 消息接收、接管/结束操作
    - 测试 ConfigPanel：表单回填、保存成功/失败、嵌入代码生成
    - 测试 SandboxRunner：用例输入、结果展示、颜色编码
    - _需求: 8.1, 5.1, 6.1, 7.1, 9.1_

- [x] 14. 检查点 — Admin_Dashboard 验证
  - 确保所有 Admin 页面渲染正常，API 对接、表单交互、实时通信功能可用。如有问题请向用户确认。

- [x] 15. Web Component 嵌入与主题定制
  - [x] 15.1 实现 embed.tsx 入口
    - 创建 `src/embed.tsx`：Web Component 注册入口
    - 定义 `<cuckoo-chat>` 自定义元素，使用 Shadow DOM 实现样式隔离
    - 读取 `data-*` 属性（api-key, theme, position, lang）或 `window.CuckooConfig` 配置对象
    - 在 Shadow Root 中挂载 React 应用（ChatWidget 组件）
    - 通过 `adoptedStyleSheets` 或 `style.setProperty()` 注入品牌色/Logo 到 Shadow Root
    - _需求: 10.5, 14.1, 14.2, 设计补充-Web Component主题注入_

  - [x] 15.2 实现主题系统
    - 支持 `light` / `dark` 模式切换
    - CSS 变量：`--ce-primary-color`、`--ce-bg-color`、Logo URL
    - Shadow DOM 内样式通过 Tailwind CSS 编译后注入
    - 确保嵌入模式下不污染宿主页面 CSS
    - _需求: 14.2_

  - [x] 15.3 配置 Vite 双入口构建
    - 更新 `vite.config.ts`：rollupOptions.input 配置 main + embed 双入口
    - embed.js 单文件输出（不拆分 chunk），entryFileNames 特殊处理
    - 确保 embed.js gzip 后 < 150KB
    - _需求: 10.5, 设计-性能SLA_

  - [x]* 15.4 编写 Web Component 测试
    - 测试 `<cuckoo-chat>` 自定义元素注册和渲染
    - 测试 data-* 属性读取和主题注入
    - 测试 Shadow DOM 样式隔离
    - _需求: 10.5, 14.1_

- [x] 16. 检查点 — Web Component 验证
  - 确保 embed.js 构建成功，Web Component 可嵌入测试页面，主题定制生效，样式隔离正常。如有问题请向用户确认。

- [ ] 17. PBT 属性测试与 E2E 测试
  - [x]* 17.1 编写属性测试 — P1: SSE Token 流渲染完整性
    - **Property 1: SSE Token 流渲染完整性（Round-Trip）**
    - 使用 Playwright + fast-check 生成随机 Token 序列（1~500 个，含中文/英文/Markdown/特殊字符）
    - 模拟 SSE 事件流逐个推送 Token
    - 断言最终 Message_Bubble 的纯文本内容等于所有 Token 的拼接（Markdown 渲染后提取纯文本）
    - **验证: 需求 1.1, 1.2**

  - [x]* 17.2 编写属性测试 — P6: 流式 Markdown 渲染 XSS 防御
    - **Property 6: 流式 Markdown 渲染 XSS 防御不变量**
    - 使用 Playwright + fast-check 生成随机恶意 payload（`<script>`、`onclick=`、`javascript:`、`onerror=`、不闭合标签）
    - 模拟 SSE 推送恶意 Token 序列
    - 断言渲染后 DOM 中不存在 `<script>` 元素、`on*` 事件处理器属性或 `javascript:` 协议链接
    - **验证: 需求 1.2**

  - [~]* 17.3 编写 E2E 测试 — 登录流程
    - Playwright 测试：输入邮箱密码 → 登录成功 → 跳转 Dashboard
    - 测试未登录访问 /admin → 重定向 /login
    - _需求: 4.1, 10.3_

  - [~]* 17.4 编写 E2E 测试 — 聊天流程
    - Playwright 测试：发送消息 → SSE 流式接收 → 消息完成展示
    - 测试文件上传 → 预压缩 → 展示缩略图
    - _需求: 1.1, 2.1_

  - [~]* 17.5 编写 E2E 测试 — HITL 流程
    - Playwright 测试：接收介入请求 → 接管 → 发送消息 → 结束介入
    - _需求: 6.3, 6.4, 6.5_

  - [~]* 17.6 编写 E2E 测试 — 知识库管理
    - Playwright 测试：上传文档 → 轮询状态 → 完成
    - _需求: 5.1, 5.3_

- [x] 18. 检查点 — 测试验证
  - 确保所有 PBT 属性测试（P1-P8）通过，E2E 测试通过。如有问题请向用户确认。

- [x] 19. 性能优化与构建部署
  - [x] 19.1 实现路由懒加载与代码分割
    - 使用 `React.lazy()` + `Suspense` 对所有 Admin 页面实现路由级懒加载
    - 配置 Vite 代码分割策略，vendor chunk 分离（react/zustand/radix/recharts）
    - 确保 FCP < 1.5s（桌面端）
    - _需求: 补充-性能SLA_

  - [x] 19.2 实现埋点集成
    - 在路由切换时自动采集 `page_view` 事件
    - 在关键交互点集成埋点：`message_sent`, `message_received`, `file_upload`, `hitl_requested`, `config_changed`, `sandbox_run`, `error_occurred`
    - 确保非生产环境禁用上报，隐私政策同意后才上报
    - _需求: 13.1, 13.2, 13.3_

  - [x] 19.3 创建 Docker + Nginx 部署配置
    - 创建 `frontend/Dockerfile`：多阶段构建（node:20-alpine build → nginx:alpine serve）
    - 创建 `frontend/nginx.conf`：SPA 路由回退、API 反向代理（/v1/ → api-gateway:8000, /admin/v1/ → admin-service:8002）、WebSocket upgrade 支持
    - 配置安全 Headers：X-Content-Type-Options, X-Frame-Options, CSP
    - 配置静态资源缓存：embed.js 24h、assets/ 1年 immutable
    - _需求: 设计-Docker部署, 设计-Nginx配置_

  - [x] 19.4 配置 ESLint + Prettier + Husky
    - 配置 ESLint（TypeScript + React 规则）
    - 配置 Prettier 代码格式化
    - 配置 Husky pre-commit hook：lint-staged
    - _需求: 技术栈-代码规范_

  - [x]* 19.5 编写构建验证测试
    - 验证 `pnpm build` 产物：main 入口 + embed.js 单文件
    - 验证 embed.js gzip 体积 < 150KB
    - 验证 Nginx 配置语法正确
    - _需求: 设计-性能SLA_

  - [x] 19.6 实现 API Mock（MSW）
    - 配置 MSW（Mock Service Worker）拦截所有后端 API 请求
    - 为每个 API 端点提供 Mock 数据（与后端 API 契约对齐）
    - 支持开发模式下独立运行前端（无需后端服务）
    - 在 Vitest 中集成 MSW 作为测试 Mock 层
    - _需求: 全局（前端独立开发支持）_

  - [x]* 19.7 配置 CI/CD（GitHub Actions）
    - 创建 `.github/workflows/frontend-ci.yml`
    - 流水线：`pnpm install` → `pnpm lint` → `pnpm test` → `pnpm build`
    - 属性测试（P1-P8）在 CI 中运行
    - Docker 构建推送到容器仓库
    - _需求: 全局（自动化构建测试）_

  - [x]* 19.8 编写无障碍测试
    - 集成 axe-core 到 Playwright E2E 测试
    - 测试键盘导航（Tab 顺序、Enter 激活、Escape 关闭）
    - 测试 aria-label 覆盖率
    - 测试颜色对比度 ≥ 4.5:1（WCAG 2.1 AA）
    - _需求: 10.7_

  - [x]* 19.9 配置 Lighthouse CI
    - 集成 Lighthouse CI 到 GitHub Actions
    - 设置性能回归检测阈值：FCP < 1.5s、INP < 200ms、LCP < 2.5s
    - 构建失败条件：任一核心指标低于阈值
    - _需求: 补充-性能SLA_

- [x] 20. 最终检查点 — 全量验证
  - 确保 `pnpm build` 成功，所有单元测试、属性测试（P1-P8）、E2E 测试通过。Docker 构建成功。如有问题请向用户确认。

## 备注

- 标记 `*` 的子任务为可选测试任务，可跳过以加速 MVP 交付
- 每个任务引用具体需求编号，确保需求可追溯
- 检查点确保增量验证，及时发现问题
- 属性测试（P1-P8）验证通用正确性属性，单元测试验证具体示例和边界条件
- 所有代码使用 TypeScript，测试使用 Vitest + Testing Library + Playwright + fast-check
