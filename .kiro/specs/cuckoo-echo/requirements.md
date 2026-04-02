# 需求文档

## 项目简介

Cuckoo-Echo（布谷回响）是一个面向企业的百万日活 AI 智能客服 SaaS 平台。
平台以多租户隔离为基础，支持文字、语音、图片多模态输入，通过 LangGraph 编排 Agent 工作流，
结合 RAG 知识库检索与业务工具调用，为 B 端企业提供高并发、低延迟的智能客服能力，
并配套独立的管理后台供运营人员进行知识库管理、租户配置与人工介入。

---

## 词汇表

- **System**：Cuckoo-Echo 平台整体
- **Chat_Service**：负责处理 C 端用户对话的核心服务（FastAPI + LangGraph）
- **Admin_Service**：独立的管理后台 API 服务
- **Agent**：LangGraph 编排的 AI 工作流引擎
- **Router**：Agent 内部的意图分类与路由节点
- **RAG_Engine**：知识检索增强生成模块（Milvus 向量检索 + LLM 生成）
- **Tool_Executor**：Agent 内部的业务工具调用节点（查询订单、修改地址等）
- **ASR_Service**：语音转文本服务（基于 Whisper）
- **Vision_LLM**：支持图片理解的多模态大模型
- **Embedding_Service**：将文本转换为向量的嵌入模型服务
- **Knowledge_Pipeline**：文档解析、分块、向量化的异步处理管道
- **Tenant**：使用 Cuckoo-Echo 的企业客户（B 端租户）
- **End_User**：Tenant 旗下的 C 端最终用户
- **Admin_User**：Tenant 的运营/管理人员，使用管理后台
- **Gateway**：多租户 API 网关，负责鉴权、限流、Tenant-ID 解析
- **RLS**：PostgreSQL 行级安全策略（Row-Level Security）
- **PartitionKey**：Milvus 向量库的租户隔离键
- **Thread**：一次完整的对话会话，对应 LangGraph 的 thread_id
- **Checkpointer**：LangGraph 的状态持久化组件
- **OSS**：对象存储服务（存储图片、音频等媒体文件）
- **TTFT**：首字响应时间（Time To First Token）
- **DAU**：日活跃用户数（Daily Active Users）
- **GSLB**：全局负载均衡（Global Server Load Balancing）

---

## 需求列表


### 需求 1：多租户接入与隔离

**用户故事：** 作为企业租户，我希望我的数据与其他租户完全隔离，以确保业务数据安全不泄露。

#### 验收标准

1. WHEN 请求到达 Gateway 时，THE Gateway SHALL 从 Authorization Header 中解析 `tenant_id`，并在整个请求生命周期中透传该值。
2. IF 请求缺少有效的 API Key，THEN THE Gateway SHALL 返回 HTTP 401 状态码并拒绝请求。
3. THE System SHALL 在 PostgreSQL 的 `users`、`threads`、`messages` 表上启用 RLS 策略，使每条 SQL 查询仅能访问当前 `tenant_id` 对应的行。
4. WHEN Chat_Service 执行数据库操作时，THE Chat_Service SHALL 在同一事务开头执行 `SET LOCAL app.current_tenant = '{tenant_id}'`，以激活 RLS 过滤。
5. WHEN RAG_Engine 执行向量检索时，THE RAG_Engine SHALL 在 Milvus 查询中强制指定 `PartitionKey = tenant_id`，确保仅检索该租户的知识切片。
6. THE System SHALL 使用 Redis Key 前缀 `cuckoo:session:{tenant_id}:{user_id}` 隔离各租户的缓存数据。
7. IF 代码尝试插入 `tenant_id` 与当前上下文不匹配的数据，THEN THE System SHALL 由 PostgreSQL RLS 抛出异常并回滚事务。
8. THE System SHALL 支持在单个 Milvus Collection 内通过 PartitionKey 隔离不同租户的向量数据，而非为每个租户创建独立 Collection。

---

### 需求 2：多模态输入处理

