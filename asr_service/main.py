"""ASR Service — Whisper-based speech-to-text."""
from __future__ import annotations

import structlog
from fastapi import FastAPI, Header, HTTPException, UploadFile

log = structlog.get_logger()

SUPPORTED_AUDIO_TYPES = {
    "audio/wav",
    "audio/mp3",
    "audio/mpeg",
    "audio/m4a",
    "audio/x-m4a",
    "audio/mp4",
}

app = FastAPI(title="Cuckoo-Echo ASR Service")

# Prometheus metrics
try:
    from shared.metrics import setup_prometheus
    setup_prometheus(app, service_name="asr-service")
except ImportError:
    pass

# Clients — wired at app startup, not at import time
whisper_client = None
oss_client = None


class WhisperError(Exception):
    pass


@app.post("/v1/asr/transcribe")
async def transcribe(
    file: UploadFile,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
):
    if file.content_type not in SUPPORTED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported audio format")

    # Upload to OSS
    oss_path = f"{x_tenant_id}/audio/{file.filename}"
    if oss_client:
        oss_path = await oss_client.upload(file, prefix=f"{x_tenant_id}/audio/")

    # Transcribe
    try:
        if whisper_client:
            result = await whisper_client.transcribe(oss_path)
            text = result.get("text", "") if isinstance(result, dict) else str(result)
        else:
            text = "[ASR stub: whisper not configured]"
        return {"text": text, "oss_path": oss_path}
    except Exception as e:
        log.error("asr_failed", error=str(e), tenant_id=x_tenant_id)
        raise HTTPException(status_code=500, detail="ASR_FAILED")
