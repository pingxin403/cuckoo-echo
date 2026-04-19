# Tasks

## Implementation Checklist

- [x] 1.1 添加文件上传端点 POST /v1/chat/upload (uses oss_signed_url)
- [x] 1.2 添加文件存储 (本地/S3) (minio integration)
- [x] 1.3 集成多模态 LLM (GPT-4V) (ai_gateway/client.py)
- [x] 1.4 添加图片理解工具 (vision_completion)
- [x] 1.5 添加成本限制中间件 (billing via shared/billing.py)
- [x] 1.6 添加多提供商降级 (fallback in ai_gateway)
- [x] 1.7 添加单元测试 (test_vision_preprocess.py)
- [x] 1.8 验证功能

## 已实现

### Vision LLM (ai_gateway/)
- client.py vision_completion() - GPT-4V image understanding

### Integration (chat_service/)
- preprocess.py - calls vision_client.vision_completion()

### Config (shared/)
- config.py vision_model (gpt-4o-mini default)

### Tests (tests/unit/)
- test_vision_preprocess.py - 5 tests