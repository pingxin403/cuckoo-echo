"""Document parser — Docling-based unified parsing for PDF/Word/HTML/TXT."""
from __future__ import annotations

from pathlib import Path

import structlog

log = structlog.get_logger()


class ParseError(Exception):
    """Raised when document parsing fails."""


async def parse_document(file_path: str) -> str:
    """Parse a document file and return its text content as Markdown.

    Uses Docling DocumentConverter for PDF/Word/HTML.
    Falls back to plain text reading for .txt files.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return _parse_text(path)

    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(path))
        markdown = result.document.export_to_markdown()
        if not markdown or not markdown.strip():
            raise ParseError(f"Docling returned empty content for {file_path}")
        log.info("document_parsed", path=file_path, format=suffix)
        return markdown
    except ImportError:
        log.warning("docling_not_available", msg="falling back to text extraction")
        return _parse_text(path)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"Failed to parse {file_path}: {e}") from e


def _parse_text(path: Path) -> str:
    """Simple text file reader."""
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise ParseError(f"Empty file: {path}")
        return text
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
        if not text.strip():
            raise ParseError(f"Empty file: {path}")
        return text
