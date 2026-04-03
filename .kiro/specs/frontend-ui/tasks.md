# 实施计划：Cuckoo-Echo 前端 UI

## 概述

基于 React 18 + TypeScript + Zustand + Radix UI + Tailwind CSS + Vite + pnpm 技术栈，按模块递增交付前端两大模块（Chat_Widget + Admin_Dashboard）。任务按阶段组织，每个阶段结束设置检查点，确保增量验证。

## 任务列表

- [ ] 1. 项目脚手架与基础设施
  - [ ] 1.1 初始化前端项目结构
    - 使用 `pnpm create vite frontend --template react-ts` 创建项目
    - 安装核心依赖：`zustand`, `@radix-ui/react-*`, `tailwindcss`, `axios`, `react-router-dom`, `react-markdown`, `remark-gfm`, `dompurify`, `react-virtuoso`, `recharts`, `idb-keyval`, `uuid`
    - 安装开发依赖：`vitest`, `@testing-library/react`, `fast-check`, `msw`, `fake-indexeddb`, `@types/dompurify`
    - 配置 `tailwind.config.ts`、`tsconfig.json`、`vite.config.ts`（含双入口 main + embed）
    - 创建目录结构：`src/components/`, `src/pages/chat/`, `src/pages/admin/`, `src/stores/`, `src/network/`, `src/hooks/`, `src/lib/`, `src/types/`, `src/styles/`
    - 创建 `src/styles/globals.css`（Tailwind 入口 + CSS 变量 `--ce-primary-color`, `--ce-bg-color`）
    - _需求: 10.2, 10.5, 10.7_

  - [ ] 1.2 定义 TypeScript 类型系统
    - 创建 `src/types/index.ts`，定义所有核心接口：`Message`, `MediaAttachment`, `ToolCall`, `ThreadMeta`, `AdminUser`, `KnowledgeDoc`, `HITLSession`, `PersonaConfig`, `ModelConfig`, `RateLimitConfig`, `MetricsOverview`, `TestCase`, `SandboxResult`, `ChatWidgetProps`
    - 定义联合类型：`SessionStatus`, `ConnectionStatus`, `DocStatus`
    - _需求: 1.1, 2.1, 3.1, 4.2, 5.2, 6.1, 7.1, 8.1, 9.1_

  - [ ] 1.3 实现共享 UI 组件
    - 创建 `src/components/Toast.tsx`：基于 Radix UI Toast 的通知组件
    - 创建 `src/components/Skeleton.tsx`：骨架屏组件（卡片/列表/文本三种变体）
    - 创建 `src/components/OfflineBanner.tsx`：监听 `navigator.onLine` + `online/offline` 事件的全局离线横幅
    - 创建 `src/components/ErrorBoundary.tsx`：React Error Boundary，降级 UI + 刷新按钮
    - 创建 `src/components/ConfirmDialog.tsx`：基于 Radix UI AlertDialog 的确认对话框
    - _需求: 8.6, 11.4, 11.6_

- [ ] 2. 检查点 — 项目基础设施验证
  - 确保 `pnpm build` 成功，`pnpm test` 框架可运行，所有类型定义无编译错误。如有问题请向用户确认。