**用户故事：** 作为 C 端用户，我希望能够发送语音和图片，以便在无法打字时也能获得客服帮助。

#### 验收标准

1. WHEN End_User 发送音频文件时，THE ASR_Service SHALL 将音频转换为文本，并将文本传递给 Chat_Service 进行后续处理。
2. WHEN End_User 发送图片时，THE Chat_Service SHALL 将图片上传至 OSS 并获取带签名的访问 URL，再将 URL 与用户文本一并传递给 Vision_LLM。
3. THE System SHALL 支持同时包含文本和图片 URL 的混合输入，Vision_LLM SHALL 对图文内容进行联合理解后生成回复。
4. IF ASR_Service 转写失败，THEN THE Chat_Service SHALL 返回错误提示，告知用户语音识别失败并建议改用文字输入。
5. IF 上传的文件格式不在支持列表（音频：wav/mp3/m4a；图片：jpg/png/webp）内，THEN THE Gateway SHALL 返回 HTTP 415 状态码。
6. THE System SHALL 在 `messages` 表的 `media_urls` JSONB 字段中记录本条消息关联的所有媒体文件 OSS 路径。
7. WHEN ASR_Service 完成转写后，THE Chat_Service SHALL 在 500ms 内将文本送入 Agent 处理流程。
8. WHEN End_User 发送语音或图片时，THE Chat_Service SHALL 向前端推送"处理中"状态事件，以在多模态预处理阶段提供过渡 UI 反馈。

---

### 需求 3：RAG 知识库问答

**用户故事：** 作为 C 端用户，我希望系统能够基于企业知识库准确回答我的问题，而不是给出通用的无关回复。

#### 验收标准

1. WHEN End_User 发送问题时，THE RAG_Engine SHALL 将问题向量化后在 Milvus 中检索 Top-K（K 默认为 5）个相关知识切片。
2. WHEN RAG_Engine 完成向量检索后，THE RAG_Engine SHALL 对召回的 Top-K 切片执行 Rerank（重排序），将最终输入给 LLM 的上下文精简为 Top-3 最相关切片，以减少幻觉并降低 Token 消耗。
3. WHEN RAG_Engine 完成检索后，THE Agent SHALL 将检索到的知识切片与对话历史一并传递给 LLM 生成最终回复。
3. THE Knowledge_Pipeline SHALL 支持解析 PDF、Word、HTML、纯文本格式的文档，并按配置的分块策略（chunk_size、chunk_overlap）切分为知识片段。
4. WHEN 文档被上传至 Admin_Service 后，THE Knowledge_Pipeline SHALL 异步完成解析、分块、调用 Embedding_Service 向量化，并将向量写入 Milvus。IF 任意处理步骤失败，THE Knowledge_Pipeline SHALL 将失败任务写入死信队列（DLQ），并将文档状态标记为 `failed`，支持 Admin_User 手动重试或人工介入处理，确保失败任务不被静默丢弃。
5. IF 知识库中无相关内容（相似度低于阈值 0.7），THEN THE Agent SHALL 告知用户无法从知识库中找到答案，并提供转人工选项。
6. THE Embedding_Service SHALL 对相同文本输入始终返回相同的向量表示（幂等性）。
7. THE Knowledge_Pipeline SHALL 支持对已有文档进行更新和删除，更新后 Milvus 中对应的旧向量 SHALL 被替换。
8. FOR ALL 有效的知识文档，经过解析 → 向量化 → 检索的完整流程后，原始文档的核心语义 SHALL 能够被检索命中（往返一致性）。

---

### 需求 4：业务工具调用（Tool Use）

**用户故事：** 作为 C 端用户，我希望直接在对话中查询订单状态或修改收货地址，而无需跳转到其他页面。

#### 验收标准

