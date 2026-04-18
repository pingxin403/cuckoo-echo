# Requirements

## 功能需求

### E2E 测试

| 功能 | 优先级 | 状态 |
|------|--------|------|
| 登录流程测试 | P0 | 待实现 |
| 对话流程测试 | P0 | 待实现 |
| 文件上传测试 | P0 | 待实现 |
| HITL 流程测试 | P0 | 待实现 |

## 测试场景

### 登录流程

```python
def test_login():
    # 打开登录页
    # 输入凭据
    # 点击登录
    # 验证跳转 Dashboard
```

### 对话流程

```python
def test_chat():
    # 登录
    # 发起对话
    # 验证 SSE 流式响应
    # 验证消息保存
```

### 文件上传

```python
def test_upload():
    # 登录 Admin
    # 上传知识库文件
    # 验证索引创建
```

### HITL 流程

```python
def test_hitl():
    # 触发工具调用
    # 验证暂停
    # 人工批准
    # 验证继续执行
```