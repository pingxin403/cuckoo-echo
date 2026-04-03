"""MinIO/OSS client wrapper."""
from __future__ import annotations

import structlog

from shared.config import get_settings

log = structlog.get_logger()


class OSSClient:
    def __init__(self):
        settings = get_settings()
        self.endpoint = settings.minio_endpoint
        self.access_key = settings.minio_access_key
        self.secret_key = settings.minio_secret_key
        self.bucket = settings.minio_bucket
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from minio import Minio

                self._client = Minio(
                    self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=False,  # Local dev; True for production
                )
                # Ensure bucket exists
                if not self._client.bucket_exists(self.bucket):
                    self._client.make_bucket(self.bucket)
            except ImportError:
                log.warning("minio_not_installed")
        return self._client

    async def upload(self, file, prefix: str = "") -> str:
        """Upload file to OSS, return the object path."""
        from io import BytesIO

        client = self._get_client()
        if not client:
            return f"{prefix}{getattr(file, 'filename', 'unknown')}"

        content = await file.read() if hasattr(file, "read") else file
        object_name = f"{prefix}{getattr(file, 'filename', 'file')}"
        client.put_object(self.bucket, object_name, BytesIO(content), len(content))
        log.info("oss_uploaded", path=object_name)
        return object_name

    async def get_signed_url(self, object_name: str, expires_hours: int = 1) -> str:
        """Get a pre-signed URL for the object."""
        from datetime import timedelta

        client = self._get_client()
        if not client:
            return f"http://{self.endpoint}/{self.bucket}/{object_name}"
        return client.presigned_get_object(self.bucket, object_name, expires=timedelta(hours=expires_hours))

    async def delete(self, object_name: str) -> None:
        """Delete an object from OSS."""
        client = self._get_client()
        if client:
            client.remove_object(self.bucket, object_name)


def get_oss_client() -> OSSClient:
    """Return a new OSSClient instance."""
    return OSSClient()