1. WHEN Router 识别到用户意图为业务操作时，THE Agent SHALL 将请求路由至 Tool_Executor 节点，而非 RAG_Engine 节点。Router SHALL 优先使用规则引擎（正则/关键词匹配）对高频标准意图（如"查订单"、"改地址"）进行确定性路由，仅在规则未命中时才调用 LLM 进行意图分类，以保证高频业务路由准确率 ≥ 99.9%。
2. THE Tool_Executor SHALL 支持以下 MVP 工具：查询订单状态（`get_order_status`）、修改收货地址（`update_shipping_address`）。
3. WHEN Tool_Executor 调用外部 API 或查询 PostgreSQL 时，THE Tool_Executor SHALL 在请求中携带 `tenant_id` 以确保数据隔离。
4. IF 工具调用返回错误或超时（超过 5 秒），THEN THE Agent SHALL 向用户返回友好的错误提示，并记录工具调用失败日志。
5. THE System SHALL 在 `messages` 表的 `tool_calls` JSONB 字段中记录每次工具调用的名称、入参和返回结果。
6. WHEN Tool_Executor 完成调用后，THE Agent SHALL 将工具返回结果传递给 LLM 生成自然语言回复。

---

### 需求 5：流式对话响应（Streaming）

**用户故事：** 作为 C 端用户，我希望看到打字机效果的逐字输出，以减少等待焦虑感。

#### 验收标准

1. THE Chat_Service SHALL 通过 SSE（Server-Sent Events）协议向客户端推送 LLM 生成的 Token 流。
2. WHEN LLM 开始生成时，THE Chat_Service SHALL 在规定时间内推送第一个 Token，TTFT 上限按场景分级：纯文本/语义缓存命中 < 500ms；RAG 查询 < 1200ms；多模态/Vision LLM < 3000ms。TTFT 的计时起点定义为：纯文本输入时为 Gateway 接收到请求的时刻；多模态输入（语音/图片）时为 ASR 转写完成或图片 OSS URL 获取完毕、Agent 正式开始处理的时刻。
3. THE System SHALL 同时支持 SSE、WebSocket、HTTP 三种接入协议，客户端可根据场景选择。
4. WHEN 对话流结束时，THE Chat_Service SHALL 发送 `[DONE]` 事件标记流结束，并关闭 SSE 连接。
5. IF 客户端断开连接，THEN THE Chat_Service SHALL 静默接收完当前正在生成的 Chunk，完成本次 Token 统计，并将截断的回复以 `interrupted` 状态写入 `messages` 表，确保计费准确性。后端 LLM 调用 SHALL 使用 `asyncio.shield` 包装，确保客户端断开不会中断与外部大模型的网络 IO。
6. WHILE LLM 正在生成时，THE Chat_Service SHALL 保持 SSE 连接活跃，每隔 15 秒发送一次心跳事件以防止连接超时。

---

### 需求 6：对话状态管理与记忆

**用户故事：** 作为 C 端用户，我希望系统能记住本次对话的上下文，不需要我重复说明背景信息。

#### 验收标准

1. THE Checkpointer SHALL 使用 Redis 存储当前活跃会话的 LangGraph Graph State，读写延迟 SHALL 低于 10ms（P99）。Redis 在此严格作为热数据缓存层，PostgreSQL 为唯一持久化数据源。
2. WHEN 会话结束或空闲超过 30 分钟时，THE System SHALL 将对话历史异步写入 Kafka，由消费者批量持久化至 PostgreSQL `messages` 表。
3. WHEN End_User 在同一 Thread 内发送新消息时，THE Agent SHALL 从 Redis Checkpointer 中恢复完整的对话上下文后再处理新消息。
4. THE System SHALL 为每个 Thread 分配唯一的 UUID，该 UUID 同时作为 LangGraph 的 `thread_id` 和 PostgreSQL `threads` 表的主键。
5. IF Redis 中的 Session 已过期，THEN THE Chat_Service SHALL 从 PostgreSQL 中重建最近 N 条（N 默认为 20）消息作为上下文，继续对话。
6. THE System SHALL 在 `messages` 表中记录每条消息消耗的 Token 数量，用于租户计费统计。
7. THE System SHALL 采用 Write-Through 策略管理对话状态：每轮对话完成后（或每 N 轮，N 可配置），Chat_Service SHALL 立即将增量消息同步写入 PostgreSQL，同时更新 Redis 缓存。Redis 的 TTL 主动续期（每次新消息重置为 30 分钟）仅用于防止活跃会话被自然过期，不作为数据持久化的触发条件。
8. THE System SHALL 对同一 Thread ID 的并发请求在服务端实现请求队列化（per-thread queue），确保同一会话的消息按序处理，避免高并发下的 Graph State 脏写，优先于依赖分布式锁的乐观并发控制。每个 Thread 的队列长度上限为 100 条，超出上限时 THE System SHALL 拒绝新请求并返回 HTTP 503，同时触发背压告警；队列积压超过阈值时 THE System SHALL 向监控系统上报指标。

