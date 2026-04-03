"""Async Whisper client — supports local inference and remote OpenAI-compatible API."""
from __future__ import annotations

import structlog

from shared.config import get_settings

log = structlog.get_logger()


class WhisperClient:
    """Configurable ASR client supporting local (faster-whisper) and remote modes."""

    def __init__(self, mode: str = "remote", api_url: str = "", model: str = "whisper-1"):
        self.mode = mode  # "local" or "remote"
        self.api_url = api_url
        self.model = model
        self._local_model = None

    async def transcribe(self, audio_path: str) -> dict:
        """Transcribe audio file. Returns {"text": str, "language": str}."""
        if self.mode == "local":
            return await self._transcribe_local(audio_path)
        return await self._transcribe_remote(audio_path)

    async def _transcribe_local(self, audio_path: str) -> dict:
        """Local inference using faster-whisper."""
        try:
            if self._local_model is None:
                from faster_whisper import WhisperModel

                self._local_model = WhisperModel(self.model, device="auto")
                log.info("whisper_local_model_loaded", model=self.model)

            import asyncio

            loop = asyncio.get_running_loop()
            segments, info = await loop.run_in_executor(
                None, lambda: self._local_model.transcribe(audio_path)
            )
            text = " ".join(seg.text for seg in segments)
            return {"text": text.strip(), "language": info.language}
        except ImportError:
            log.error("faster_whisper_not_installed")
            raise RuntimeError("faster-whisper not installed. Install with: uv add faster-whisper")
        except Exception as e:
            log.error("whisper_local_failed", error=str(e))
            raise

    async def _transcribe_remote(self, audio_path: str) -> dict:
        """Remote inference via OpenAI-compatible /v1/audio/transcriptions API."""
        try:
            import httpx

            url = f"{self.api_url}/v1/audio/transcriptions"
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(audio_path, "rb") as f:
                    resp = await client.post(
                        url,
                        files={"file": (audio_path, f, "audio/wav")},
                        data={"model": self.model},
                    )
                resp.raise_for_status()
                data = resp.json()
                return {"text": data.get("text", ""), "language": data.get("language", "")}
        except Exception as e:
            log.error("whisper_remote_failed", error=str(e), url=self.api_url)
            raise


def get_whisper_client() -> WhisperClient:
    """Create a WhisperClient from Settings."""
    settings = get_settings()
    mode = getattr(settings, "asr_mode", "remote")
    api_url = getattr(settings, "asr_api_url", "http://localhost:9000")
    model = getattr(settings, "asr_model", "whisper-1")
    return WhisperClient(mode=mode, api_url=api_url, model=model)
