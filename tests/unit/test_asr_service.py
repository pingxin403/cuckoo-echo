"""Unit tests for ASR Service."""
import io

import pytest
from starlette.testclient import TestClient

from asr_service.main import SUPPORTED_AUDIO_TYPES, app


class TestASRTranscribe:
    def test_unsupported_format_returns_415(self):
        client = TestClient(app)
        file = io.BytesIO(b"fake content")
        resp = client.post(
            "/v1/asr/transcribe",
            files={"file": ("test.ogg", file, "audio/ogg")},
            headers={"X-Tenant-ID": "t1"},
        )
        assert resp.status_code == 415

    def test_supported_format_returns_200(self):
        client = TestClient(app)
        file = io.BytesIO(b"fake wav content")
        resp = client.post(
            "/v1/asr/transcribe",
            files={"file": ("test.wav", file, "audio/wav")},
            headers={"X-Tenant-ID": "t1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "text" in data
        assert "oss_path" in data

    def test_oss_path_includes_tenant_prefix(self):
        client = TestClient(app)
        file = io.BytesIO(b"fake mp3")
        resp = client.post(
            "/v1/asr/transcribe",
            files={"file": ("test.mp3", file, "audio/mp3")},
            headers={"X-Tenant-ID": "tenant-abc"},
        )
        assert resp.status_code == 200
        assert "tenant-abc" in resp.json()["oss_path"]

    def test_missing_tenant_header_returns_422(self):
        client = TestClient(app)
        file = io.BytesIO(b"fake")
        resp = client.post(
            "/v1/asr/transcribe",
            files={"file": ("test.wav", file, "audio/wav")},
        )
        assert resp.status_code == 422  # missing required header

    def test_all_supported_audio_types_accepted(self):
        """Each supported MIME type should return 200."""
        client = TestClient(app)
        for mime in SUPPORTED_AUDIO_TYPES:
            file = io.BytesIO(b"audio bytes")
            resp = client.post(
                "/v1/asr/transcribe",
                files={"file": ("test.bin", file, mime)},
                headers={"X-Tenant-ID": "t1"},
            )
            assert resp.status_code == 200, f"Expected 200 for {mime}, got {resp.status_code}"
