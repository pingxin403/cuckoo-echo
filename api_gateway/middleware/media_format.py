"""Media format validation via magic-number inspection.

Reads the first 16 bytes of an uploaded file to determine the actual format,
rather than trusting the ``Content-Type`` header which is trivially spoofable.

Supported formats:
- Image: JPEG, PNG, WEBP
- Audio: WAV, MP3, M4A

Returns a ``(format_name, media_type)`` tuple on success, or raises
``UnsupportedMediaFormat`` (which the caller should translate to HTTP 415).
"""

from __future__ import annotations

import structlog

log = structlog.get_logger()


class UnsupportedMediaFormat(Exception):
    """Raised when the uploaded file's magic bytes don't match any supported format."""


# Magic byte signatures
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89\x50\x4e\x47"
_RIFF_MAGIC = b"\x52\x49\x46\x46"  # RIFF container (WAV or WEBP)
_WEBP_SIGNATURE = b"\x57\x45\x42\x50"  # at offset 8
_WAV_SIGNATURE = b"\x57\x41\x56\x45"  # at offset 8
_MP3_MAGIC_PREFIXES = (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")
_ID3_MAGIC = b"\x49\x44\x33"  # ID3 tag header (MP3)
_FTYP_SIGNATURE = b"\x66\x74\x79\x70"  # at offset 4 (M4A / MP4 container)


def validate_media_format(header: bytes) -> tuple[str, str]:
    """Identify the media format from the first 16 bytes of a file.

    Parameters
    ----------
    header:
        The first 16 (or more) bytes of the uploaded file.

    Returns
    -------
    tuple[str, str]
        ``(format_name, media_type)`` e.g. ``("jpeg", "image")``

    Raises
    ------
    UnsupportedMediaFormat
        If the magic bytes don't match any supported format.
    """
    if len(header) < 4:
        raise UnsupportedMediaFormat("File too small to identify format")

    # JPEG: FF D8 FF
    if header[:3] == _JPEG_MAGIC:
        return ("jpeg", "image")

    # PNG: 89 50 4E 47
    if header[:4] == _PNG_MAGIC:
        return ("png", "image")

    # RIFF container: check sub-type at offset 8
    if header[:4] == _RIFF_MAGIC and len(header) >= 12:
        sub_type = header[8:12]
        if sub_type == _WEBP_SIGNATURE:
            return ("webp", "image")
        if sub_type == _WAV_SIGNATURE:
            return ("wav", "audio")

    # MP3: FF FB / FF F3 / FF F2
    if header[:2] in _MP3_MAGIC_PREFIXES:
        return ("mp3", "audio")

    # MP3 with ID3 tag: 49 44 33
    if header[:3] == _ID3_MAGIC:
        return ("mp3", "audio")

    # M4A (ftyp box): offset 4 = 66 74 79 70
    if len(header) >= 8 and header[4:8] == _FTYP_SIGNATURE:
        return ("m4a", "audio")

    raise UnsupportedMediaFormat(
        f"Unrecognized magic bytes: {header[:16].hex()}"
    )
