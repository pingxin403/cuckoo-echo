# Requirements

## 功能需求

### 集成测试

| 功能 | 优先级 | 状态 |
|------|--------|------|
| Docker Compose 测试 | P0 | 待实现 |
| 数据库迁移测试 | P0 | 待实现 |
| 多租户隔离测试 | P0 | 待实现 |
| 健康检查测试 | P0 | 待实现 |

## 测试场景

### Docker Compose 测试

```bash
docker-compose up -d
docker-compose ps
# 验证所有服务 running
```

### 数据库迁移测试

```python
def test_migration():
    # 运行 alembic upgrade
    # 验证表结构
    # 运行 downgrade 后再 upgrade
```

### 多租户隔离测试

```python
def test_tenant_isolation():
    # 创建 tenant_a 的会话
    # tenant_b 无法访问 tenant_a 的数据
    # 验证 row-level security
```

### 健康检查测试

```python
def test_health():
    # GET /health
    # GET /health/ready
    # 验证返回 200
```