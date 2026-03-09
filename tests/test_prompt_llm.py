"""Tests for prompt_llm.py — all LLM calls are mocked."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from prompt_llm import generate_content_jsons

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

FAKE_GIST = """\
# Introduction to Intelligence

## Human Intelligence vs. Machine Intelligence

Intelligence is the ability to learn. Humans can adapt across many domains.

Story/Analogy: Think of the brain as a swiss army knife.

---

## Synopsis

Intelligence comes in many forms. Understanding both human and machine intelligence
is the first step to understanding AI.
"""

_STYLE_TOKENS = {
    "illustration_style": "{{global.illustration_style}}",
    "aspect_ratio":        "{{global.aspect_ratio}}",
    "font_style":          "{{global.font_style}}",
    "layout_language":     "{{global.layout_language}}",
    "background_color":    "{{grade.background_color}}",
    "primary_color":       "{{grade.primary_color}}",
    "accent_color":        "{{grade.accent_color}}",
    "mood":                "{{grade.mood}}",
    "complexity_level":    "{{grade.complexity_level}}",
}

_IMAGE_PROMPT = (
    "A {{global.layout_language}} infographic in {{global.illustration_style}} style "
    "with {{grade.mood}} tone at {{global.aspect_ratio}} using {{global.font_style}} "
    "on {{grade.background_color}} background. Primary {{grade.primary_color}}, "
    "accent {{grade.accent_color}}, complexity {{grade.complexity_level}}."
)

FAKE_PAGE_1 = {
    "page": 1,
    "topic": "Introduction to Intelligence",
    "layout_type": "multi_column",
    "title": "What is Intelligence?",
    "subtitle": "Humans and machines think differently",
    "style": _STYLE_TOKENS,
    "sections": [
        {
            "heading": "Human Intelligence",
            "body": "Intelligence is the ability to learn.",
            "visual_hint": "A child reading a book next to a robot.",
        }
    ],
    "image_prompt": _IMAGE_PROMPT,
}

FAKE_PAGE_2 = {
    "page": 2,
    "topic": "Introduction to Intelligence",
    "layout_type": "analogy_anchor",
    "title": "Brain vs Machine",
    "subtitle": "Swiss army knife meets chess computer",
    "style": _STYLE_TOKENS,
    "sections": [
        {
            "heading": "The Analogy",
            "body": "Think of the brain as a swiss army knife.",
            "visual_hint": "A glowing brain shaped like a swiss army knife.",
        }
    ],
    "image_prompt": _IMAGE_PROMPT,
}


def _make_mock_response(content: str) -> MagicMock:
    """Build a mock litellm response object."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _llm_json(*pages) -> str:
    """Serialize one or more page dicts into the LLM multi-page format."""
    return "\n---\n".join(json.dumps(p) for p in pages)


# ---------------------------------------------------------------------------
# Skip logic
# ---------------------------------------------------------------------------

def test_skip_if_page1_exists(tmp_path):
    """page_1_content.json exists → return its content without calling LLM."""
    content = json.dumps(FAKE_PAGE_1, indent=2)
    (tmp_path / "page_1_content.json").write_text(content, encoding="utf-8")

    with patch("litellm.completion") as mock_llm:
        result = generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    mock_llm.assert_not_called()
    assert result == [content]


def test_skip_returns_both_pages(tmp_path):
    """If both page_1 and page_2 exist, both are returned."""
    c1 = json.dumps(FAKE_PAGE_1, indent=2)
    c2 = json.dumps(FAKE_PAGE_2, indent=2)
    (tmp_path / "page_1_content.json").write_text(c1, encoding="utf-8")
    (tmp_path / "page_2_content.json").write_text(c2, encoding="utf-8")

    with patch("litellm.completion") as mock_llm:
        result = generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    mock_llm.assert_not_called()
    assert result == [c1, c2]


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def test_generates_single_page(tmp_path):
    """LLM returns 1 valid JSON → page_1_content.json saved, list of 1 returned."""
    with patch("litellm.completion", return_value=_make_mock_response(_llm_json(FAKE_PAGE_1))):
        result = generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    assert isinstance(result, list)
    assert len(result) == 1
    assert (tmp_path / "page_1_content.json").exists()
    assert not (tmp_path / "page_2_content.json").exists()


def test_generates_two_pages(tmp_path):
    """LLM returns 2 pages separated by --- → both files saved."""
    raw = _llm_json(FAKE_PAGE_1, FAKE_PAGE_2)
    with patch("litellm.completion", return_value=_make_mock_response(raw)):
        result = generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    assert len(result) == 2
    assert (tmp_path / "page_1_content.json").exists()
    assert (tmp_path / "page_2_content.json").exists()


def test_creates_output_dir(tmp_path):
    """Output directory (including parents) is created if it does not exist."""
    nested = tmp_path / "output" / "grade_6" / "module_1" / "topic_1"
    assert not nested.exists()

    with patch("litellm.completion", return_value=_make_mock_response(_llm_json(FAKE_PAGE_1))):
        generate_content_jsons(FAKE_GIST, 6, 1, 1, nested)

    assert (nested / "page_1_content.json").exists()


def test_return_is_list_of_strings(tmp_path):
    """Return value is a list of strings."""
    with patch("litellm.completion", return_value=_make_mock_response(_llm_json(FAKE_PAGE_1))):
        result = generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    assert isinstance(result, list)
    assert all(isinstance(s, str) for s in result)