---

### 需求 7：人工介入（Human-in-the-Loop）

**用户故事：** 作为运营人员，我希望在 AI 无法解决问题时能够接管对话，以保障用户体验。

#### 验收标准

1. WHEN Router 判断用户情绪为负面或连续 3 轮对话未解决问题时，THE Agent SHALL 暂停 Graph 执行并通过 WebSocket 向 Admin_Service 推送人工介入请求。
2. WHEN Admin_User 接管会话时，THE System SHALL 将 Thread 状态更新为 `human_intervention`，并停止 Agent 自动回复。
3. WHEN Admin_User 结束人工介入时，THE System SHALL 将 Thread 状态恢复为 `active`，Agent 可继续处理后续消息。
4. THE Admin_Service SHALL 向 Admin_User 展示完整的对话历史（包含 AI 回复和工具调用记录），以便快速了解上下文。
5. IF 人工介入请求在 60 秒内无人响应，THEN THE System SHALL 向 End_User 发送等待提示，并继续尝试通过 Agent 处理；IF Agent 仍无法解决且无客服在线，THEN THE System SHALL 自动创建工单并向 End_User 承诺回复时限（如次日工作时间内），实现优雅降级。
6. THE System SHALL 记录每次人工介入的开始时间、结束时间和处理人 ID，用于运营数据统计。

---

### 需求 8：知识库管理（Admin）

**用户故事：** 作为运营人员，我希望能够上传和管理企业知识文档，以确保 AI 回答基于最新的业务信息。

#### 验收标准

1. THE Admin_Service SHALL 提供文档上传接口，支持单次上传最大 50MB 的文件。
2. WHEN 文档上传成功后，THE Knowledge_Pipeline SHALL 在后台异步处理，Admin_User SHALL 能够通过接口查询处理进度（pending / processing / completed / failed）。
3. THE Admin_Service SHALL 支持对已上传文档执行删除操作，删除后 Milvus 中对应的向量 SHALL 在 60 秒内被清除。
4. THE Admin_Service SHALL 允许 Admin_User 配置租户专属的系统提示词（System Prompt）和机器人 Persona。
5. THE Admin_Service SHALL 允许 Admin_User 为租户选择使用的 LLM 模型（从平台支持的模型列表中选择）。
6. WHERE 租户启用了语义缓存功能，THE System SHALL 对语义相似度超过 0.95 的重复问题直接返回缓存答案，不调用 LLM。
7. THE Admin_Service SHALL 提供沙盒试运行环境，允许 Admin_User 在正式上线前使用历史真实对话记录对当前机器人配置（Persona、知识库、Prompt）进行回归测试，验证 AI 回答质量后再发布至生产环境。

---

### 需求 9：数据看板与监控（Admin）

**用户故事：** 作为运营人员，我希望能够查看平台的关键指标，以便评估 AI 客服效果并优化配置。

#### 验收标准

