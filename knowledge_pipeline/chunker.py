"""Text chunker — recursive character splitting with CJK-aware separators."""
from __future__ import annotations

import structlog

log = structlog.get_logger()

DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64
SEPARATORS = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]


def split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split text into chunks using recursive character splitting.

    Returns at least one non-empty chunk for any valid input.
    """
    if not text or not text.strip():
        return []

    chunks = _recursive_split(text.strip(), SEPARATORS, chunk_size, chunk_overlap)
    # Ensure at least one chunk
    if not chunks:
        chunks = [text.strip()[:chunk_size]]
    # Filter empty chunks
    chunks = [c.strip() for c in chunks if c.strip()]
    return chunks if chunks else [text.strip()[:chunk_size]]


def _recursive_split(
    text: str,
    separators: list[str],
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """Recursively split text by separators, respecting chunk_size."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    # Try each separator
    for sep in separators:
        if sep == "":
            # Character-level split as last resort
            return _fixed_size_split(text, chunk_size, chunk_overlap)
        if sep in text:
            parts = text.split(sep)
            chunks: list[str] = []
            current = ""
            for part in parts:
                candidate = current + sep + part if current else part
                if len(candidate) <= chunk_size:
                    current = candidate
                else:
                    if current:
                        chunks.append(current)
                    if len(part) > chunk_size:
                        # Recurse with remaining separators
                        idx = separators.index(sep)
                        chunks.extend(
                            _recursive_split(
                                part, separators[idx + 1 :], chunk_size, chunk_overlap
                            )
                        )
                    else:
                        current = part
            if current:
                chunks.append(current)
            return chunks

    return _fixed_size_split(text, chunk_size, chunk_overlap)


def _fixed_size_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Fixed-size character split with overlap."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start >= len(text):
            break
    return [c for c in chunks if c.strip()]