def test_json_content_matches_page(tmp_path):
    """Saved page_1_content.json round-trips back to FAKE_PAGE_1."""
    with patch("litellm.completion", return_value=_make_mock_response(_llm_json(FAKE_PAGE_1))):
        generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    saved = json.loads((tmp_path / "page_1_content.json").read_text(encoding="utf-8"))
    assert saved == FAKE_PAGE_1


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------

def test_retry_on_json_error(tmp_path):
    """First response is invalid JSON → retried; second response saves the file."""
    responses = [
        _make_mock_response("this is not json at all"),
        _make_mock_response(_llm_json(FAKE_PAGE_1)),
    ]
    with patch("litellm.completion", side_effect=responses) as mock_llm:
        result = generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    assert mock_llm.call_count == 2
    assert len(result) == 1
    assert (tmp_path / "page_1_content.json").exists()


def test_raises_after_two_failures(tmp_path):
    """Both attempts return invalid JSON → JSONDecodeError propagates."""
    responses = [
        _make_mock_response("not json"),
        _make_mock_response("also not json"),
    ]
    with patch("litellm.completion", side_effect=responses):
        with pytest.raises(json.JSONDecodeError):
            generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _page_without(field):
    """Return FAKE_PAGE_1 with one required field removed."""
    p = dict(FAKE_PAGE_1)
    p.pop(field)
    return p


def test_validation_missing_required_field(tmp_path):
    """JSON missing 'image_prompt' raises ValueError."""
    bad = _page_without("image_prompt")
    with patch("litellm.completion", return_value=_make_mock_response(json.dumps(bad))):
        with pytest.raises(ValueError, match="Missing required fields"):
            generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)


def test_validation_bad_style_token(tmp_path):
    """Hardcoded hex in style raises ValueError."""
    bad_style = dict(_STYLE_TOKENS)
    bad_style["background_color"] = "#FF0000"
    bad = {**FAKE_PAGE_1, "style": bad_style}
    with patch("litellm.completion", return_value=_make_mock_response(json.dumps(bad))):
        with pytest.raises(ValueError, match="not a valid token"):
            generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)


def test_validation_missing_section_field(tmp_path):
    """Section missing 'visual_hint' raises ValueError."""
    bad_section = {"heading": "Test Heading", "body": "Some body text."}
    bad = {**FAKE_PAGE_1, "sections": [bad_section]}
    with patch("litellm.completion", return_value=_make_mock_response(json.dumps(bad))):
        with pytest.raises(ValueError, match="visual_hint"):
            generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)


def test_validation_invalid_layout_type(tmp_path):
    """Unknown layout_type raises ValueError."""
    bad = {**FAKE_PAGE_1, "layout_type": "unknown_layout"}
    with patch("litellm.completion", return_value=_make_mock_response(json.dumps(bad))):
        with pytest.raises(ValueError, match="Invalid layout_type"):
            generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)


def test_validation_missing_image_prompt_token(tmp_path):
    """image_prompt missing a token raises ValueError."""
    broken_prompt = _IMAGE_PROMPT.replace("{{grade.mood}}", "energetic")
    bad = {**FAKE_PAGE_1, "image_prompt": broken_prompt}
    with patch("litellm.completion", return_value=_make_mock_response(json.dumps(bad))):
        with pytest.raises(ValueError, match="image_prompt missing token"):
            generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)


# ---------------------------------------------------------------------------
# litellm call parameters
# ---------------------------------------------------------------------------

def test_litellm_called_with_correct_model(tmp_path):
    with patch("litellm.completion", return_value=_make_mock_response(_llm_json(FAKE_PAGE_1))) as mock_llm:
        generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    _, kwargs = mock_llm.call_args
    assert kwargs["model"] == "ollama/llama3.1"


def test_litellm_called_with_api_base(tmp_path):
    with patch("litellm.completion", return_value=_make_mock_response(_llm_json(FAKE_PAGE_1))) as mock_llm:
        generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    _, kwargs = mock_llm.call_args
    assert kwargs["api_base"] == "http://localhost:11434"


def test_litellm_called_with_system_prompt(tmp_path):
    with patch("litellm.completion", return_value=_make_mock_response(_llm_json(FAKE_PAGE_1))) as mock_llm:
        generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    _, kwargs = mock_llm.call_args
    messages = kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert len(messages[0]["content"]) > 100  # system prompt is substantial


def test_litellm_called_with_gist_in_user_message(tmp_path):
    with patch("litellm.completion", return_value=_make_mock_response(_llm_json(FAKE_PAGE_1))) as mock_llm:
        generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    _, kwargs = mock_llm.call_args
    messages = kwargs["messages"]
    assert messages[1]["role"] == "user"
    assert "Introduction to Intelligence" in messages[1]["content"]


def test_litellm_called_with_grade_in_user_message(tmp_path):
    with patch("litellm.completion", return_value=_make_mock_response(_llm_json(FAKE_PAGE_1))) as mock_llm:
        generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    _, kwargs = mock_llm.call_args
    messages = kwargs["messages"]
    assert "Grade: 6" in messages[1]["content"]


def test_litellm_temperature_and_max_tokens(tmp_path):
    with patch("litellm.completion", return_value=_make_mock_response(_llm_json(FAKE_PAGE_1))) as mock_llm:
        generate_content_jsons(FAKE_GIST, 6, 1, 1, tmp_path)

    _, kwargs = mock_llm.call_args
    assert kwargs["temperature"] == 0.7
    assert kwargs["max_tokens"] == 4096
