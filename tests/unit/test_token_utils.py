"""Tests for token estimation utilities"""

import pytest
from src.utils.token_utils import estimate_tokens, _heuristic_estimate


class TestEstimateTokens:
    """Test estimate_tokens function"""

    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_none_like(self):
        assert estimate_tokens("") == 0

    def test_english_text(self):
        tokens = estimate_tokens("Hello, how are you today?")
        assert tokens > 0
        assert tokens < 20  # Should be around 6-7 tokens

    def test_chinese_text(self):
        tokens = estimate_tokens("你好世界")
        assert tokens > 0  # Should NOT be 0 (the old bug)
        assert tokens >= 2  # At minimum 2 tokens for 4 CJK chars

    def test_mixed_text(self):
        tokens = estimate_tokens("Hello 你好 World 世界")
        assert tokens > 0

    def test_long_english(self):
        text = "The quick brown fox jumps over the lazy dog. " * 100
        tokens = estimate_tokens(text)
        assert tokens > 100

    def test_long_chinese(self):
        text = "这是一段很长的中文文本用于测试。" * 100
        tokens = estimate_tokens(text)
        assert tokens > 100


class TestHeuristicEstimate:
    """Test the CJK-aware heuristic fallback"""

    def test_pure_chinese(self):
        # "你好" = 2 CJK chars x 1.5 = 3 tokens
        result = _heuristic_estimate("你好")
        assert result == 3

    def test_pure_english(self):
        # "Hello World" = 11 chars / 4 ≈ 2 tokens
        result = _heuristic_estimate("Hello World")
        assert result >= 2

    def test_mixed_cjk_ascii(self):
        result = _heuristic_estimate("Hello你好World世界")
        assert result > 0

    def test_whitespace_only(self):
        result = _heuristic_estimate("   ")
        assert result == 0

    def test_japanese(self):
        result = _heuristic_estimate("こんにちは")
        assert result > 0

    def test_korean(self):
        result = _heuristic_estimate("안녕하세요")
        assert result > 0
