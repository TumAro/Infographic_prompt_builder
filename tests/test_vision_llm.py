"""Tests for vision_llm.py — mocks litellm.completion to avoid real LLM calls."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import vision_llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(content: str):
    """Build a fake litellm response object."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


SAMPLE_IMAGE = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
SAMPLE_EXT = "png"
SAMPLE_TOPIC = "Introduction to Intelligence"
SAMPLE_SUBTOPIC = "Human vs Machine"
SAMPLE_CAPTION = "Figure 1 comparison chart"


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------

class TestDescribeImageSuccess:
    def test_returns_model_content(self, monkeypatch):
        monkeypatch.setattr(
            vision_llm.litellm, "completion",
            lambda **kw: _make_response("A diagram showing two sides."),
        )
        result = vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, SAMPLE_CAPTION, SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )
        assert result == "A diagram showing two sides."

    def test_strips_thinking_tags(self, monkeypatch):
        monkeypatch.setattr(
            vision_llm.litellm, "completion",
            lambda **kw: _make_response("<think>internal</think>Clean description."),
        )
        result = vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, None, SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )
        assert result == "Clean description."
        assert "<think>" not in result

    def test_returns_on_first_attempt(self, monkeypatch):
        call_count = {"n": 0}

        def fake_completion(**kw):
            call_count["n"] += 1
            return _make_response("First attempt.")

        monkeypatch.setattr(vision_llm.litellm, "completion", fake_completion)
        vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, SAMPLE_CAPTION, SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )
        assert call_count["n"] == 1


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

class TestRetryLogic:
    def test_retries_on_exception_and_succeeds(self, monkeypatch):
        """Fails 4 times, succeeds on 5th attempt."""
        attempts = {"n": 0}

        def fake_completion(**kw):
            attempts["n"] += 1
            if attempts["n"] < 5:
                raise RuntimeError("temporary LLM error")
            return _make_response("Success on attempt 5.")

        monkeypatch.setattr(vision_llm.litellm, "completion", fake_completion)
        result = vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, SAMPLE_CAPTION, SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )
        assert result == "Success on attempt 5."
        assert attempts["n"] == 5

    def test_exactly_5_attempts_made(self, monkeypatch):
        attempts = {"n": 0}

        def fake_completion(**kw):
            attempts["n"] += 1
            raise RuntimeError("always fails")

        monkeypatch.setattr(vision_llm.litellm, "completion", fake_completion)
        vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, SAMPLE_CAPTION, SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )
        assert attempts["n"] == 5


# ---------------------------------------------------------------------------
# Fallback strings after 5 failures
# ---------------------------------------------------------------------------

class TestFallbackStrings:
    @pytest.fixture(autouse=True)
    def always_fail(self, monkeypatch):
        monkeypatch.setattr(
            vision_llm.litellm, "completion",
            lambda **kw: (_ for _ in ()).throw(RuntimeError("fail")),
        )

    def test_fallback_with_caption(self):
        result = vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, "My Caption", SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )
        assert result == "[IMAGE DESCRIPTION FAILED: My Caption]"

    def test_fallback_without_caption(self):
        result = vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, None, SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )
        assert result == "[IMAGE DESCRIPTION FAILED: no caption]"

    def test_fallback_with_empty_string_caption_treated_as_caption(self):
        # Empty string is falsy in Python; treated the same as None
        result = vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, "", SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )
        # Empty string is falsy → should hit the "no caption" path
        assert "no caption" in result or result == "[IMAGE DESCRIPTION FAILED: ]"


# ---------------------------------------------------------------------------
# Message format sent to litellm
# ---------------------------------------------------------------------------

class TestMessageFormat:
    def test_image_url_is_base64_data_uri(self, monkeypatch):
        import base64

        captured = {}

        def fake_completion(**kw):
            captured.update(kw)
            return _make_response("ok")

        monkeypatch.setattr(vision_llm.litellm, "completion", fake_completion)
        vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, None, SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )

        messages = captured["messages"]
        user_msg = next(m for m in messages if m["role"] == "user")
        content = user_msg["content"]
        image_part = next(c for c in content if c["type"] == "image_url")
        url = image_part["image_url"]["url"]

        expected_b64 = base64.b64encode(SAMPLE_IMAGE).decode("ascii")
        assert url == f"data:image/png;base64,{expected_b64}"

    def test_user_message_includes_caption(self, monkeypatch):
        captured = {}

        def fake_completion(**kw):
            captured.update(kw)
            return _make_response("ok")

        monkeypatch.setattr(vision_llm.litellm, "completion", fake_completion)
        vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, SAMPLE_CAPTION, SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )

        messages = captured["messages"]
        user_msg = next(m for m in messages if m["role"] == "user")
        text_part = next(c for c in user_msg["content"] if c["type"] == "text")
        assert f"Caption: {SAMPLE_CAPTION}" in text_part["text"]

    def test_user_message_no_caption(self, monkeypatch):
        captured = {}

        def fake_completion(**kw):
            captured.update(kw)
            return _make_response("ok")

        monkeypatch.setattr(vision_llm.litellm, "completion", fake_completion)
        vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, None, SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )

        messages = captured["messages"]
        user_msg = next(m for m in messages if m["role"] == "user")
        text_part = next(c for c in user_msg["content"] if c["type"] == "text")
        assert "No caption available" in text_part["text"]

    def test_user_message_includes_topic_and_subtopic(self, monkeypatch):
        captured = {}

        def fake_completion(**kw):
            captured.update(kw)
            return _make_response("ok")

        monkeypatch.setattr(vision_llm.litellm, "completion", fake_completion)
        vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, None, SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )

        messages = captured["messages"]
        user_msg = next(m for m in messages if m["role"] == "user")
        text_part = next(c for c in user_msg["content"] if c["type"] == "text")
        assert SAMPLE_TOPIC in text_part["text"]
        assert SAMPLE_SUBTOPIC in text_part["text"]

    def test_system_prompt_is_loaded(self, monkeypatch):
        captured = {}

        def fake_completion(**kw):
            captured.update(kw)
            return _make_response("ok")

        monkeypatch.setattr(vision_llm.litellm, "completion", fake_completion)
        vision_llm.describe_image(
            SAMPLE_IMAGE, SAMPLE_EXT, None, SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )

        messages = captured["messages"]
        system_msg = next((m for m in messages if m["role"] == "system"), None)
        assert system_msg is not None
        # The system prompt should contain some educational framing
        assert len(system_msg["content"]) > 20

    def test_jpg_extension_normalised_to_jpeg(self, monkeypatch):
        captured = {}

        def fake_completion(**kw):
            captured.update(kw)
            return _make_response("ok")

        monkeypatch.setattr(vision_llm.litellm, "completion", fake_completion)
        vision_llm.describe_image(
            SAMPLE_IMAGE, "jpg", None, SAMPLE_TOPIC, SAMPLE_SUBTOPIC
        )

        messages = captured["messages"]
        user_msg = next(m for m in messages if m["role"] == "user")
        image_part = next(c for c in user_msg["content"] if c["type"] == "image_url")
        assert "data:image/jpeg;base64," in image_part["image_url"]["url"]
