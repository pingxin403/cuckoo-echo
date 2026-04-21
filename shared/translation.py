"""Translation service for multilingual conversations."""

from __future__ import annotations

import structlog
from typing import Optional

log = structlog.get_logger()

LANGUAGE_CODES = {
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ru": "Russian",
    "ar": "Arabic",
    "pt": "Portuguese",
    "it": "Italian",
}

DEFAULT_TARGET_LANGUAGE = "en"


def detect_language(text: str) -> str:
    """Detect language from text using simple heuristics.
    
    For production, use langdetect or langid library.
    """
    if not text:
        return "en"
    
    text = text.strip()
    
    if any(ord(c) > 0x4E00 and ord(c) < 0x9FFF for c in text[:100] if c):
        return "zh"
    
    if any(ord(c) > 0x3040 and ord(c) < 0x30FF for c in text[:100] if c):
        return "ja"
    
    if any(ord(c) > 0xAC00 and ord(c) < 0xD7AF for c in text[:100] if c):
        return "ko"
    
    if any(ord(c) > 0x0600 and ord(c) < 0x06FF for c in text[:100] if c):
        return "ar"
    
    return "en"


async def translate(
    text: str,
    source_lang: Optional[str] = None,
    target_lang: str = "en",
) -> str:
    """Translate text from source to target language.
    
    In production, call LibreTranslate or Google Translate API.
    For MVP, just return text with language detection response.
    """
    if not text:
        return text
    
    if source_lang is None:
        source_lang = detect_language(text)
    
    if source_lang == target_lang:
        return text
    
    log.info(
        "translate_request",
        source=source_lang,
        target=target_lang,
        length=len(text),
    )
    
    return text


def get_language_name(code: str) -> str:
    """Get language name from code."""
    return LANGUAGE_CODES.get(code, code)