"""Property 5: Unsupported media format rejected.

# Feature: cuckoo-echo, Property 5: 不支持媒体格式返回 415
**Validates: Requirements 2.5**
"""

import pytest
from hypothesis import given, settings, HealthCheck, strategies as st

from api_gateway.middleware.media_format import validate_media_format, UnsupportedMediaFormat

UNSUPPORTED_MIMES = ["video/mp4", "application/pdf", "image/gif", "audio/ogg", "text/plain"]


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(mime=st.sampled_from(UNSUPPORTED_MIMES))
def test_unsupported_media_format_rejected(mime):
    """Fake header bytes that don't match any supported format must raise UnsupportedMediaFormat."""
    # Generate 16 bytes of garbage that don't match any supported magic bytes
    fake_header = b"\x00\x01\x02\x03" * 4  # 16 bytes of garbage
    with pytest.raises(UnsupportedMediaFormat):
        validate_media_format(fake_header)
