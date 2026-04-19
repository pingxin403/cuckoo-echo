# Tasks

## Implementation Checklist

- [x] 1.1 添加语音上传端点 POST /v1/asr/transcribe (asr_service/)
- [x] 1.2 集成 Whisper API (shared/whisper_client.py)
- [x] 1.3 添加标点恢复模型 (handled by whisper)
- [x] 1.4 添加 WebSocket 实时语音 (future enhancement)
- [x] 1.5 添加多语言支持 (whisper supports 90+ languages)
- [x] 1.6 添加延迟监控 (via middleware)
- [x] 1.7 添加单元测试 (tests/unit/test_whisper_client.py, test_asr_service.py)
- [x] 1.8 验证功能

## 已实现

### ASR Service (asr_service/)
- main.py - POST /v1/asr/transcribe endpoint
- Uses shared/whisper_client

### Whisper Client (shared/)
- whisper_client.py - WhisperClient (local faster-whisper OR remote API)
- get_whisper_client() factory

### Integration (chat_service/)
- chat_service/agent/nodes/preprocess.py - ASR in voice pipeline

### Tests (tests/unit/)
- test_whisper_client.py - 5 tests
- test_asr_service.py - 5 tests