1. THE Admin_Service SHALL 提供以下指标的查询接口：总对话数、AI 自助解决率、转人工率、平均 TTFT、Token 消耗量（按租户、按时间段）。
2. THE System SHALL 记录每次 LLM 调用的 TTFT 和总响应时间，精度为毫秒。
3. WHEN 某租户的 TTFT P95 超过对应场景上限的 2 倍时，THE System SHALL 触发告警并写入监控日志。
4. THE Admin_Service SHALL 支持按时间范围（最近 1 天、7 天、30 天）聚合统计数据。
5. THE System SHALL 对 Admin_Service 的大表查询使用独立的 PostgreSQL 只读从库，避免影响 C 端对话链路性能。
6. THE Admin_Service SHALL 提供"高频未命中问题聚类"报表，将 RAG 相似度低于阈值（未命中）或触发转人工的问题按语义聚类展示，帮助运营人员识别知识库缺口，驱动"发现问题 → 补充文档 → 提高自助率"的业务飞轮。
7. THE System SHALL 对多模态消耗（语音转写按时长、图片解析按分辨率档位）折算为统一的计费单位（Credits），并在租户账单中分项展示文本 Token 消耗与多模态 Credits 消耗。计费 Token 的计算范围明确为：LLM 输入 Token（含系统提示词 + 对话历史 + RAG 检索后实际传入 LLM 的切片）+ LLM 输出 Token；RAG 检索出但未传入 LLM 的切片不计入计费。

---

### 需求 10：多地区部署与高可用

**用户故事：** 作为平台运营方，我希望系统能够在单国多地区部署，以实现就近接入和区域容灾。

#### 验收标准

1. THE System SHALL 通过 GSLB 根据用户 IP 归属地将流量路由至最近的边缘计算节点。
2. THE System SHALL 在每个边缘区域部署独立的 Redis 集群，区域间不进行 Redis 数据同步。
3. THE System SHALL 在中心区域部署 PostgreSQL 主库，各边缘区域部署只读从库，主从同步延迟 SHALL 低于 500ms（P99）。
4. THE System SHALL 在中心区域部署 Milvus 主库，通过 Kafka 将向量变更事件分发至各边缘区域的 Milvus 从节点，同步延迟 SHALL 低于 10 秒。
5. THE Admin_Service SHALL 支持租户配置"紧急知识生效模式"：启用后，RAG_Engine 的向量检索 SHALL 强制读取中心 Milvus 主库，绕过边缘从节点，确保新上传文档立即生效，适用于紧急公告、政策变更等场景。
6. THE System SHALL 满足以下数据备份与恢复要求：PostgreSQL 执行每日全量备份并开启 WAL 归档，Milvus 向量数据定期导出至 OSS 冷备；RPO（恢复点目标）SHALL 低于 15 分钟，RTO（恢复时间目标）SHALL 低于 4 小时；THE System SHALL 每年至少执行一次跨区域灾难恢复演练并记录结果。
5. IF 某边缘区域发生故障，THEN THE GSLB SHALL 在 30 秒内将该区域流量切换至其他可用区域。
6. THE Chat_Service SHALL 是无状态服务，支持通过 Kubernetes HPA 根据 CPU/内存使用率自动水平扩缩容。
7. WHEN 本地 LLM 推理集群负载超过阈值时，THE AI_Gateway SHALL 自动将推理请求路由至其他区域的算力集群或云端 API 兜底。

---

### 需求 11：限流与防滥用

**用户故事：** 作为平台运营方，我希望系统能够防止单个用户或租户的异常流量冲击，以保障整体服务稳定性。

#### 验收标准

1. THE Gateway SHALL 基于 `tenant_id` 实施租户级别的请求频率限制，默认上限为每秒 100 次请求。
2. THE Gateway SHALL 基于 `user_id` 实施用户级别的请求频率限制，默认上限为每秒 10 次请求。
3. IF 请求超过频率限制，THEN THE Gateway SHALL 返回 HTTP 429 状态码，并在响应头中包含 `Retry-After` 字段。
4. THE Gateway SHALL 在本地内存（Token Bucket）先做粗筛限流，仅将通过粗筛的请求打到 Redis 做精准滑动窗口限流，以避免百万日活下 Redis 热点 Key 导致的 CPU 飙升。限流计数器的 Key 格式为 `cuckoo:ratelimit:{tenant_id}:{user_id}`。
5. WHERE 租户配置了自定义限流阈值，THE Gateway SHALL 使用租户专属阈值覆盖默认值。

---

