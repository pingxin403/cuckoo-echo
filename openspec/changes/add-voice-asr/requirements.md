# Requirements

## 功能需求

### Voice ASR

| 功能 | 优先级 | 状态 |
|------|--------|------|
| 语音上传端点 | P0 | 待实现 |
| Whisper 集成 | P0 | 待实现 |
| WebSocket 流式 | P1 | 待实现 |
| 标点恢复 | P1 | 待实现 |
| 多语言支持 | P1 | 待实现 |

## API 设计

### POST /v1/voice/transcribe

```bash
curl -X POST http://localhost:8000/v1/voice/transcribe \
  -H "Authorization: Bearer ck_xxx" \
  -F "file=@audio.m4a" \
  -F "language=zh"
```

Response:
```json
{
  "text": "你好，我想咨询一下产品",
  "duration": 3.5,
  "language": "zh"
}
```

### WebSocket /v1/voice/ws

Client → Server:
```json
{"type": "audio", "data": "base64..."}
```

Server → Client:
```json
{"type": "partial", "text": "你好"}
{"type": "done", "text": "你好，我想咨询一下产品"}
```

## 性能指标

- 延迟目标: < 500ms
- 准确率: > 95%
- 支持格式: mp3, m4a, wav, webm