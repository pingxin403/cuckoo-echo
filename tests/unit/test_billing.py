"""Unit tests for shared/billing.py multimodal credit calculations."""


from shared.billing import (
    AUDIO_CREDIT_RATE,
    IMAGE_CREDIT_RATES,
    calculate_audio_credits,
    calculate_image_credits,
)


class TestCalculateAudioCredits:
    def test_zero_seconds(self):
        assert calculate_audio_credits(0.0) == 0.0

    def test_negative_seconds(self):
        assert calculate_audio_credits(-5.0) == 0.0

    def test_exactly_15_seconds(self):
        # 1 chunk * 0.1 = 0.1
        assert calculate_audio_credits(15.0) == AUDIO_CREDIT_RATE

    def test_partial_chunk_rounds_up(self):
        # 1 second -> ceil(1/15) = 1 chunk -> 0.1
        assert calculate_audio_credits(1.0) == AUDIO_CREDIT_RATE

    def test_16_seconds_is_two_chunks(self):
        # ceil(16/15) = 2 chunks -> 0.2
        assert calculate_audio_credits(16.0) == 2 * AUDIO_CREDIT_RATE

    def test_60_seconds(self):
        # ceil(60/15) = 4 chunks -> 0.4
        assert calculate_audio_credits(60.0) == 4 * AUDIO_CREDIT_RATE

    def test_large_audio(self):
        # 300 seconds -> ceil(300/15) = 20 chunks -> 2.0
        assert calculate_audio_credits(300.0) == 20 * AUDIO_CREDIT_RATE


class TestCalculateImageCredits:
    def test_sd_resolution(self):
        assert calculate_image_credits("sd") == 0.5

    def test_hd_resolution(self):
        assert calculate_image_credits("hd") == 1.0

    def test_4k_resolution(self):
        assert calculate_image_credits("4k") == 2.0

    def test_unknown_resolution_defaults_to_sd(self):
        assert calculate_image_credits("unknown") == IMAGE_CREDIT_RATES["sd"]

    def test_default_is_sd(self):
        assert calculate_image_credits() == IMAGE_CREDIT_RATES["sd"]