### 需求 12：大模型兼容性（OpenAI Compatible API）

**用户故事：** 作为平台运营方，我希望系统能够灵活接入不同的大模型，以便在成本和性能之间灵活切换。

#### 验收标准

1. THE System SHALL 通过 OpenAI Compatible API（`/v1/chat/completions`）接入所有 LLM，支持 DeepSeek、Qwen、Llama 等模型。
2. THE AI_Gateway SHALL 支持配置多个 LLM 后端，并根据优先级、负载和可用性进行路由。
3. IF 主 LLM 后端不可用，THEN THE AI_Gateway SHALL 在 3 秒内自动 Fallback 至备用 LLM 后端。
4. THE System SHALL 支持流式（`stream=true`）和非流式两种调用模式，并将流式 Token 透传至 SSE 接口。
5. THE Embedding_Service SHALL 同样通过 OpenAI Compatible Embedding API 接入，支持替换不同的 Embedding 模型。
6. THE AI_Gateway 和 Gateway SHALL 对下游依赖服务（LLM、Tool_Service、ASR_Service）实施熔断（Circuit Breaker）策略：当某服务的错误率在滑动窗口内超过阈值（默认 50%）时，THE Gateway SHALL 立即熔断该服务，直接向用户返回降级响应（如"系统繁忙，请稍后重试"），防止级联雪崩；熔断后每隔 30 秒进行一次半开探测，成功则恢复。


---

## 正确性属性（用于 Property-Based Testing）

以下属性描述了系统在任意合法输入下必须满足的不变量，可用于 Property-Based Testing（如 Hypothesis、fast-check）。

### P1：多租户数据隔离不变量

**对应需求：** 需求 1

**属性描述：**
对于任意两个不同的租户 `tenant_a` 和 `tenant_b`，以及任意合法的数据库查询操作 `query`：

```
∀ tenant_a ≠ tenant_b, ∀ query:
  execute_with_context(tenant_a, query).results 中不包含任何 tenant_id = tenant_b 的行
```

**测试策略：**
- 生成随机的两个租户 ID 和随机数量的数据行（分属不同租户）
- 以 `tenant_a` 的上下文执行全表查询
- 断言结果集中所有行的 `tenant_id` 均等于 `tenant_a`
- 对 `users`、`threads`、`messages` 三张表分别验证

---

### P2：Embedding 幂等性

**对应需求：** 需求 3（验收标准 6）

**属性描述：**
对于任意合法的文本输入 `text`，Embedding_Service 的输出向量是确定性的：

```
∀ text ∈ ValidText:
  embed(text) = embed(embed_to_text_back(embed(text)))
  即：embed(text)[i] = embed(text)[i]  （多次调用结果相同）
```

**测试策略：**
- 生成随机长度（1~2000 字符）的文本字符串
- 对同一文本调用 Embedding_Service 两次
- 断言两次返回的向量在每个维度上完全相等（或误差 < 1e-6）

---

### P3：知识库往返一致性（Round-Trip）

**对应需求：** 需求 3（验收标准 8）

**属性描述：**
对于任意有效的知识文档 `doc`，经过完整的处理流程后，文档的核心语义可被检索命中：

```
∀ doc ∈ ValidDocument:
  let chunks = parse_and_chunk(doc)
  let vectors = [embed(chunk) for chunk in chunks]
  let stored = store_to_milvus(vectors, tenant_id)
  let query_vec = embed(extract_key_sentence(doc))
  let results = search_milvus(query_vec, tenant_id, top_k=5)
  ∃ result ∈ results: similarity(result, query_vec) ≥ 0.7
```

**测试策略：**
- 生成包含明确主题句的随机文档（FAQ 格式）
- 执行完整的 Knowledge_Pipeline 流程
- 用文档中的主题句作为查询，验证检索结果中包含相关切片

---

### P4：对话状态保存与恢复（Round-Trip）

**对应需求：** 需求 6

**属性描述：**
对于任意合法的对话状态 `state`，保存后恢复的状态与原始状态等价：

