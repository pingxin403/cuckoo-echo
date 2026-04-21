"""Unit tests for shared/translation.py"""

from shared.translation import (
    detect_language,
    get_language_name,
    LANGUAGE_CODES,
)


class TestDetectLanguage:
    def test_empty_text(self):
        assert detect_language("") == "en"

    def test_chinese_text(self):
        assert detect_language("你好世界") == "zh"

    def test_japanese_text(self):
        assert detect_language("こんにちは世界") == "ja"

    def test_korean_text(self):
        assert detect_language("안녕하세요") == "ko"

    def test_arabic_text(self):
        assert detect_language("مرحبا بالعالم") == "ar"

    def test_english_text(self):
        assert detect_language("Hello world") == "en"

    def test_short_text(self):
        assert detect_language("Hi") == "en"


class TestGetLanguageName:
    def test_english(self):
        assert get_language_name("en") == "English"

    def test_chinese(self):
        assert get_language_name("zh") == "Chinese"

    def test_japanese(self):
        assert get_language_name("ja") == "Japanese"

    def test_korean(self):
        assert get_language_name("ko") == "Korean"

    def test_unknown(self):
        assert get_language_name("xx") == "xx"


class TestLanguageCodes:
    def test_all_codes(self):
        assert "en" in LANGUAGE_CODES
        assert "zh" in LANGUAGE_CODES
        assert "ja" in LANGUAGE_CODES
        assert len(LANGUAGE_CODES) >= 10