- [ ] 3. 网络层与工具函数
  - [ ] 3.1 实现 Axios 实例与拦截器
    - 创建 `src/network/axios.ts`：配置 baseURL、timeout 30s、withCredentials
    - 实现 Request Interceptor：从 AuthStore 读取 accessToken 注入 Authorization Header
    - 实现 Response Interceptor：401 触发 Token Refresh Mutex → 重试/跳转登录；429 读取 Retry-After 自动延迟重试；其他错误码映射为用户友好提示（Toast）
    - _需求: 4.6, 11.1, 11.2, 11.3, 11.5, 11.6_

  - [ ] 3.2 实现 Token Refresh Mutex
    - 创建 `src/lib/tokenRefresh.ts`：单例 Promise 模式，并发刷新请求只发出一次实际请求
    - 刷新成功更新 AuthStore，刷新失败调用 logout 并跳转 `/login`
    - _需求: 4.4, 4.5_

  - [ ] 3.3 实现 SSE 客户端
    - 创建 `src/network/sseClient.ts`：基于 fetch + ReadableStream 的 SSE 客户端
    - 实现 POST 方式 SSE 连接（`POST /v1/chat/completions`，`stream=true`）
    - 实现 SSE `data:` 行解析、`[DONE]` 检测、AbortController 断开
    - 实现指数退避重连（初始 1s，最大 30s）
    - _需求: 1.1, 1.3, 1.6_

  - [ ] 3.4 实现 WebSocket 客户端
    - 创建 `src/network/wsClient.ts`：WebSocket 封装类
    - 实现连接/断开/重连（指数退避，最大 30s）
    - 实现心跳机制（每 30s 发送 ping）
    - 实现消息分发（onMessage 回调）
    - _需求: 1.5, 6.1, 6.7_

  - [ ] 3.5 实现工具函数库
    - 创建 `src/lib/sanitize.ts`：DOMPurify 封装，配置允许的标签/属性白名单
    - 创建 `src/lib/errorMap.ts`：HTTP 状态码 → 用户提示映射表（401/409/415/429/500/503）
    - 创建 `src/lib/fileValidation.ts`：文件格式/大小校验函数 `validateFile(file, category)`
    - 创建 `src/lib/imageCompress.ts`：Canvas API 图片预压缩（>2MB 转 WebP，质量 0.8）
    - 创建 `src/lib/analytics.ts`：统一埋点接口 `analytics.track(event, params)`，非生产环境禁用
    - _需求: 1.2, 2.1, 2.6, 5.6, 11.6, 13.1, 13.2, 13.4_

  - [ ]* 3.6 编写网络层与工具函数单元测试
    - 测试 Axios Interceptor：Token 注入、401 刷新重试、错误码映射
    - 测试 SSE 客户端：流解析、[DONE] 检测、断线处理
    - 测试 WebSocket 客户端：连接/断开/重连/心跳
    - 测试 Token Refresh Mutex：并发刷新只发一次请求
    - 测试 fileValidation：格式/大小校验、边界值
    - 测试 errorMap：状态码映射完整性
    - _需求: 1.6, 4.4, 11.6_

  - [ ]* 3.7 编写属性测试 — P4: 文件校验幂等性
    - **Property 4: 文件上传客户端校验幂等性**
    - 使用 fast-check 生成随机文件大小（0~100MB）+ 随机 MIME 类型
    - 断言对同一文件多次调用 `validateFile` 返回完全相同的 `{ isValid, error }` 结果
    - 断言文件大小超限时 `isValid=false`，文件类型不在允许列表时 `isValid=false`
    - **验证: 需求 2.1, 2.6, 5.6**

  - [ ]* 3.8 编写属性测试 — P5: 错误状态码映射完整性
    - **Property 5: 错误状态码映射完整性**
    - 使用 fast-check 枚举所有已知状态码 `{401, 409, 415, 429, 500, 503}` + 随机错误响应体
    - 断言 Axios Response Interceptor 展示的提示信息与 `ERROR_MAP[statusCode]` 一致
    - 断言提示信息中不包含原始技术细节（堆栈跟踪、JSON 错误体、URL 路径）
    - **验证: 需求 11.1, 11.2, 11.3, 11.6**

- [ ] 4. 检查点 — 网络层验证
  - 确保所有网络层测试通过，属性测试 P4/P5 通过。如有问题请向用户确认。

