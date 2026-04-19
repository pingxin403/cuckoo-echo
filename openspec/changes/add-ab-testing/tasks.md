# Tasks

## Implementation Checklist

- [x] 1.1 创建 experiment_service 目录
- [x] 1.2 添加实验配置 CRUD (chat_service/services/experiment.py)
- [x] 1.3 添加分流中间件 (api_gateway/middleware/experiment.py)
- [x] 1.4 添加指标收集 (experiment.py track_metric)
- [x] 1.5 添加统计计算 (experiment.py calculate_significance)
- [x] 1.6 添加 Admin API 路由 (chat_service/routes/experiment.py)
- [x] 1.7 添加单元测试 (tests/unit/test_experiment.py - 10 tests)

## 已实现的功能

### Services
- chat_service/services/experiment.py - Experiment CRUD, traffic splitting, metrics, statistical calculation

### Middleware
- api_gateway/middleware/experiment.py - Traffic splitting middleware

### Routes
- chat_service/routes/experiment.py - /v1/experiments CRUD + /results

### Tests
- tests/unit/test_experiment.py - 10 unit tests

## API Endpoints

- POST /v1/experiments - Create experiment
- GET /v1/experiments - List experiments
- GET /v1/experiments/{id} - Get experiment
- PUT /v1/experiments/{id} - Update experiment
- DELETE /v1/experiments/{id} - Delete experiment
- GET /v1/experiments/{id}/results - Get results