```
∀ state ∈ ValidAgentState:
  restore(save(state)) ≡ state
```

**测试策略：**
- 生成随机长度（1~50 轮）的对话历史作为 Agent State
- 将 State 通过 Checkpointer 保存至 Redis
- 从 Redis 恢复 State
- 断言恢复后的 `messages` 列表、`user_intent`、`tool_calls` 与原始值完全一致

---

### P5：限流滑动窗口不变量

**对应需求：** 需求 11

**属性描述：**
对于任意租户 `t` 和用户 `u`，在时间窗口 `W` 内，超过阈值 `N` 的请求必然被拒绝：

```
∀ t, u, ∀ request_sequence of length > N within window W:
  count(responses where status = 429) = length(request_sequence) - N
```

**测试策略：**
- 生成随机的请求序列（数量在阈值 N 的 1~3 倍之间）
- 在时间窗口内快速发送所有请求
- 断言前 N 个请求返回 200，后续请求返回 429
- 验证窗口重置后，新的 N 个请求可以正常通过

---

### P6：多租户向量检索隔离不变量

**对应需求：** 需求 1（验收标准 5）、需求 3

**属性描述：**
对于任意两个租户 `tenant_a` 和 `tenant_b`，向量检索结果不会跨租户泄露：

```
∀ tenant_a ≠ tenant_b, ∀ query_vector:
  search_milvus(query_vector, partition_key=tenant_a).results 中
  不包含任何属于 tenant_b 的向量
```

**测试策略：**
- 为两个不同租户分别写入语义相似的知识向量
- 以 `tenant_a` 的 PartitionKey 执行检索
- 断言所有返回结果的 `tenant_id` 字段均等于 `tenant_a`

---

### P7：工具调用 tenant_id 透传不变量

**对应需求：** 需求 4（验收标准 3）

**属性描述：**
对于任意工具调用，Tool_Executor 发出的每一次外部请求都必须携带正确的 `tenant_id`：

```
∀ tool_call triggered by tenant_t:
  tool_call.request.tenant_id = tenant_t
```

**测试策略：**
- 使用 mock 工具拦截所有工具调用请求
- 生成随机 `tenant_id` 并触发工具调用
- 断言每次 mock 工具收到的请求中 `tenant_id` 与触发时的值完全一致


---

### P8：Agent 路由确定性（Routing Determinism）

**对应需求：** 需求 4（验收标准 1）

**属性描述：**
对于任意包含明确业务操作意图的消息，Router 必须将其路由至 Tool_Executor，而非 RAG_Engine 或其他节点：

```
∀ msg where has_clear_tool_intent(msg):
  route(msg) == Tool_Executor

∀ msg where has_clear_knowledge_intent(msg):
  route(msg) == RAG_Engine
```

**测试策略：**
- 构造一批具有明确意图标签的测试消息（如"查询订单 12345"→ Tool，"退货政策是什么"→ RAG）
- 生成随机的措辞变体（同义改写）
- 断言 Router 对同一语义意图的路由结果保持一致，不因措辞变化而产生错误路由

---

### P9：高并发状态安全（Concurrency Safety）

**对应需求：** 需求 6

**属性描述：**
同一个 Thread 在收到并发请求时，LangGraph 的 Graph State 不能发生脏写（Race Condition），消息数量必须精确等于原始数量加上并发写入数量：

```
∀ Thread T with initial message count M,
∀ concurrent requests [R1, R2, ..., Rn] to Thread T:
  final_message_count(T) == M + n
  且 T 的状态图不因写冲突而崩溃或产生重复消息
```

**测试策略：**
- 对同一 Thread ID 并发发送 N 条消息（N 取 2~10 的随机值）
- 等待所有请求完成后，从 Redis Checkpointer 读取最终状态
- 断言 `messages` 列表长度精确等于 M + N
- 断言不存在重复的 message ID（无幂等性破坏）
- 实现上首选服务端 per-thread 请求队列化（保证串行处理），次选 Redis 乐观锁（WATCH/MULTI/EXEC）或 Redlock 保证写入原子性
