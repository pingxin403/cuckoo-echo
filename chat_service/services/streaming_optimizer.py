"""Streaming optimization with backpressure and multi-stream handling."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class StreamingMetrics:
    """Streaming performance metrics."""

    total_chunks: int = 0
    total_tokens: int = 0
    first_token_latency_ms: float = 0.0
    last_token_timestamp: float = 0.0
    error_count: int = 0
    backpressure_events: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_chunks": self.total_chunks,
            "total_tokens": self.total_tokens,
            "first_token_latency_ms": self.first_token_latency_ms,
            "error_count": self.error_count,
            "backpressure_events": self.backpressure_events,
        }


@dataclass
class StreamBuffer:
    """Adaptive buffer for streaming content."""

    content: list[str] = field(default_factory=list)
    capacity: int = 100
    watermark_high: int = 80
    watermark_low: int = 20

    def add(self, chunk: str) -> bool:
        """Add chunk, return False if at capacity."""
        if len(self.content) >= self.capacity:
            return False
        self.content.append(chunk)
        return True

    def get(self) -> str:
        """Get and clear buffer."""
        result = "".join(self.content)
        self.content.clear()
        return result

    def should_backpressure(self) -> bool:
        """Check if backpressure should be applied."""
        return len(self.content) >= self.watermark_high

    def should_resume(self) -> bool:
        """Check if streaming should resume."""
        return len(self.content) <= self.watermark_low


class StreamingOptimizer:
    """Optimize streaming with chunking, backpressure, buffering."""

    def __init__(self, chunk_size: int = 64, enable_compression: bool = False):
        self.chunk_size = chunk_size
        self.enable_compression = enable_compression
        self._buffers: dict[str, StreamBuffer] = {}
        self._client_flow: dict[str, bool] = {}
        self._metrics = StreamingMetrics()
        self._stream_start_times: dict[str, float] = {}
        logger.info("streaming_optimizer_init", chunk_size=chunk_size)

    def optimize_chunk(self, chunk: str) -> list[str]:
        """Split large chunks into optimal sizes."""
        if len(chunk) <= self.chunk_size:
            return [chunk]

        chunks = []
        for i in range(0, len(chunk), self.chunk_size):
            chunks.append(chunk[i : i + self.chunk_size])
        self._metrics.total_chunks += len(chunks)
        return chunks

    def can_enqueue(self, stream_id: str, content: str) -> bool:
        """Check if content can be enqueued."""
        if stream_id not in self._buffers:
            self._buffers[stream_id] = StreamBuffer()
            self._client_flow[stream_id] = True
            self._stream_start_times[stream_id] = time.time()

        buffer = self._buffers[stream_id]

        if not self._client_flow.get(stream_id, True):
            self._metrics.backpressure_events += 1
            logger.warning("backpressure_active", stream_id=stream_id)
            return False

        return buffer.add(content)

    def handle_backpressure(self, stream_id: str, permitted: bool) -> None:
        """Handle client flow control."""
        self._client_flow[stream_id] = permitted
        if permitted:
            logger.info("backpressure_released", stream_id=stream_id)
        else:
            logger.info("backpressure_applied", stream_id=stream_id)

    def flush_buffer(self, stream_id: str) -> str:
        """Flush buffer for stream."""
        if stream_id in self._buffers:
            return self._buffers[stream_id].get()
        return ""

    def record_first_token(self, stream_id: str) -> None:
        """Record time to first token."""
        if stream_id in self._stream_start_times:
            latency = (time.time() - self._stream_start_times[stream_id]) * 1000
            self._metrics.first_token_latency_ms = latency
            logger.info("first_token_latency", stream_id=stream_id, latency_ms=latency)

    def get_metrics(self) -> dict[str, Any]:
        """Get streaming metrics."""
        return self._metrics.to_dict()


class MultiStreamHandler:
    """Handle multiple parallel streams."""

    def __init__(self):
        self._streams: dict[str, StreamingOptimizer] = {}
        self._coordinator: dict[str, list[str]] = {}

    def create_stream(self, stream_id: str, chunk_size: int = 64) -> StreamingOptimizer:
        """Create a new stream handler."""
        optimizer = StreamingOptimizer(chunk_size=chunk_size)
        self._streams[stream_id] = optimizer
        logger.info("stream_created", stream_id=stream_id)
        return optimizer

    def get_stream(self, stream_id: str) -> StreamingOptimizer | None:
        """Get stream by ID."""
        return self._streams.get(stream_id)

    def coordinate_streams(self, stream_ids: list[str]) -> dict[str, str]:
        """Coordinate multiple stream outputs."""
        results = {}
        for stream_id in stream_ids:
            if stream_id in self._streams:
                results[stream_id] = self._streams[stream_id].get_metrics()
        return results

    async def cancel_stream(self, stream_id: str) -> None:
        """Cancel a stream."""
        if stream_id in self._streams:
            self._streams[stream_id]._buffers.clear()
            logger.info("stream_cancelled", stream_id=stream_id)

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """Get metrics for all streams."""
        return {sid: opt.get_metrics() for sid, opt in self._streams.items()}


multi_stream_handler = MultiStreamHandler()