- [ ] 5. Zustand 状态管理
  - [ ] 5.1 实现 AuthStore
    - 创建 `src/stores/authStore.ts`
    - 实现 `login(email, password)` → 调用 `POST /admin/v1/auth/login`，存储 accessToken 到内存
    - 实现 `logout()` → 清除 accessToken，调用后端清除 cookie，跳转 `/login`
    - 实现 `setAccessToken(token)` 和 `checkTokenExpiry()` → 剩余 < 1h 返回 true
    - _需求: 4.1, 4.2, 4.5, 4.7_

  - [ ] 5.2 实现 ChatStore
    - 创建 `src/stores/chatStore.ts`
    - 实现消息管理：`sendMessage`, `appendToken`（rAF 批量累积）, `finishStreaming`, `replaceTempId`
    - 实现 `loadThread(threadId)` → 调用 `GET /v1/threads/{thread_id}` 加载历史
    - 实现 `reconcileMessages(serverMessages)` → 本地/服务端消息合并，去重 + 保留 optimistic 消息 + 按时间排序
    - 实现 `setConnectionStatus` 管理连接状态
    - _需求: 1.1, 1.2, 1.6, 3.2, 3.3_

  - [ ] 5.3 实现 SessionStore
    - 创建 `src/stores/sessionStore.ts`
    - 实现会话状态机：`active` ↔ `hitl_pending` ↔ `hitl_active` ↔ `resolved`
    - 实现 `createThread()` → 生成 uuidv4
    - 实现 `switchThread(threadId)` 和 `switchProtocol('sse' | 'websocket')`
    - _需求: 3.1, 3.3, 12.1, 12.3_

  - [ ] 5.4 实现 AdminStore
    - 创建 `src/stores/adminStore.ts`
    - 实现知识库管理：`fetchDocuments`, `uploadDocument`, `deleteDocument`
    - 实现 HITL 管理：`takeHitlSession`, `endHitlSession`
    - 实现配置管理：`savePersona`, `saveModelConfig`, `saveRateLimitConfig`
    - 实现指标管理：`fetchMetrics(period)`
    - 实现沙盒管理：`runSandbox(testCases)`
    - _需求: 5.1, 5.2, 5.5, 6.3, 6.5, 7.1, 7.2, 7.3, 8.1, 8.2, 9.2_

  - [ ] 5.5 实现 IndexedDB 缓存层
    - 创建 `src/lib/cache.ts`：基于 idb-keyval 的 LRU 缓存
    - 实现 `CacheConfig`：maxSizeBytes=10MB, maxMessages=50/会话, maxThreads=20, ttlDays=7
    - 实现写入时总大小检查 → 超限按 `cachedAt` 升序淘汰最旧会话
    - 实现 TTL 过期自动清除
    - 集成到 ChatStore：persist 中间件 hydrate/dehydrate
    - _需求: 3.6_

  - [ ]* 5.6 编写 Store 单元测试
    - 测试 AuthStore：登录/登出状态切换、Token 过期检测
    - 测试 ChatStore：消息添加、temp_id 替换、流式内容累积
    - 测试 SessionStore：会话状态机转换
    - 测试 AdminStore：CRUD 操作状态更新
    - _需求: 4.2, 1.1, 3.1, 12.1_

  - [ ]* 5.7 编写属性测试 — P2: 消息顺序不变量
    - **Property 2: 消息顺序不变量**
    - 使用 fast-check 生成随机消息数组（1~100 条，随机时间戳）
    - 断言 ChatStore 中消息按 `createdAt` 时间戳升序排列
    - **验证: 需求 1.8, 3.2**

  - [ ]* 5.8 编写属性测试 — P7: 消息 Reconciliation 合并正确性
    - **Property 7: 消息 Reconciliation 合并正确性**
    - 使用 fast-check 生成随机本地消息列表 + 随机服务端消息列表（含重叠/temp_id）
    - 断言合并结果：(1) 包含所有 server_msgs；(2) 保留未确认的 optimistic 消息；(3) 按 createdAt 升序；(4) 无重复消息
    - **验证: 需求 1.6**

  - [ ]* 5.9 编写属性测试 — P8: IndexedDB 缓存 LRU 不变量
    - **Property 8: IndexedDB 缓存 LRU 不变量**
    - 使用 fast-check + fake-indexeddb 生成随机缓存写入序列（随机大小 1KB~5MB）
    - 断言写入后总缓存大小 ≤ 10MB
    - 断言超限时按 cachedAt 升序淘汰最旧会话
    - 断言读取缓存数据与写入数据一致（Round-Trip）
    - **验证: 需求 3.6**

  - [ ]* 5.10 编写属性测试 — P3: JWT 令牌生命周期不变量
    - **Property 3: JWT 令牌生命周期不变量**
    - 使用 fast-check 生成随机 JWT 过期时间 + 并发请求数（1~10）
    - 断言有效期内所有请求携带有效 Token
    - 断言过期且刷新失败后用户被重定向至 `/login`
    - 断言并发刷新时实际发出的刷新请求恰好为 1 次
    - **验证: 需求 4.2, 4.4, 4.6**

- [ ] 6. 检查点 — 状态管理验证
  - 确保所有 Store 单元测试通过，属性测试 P2/P3/P7/P8 通过。如有问题请向用户确认。

- [ ] 7. Chat_Widget 页面组件
  - [ ] 7.1 实现 ChatWidget 主组件
    - 创建 `src/pages/chat/ChatWidget.tsx`
    - 接收 `ChatWidgetProps`（apiKey, theme, position, lang, primaryColor, bgColor, logoUrl）
    - 管理 SSE ↔ WebSocket 协议切换（基于 SessionStore.status）
    - 集成 useSSE / useWebSocket hooks
    - _需求: 1.5, 14.1, 14.2_
