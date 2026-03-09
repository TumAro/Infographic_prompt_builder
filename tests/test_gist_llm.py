"""Tests for gist_llm.py — all LLM calls are mocked."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from gist_llm import generate_gist, _format_user_message

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TOPIC_CONTENT = {
    "topic": "Introduction to Intelligence",
    "subtopics": [
        {
            "name": "Human Intelligence vs. Machine Intelligence",
            "blocks": [
                {"type": "paragraph", "text": "Intelligence is the ability to learn."},
                {"type": "story",     "text": "Once upon a time in Mindsville..."},
                {"type": "figure_caption", "text": "Figure 1 Components of Emotional Understanding."},
            ],
        },
        {
            "name": "Exploring the Forms of Intelligence",
            "blocks": [
                {"type": "paragraph", "text": "Natural intelligence is found in living beings."},
                {"type": "fun_fact",  "text": "Fun Fact: Ants can carry 50 times their body weight."},
                {
                    "type": "table",
                    "rows": [
                        ["Type", "Example"],
                        ["Natural", "Humans, Animals"],
                        ["Artificial", "Robots, Computers"],
                    ],
                },
            ],
        },
    ],
}

FAKE_GIST = "# Introduction to Intelligence\n\n## Human Intelligence\n\nSummary here.\n\n## Synopsis\n\nKey takeaway."


def _make_mock_response(content: str) -> MagicMock:
    """Build a mock litellm response object."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# generate_gist — skip logic
# ---------------------------------------------------------------------------

def test_skip_if_exists(tmp_path):
    """If gist.md already exists, return it without calling the LLM."""
    gist_path = tmp_path / "gist.md"
    gist_path.write_text("cached content", encoding="utf-8")

    with patch("litellm.completion") as mock_llm:
        result = generate_gist(TOPIC_CONTENT, 6, tmp_path)

    assert result == "cached content"
    mock_llm.assert_not_called()


# ---------------------------------------------------------------------------
# generate_gist — generation path
# ---------------------------------------------------------------------------

def test_generates_and_saves(tmp_path):
    """LLM response is saved to gist.md and returned."""
    with patch("litellm.completion", return_value=_make_mock_response(FAKE_GIST)):
        result = generate_gist(TOPIC_CONTENT, 6, tmp_path)

    assert result == FAKE_GIST.strip()
    assert (tmp_path / "gist.md").read_text(encoding="utf-8") == FAKE_GIST.strip()


def test_creates_output_dir(tmp_path):
    """Output directory (including parents) is created if it does not exist."""
    nested = tmp_path / "output" / "grade_6" / "module_1" / "topic_1"
    assert not nested.exists()

    with patch("litellm.completion", return_value=_make_mock_response(FAKE_GIST)):
        generate_gist(TOPIC_CONTENT, 6, nested)

    assert (nested / "gist.md").exists()


def test_strips_whitespace_from_response(tmp_path):
    """Leading/trailing whitespace in the LLM response is stripped."""
    padded = "  \n\n" + FAKE_GIST + "\n\n  "
    with patch("litellm.completion", return_value=_make_mock_response(padded)):
        result = generate_gist(TOPIC_CONTENT, 6, tmp_path)

    assert result == FAKE_GIST.strip()


# ---------------------------------------------------------------------------
# generate_gist — litellm call parameters
# ---------------------------------------------------------------------------

def test_litellm_called_with_correct_model(tmp_path):
    with patch("litellm.completion", return_value=_make_mock_response(FAKE_GIST)) as mock_llm:
        generate_gist(TOPIC_CONTENT, 6, tmp_path)

    _, kwargs = mock_llm.call_args
    assert kwargs["model"] == "ollama/llama3.1"


def test_litellm_called_with_api_base(tmp_path):
    with patch("litellm.completion", return_value=_make_mock_response(FAKE_GIST)) as mock_llm:
        generate_gist(TOPIC_CONTENT, 6, tmp_path)

    _, kwargs = mock_llm.call_args
    assert kwargs["api_base"] == "http://localhost:11434"


def test_litellm_called_with_system_prompt(tmp_path):
    with patch("litellm.completion", return_value=_make_mock_response(FAKE_GIST)) as mock_llm:
        generate_gist(TOPIC_CONTENT, 6, tmp_path)

    _, kwargs = mock_llm.call_args
    messages = kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert len(messages[0]["content"]) > 100  # system prompt is substantial


def test_litellm_called_with_user_message(tmp_path):
    with patch("litellm.completion", return_value=_make_mock_response(FAKE_GIST)) as mock_llm:
        generate_gist(TOPIC_CONTENT, 6, tmp_path)

    _, kwargs = mock_llm.call_args
    messages = kwargs["messages"]
    assert messages[1]["role"] == "user"
    assert "Introduction to Intelligence" in messages[1]["content"]


def test_litellm_temperature_and_max_tokens(tmp_path):
    with patch("litellm.completion", return_value=_make_mock_response(FAKE_GIST)) as mock_llm:
        generate_gist(TOPIC_CONTENT, 6, tmp_path)

    _, kwargs = mock_llm.call_args
    assert kwargs["temperature"] == 0.3
    assert kwargs["max_tokens"] == 2048


# ---------------------------------------------------------------------------
# _format_user_message
# ---------------------------------------------------------------------------

def test_format_grade_header():
    msg = _format_user_message(TOPIC_CONTENT, 6)
    assert msg.startswith("Grade: 6")


def test_format_topic_header():
    msg = _format_user_message(TOPIC_CONTENT, 6)
    assert "# Introduction to Intelligence" in msg


def test_format_subtopic_headers():
    msg = _format_user_message(TOPIC_CONTENT, 6)
    assert "## Human Intelligence vs. Machine Intelligence" in msg
    assert "## Exploring the Forms of Intelligence" in msg


def test_format_paragraph_block():
    msg = _format_user_message(TOPIC_CONTENT, 6)
    assert "[paragraph] Intelligence is the ability to learn." in msg


def test_format_story_block():
    msg = _format_user_message(TOPIC_CONTENT, 6)
    assert "[story] Once upon a time in Mindsville..." in msg


def test_format_figure_caption_block():
    msg = _format_user_message(TOPIC_CONTENT, 6)
    assert "[figure_caption] Figure 1 Components of Emotional Understanding." in msg


def test_format_fun_fact_block():
    msg = _format_user_message(TOPIC_CONTENT, 6)
    assert "[fun_fact] Fun Fact: Ants can carry 50 times their body weight." in msg


def test_format_table_block():
    msg = _format_user_message(TOPIC_CONTENT, 6)
    assert "[table]" in msg
    assert "Type | Example" in msg
    assert "Natural | Humans, Animals" in msg


def test_format_all_blocks_present():
    """Every block from every subtopic appears somewhere in the message."""
    msg = _format_user_message(TOPIC_CONTENT, 6)
    assert "Intelligence is the ability to learn." in msg
    assert "Once upon a time in Mindsville..." in msg
    assert "Natural intelligence is found in living beings." in msg
    assert "Artificial | Robots, Computers" in msg
