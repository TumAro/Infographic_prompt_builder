"""Tests for resolver.py — pure data transformation, no mocks needed for core logic."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import resolver
from resolver import _resolve_value, _resolve_string, resolve_topic

# ---------------------------------------------------------------------------
# Inline style configs (avoid dependency on project files for unit tests)
# ---------------------------------------------------------------------------

GLOBAL = {
    "illustration_style": "flat vector cartoon",
    "aspect_ratio": "9:16",
    "font_style": "rounded sans-serif",
    "layout_language": "infographic",
}

GRADE = {
    "background_color": "#FFF9C4",
    "primary_color": "#FF6B35",
    "accent_color": "#4ECDC4",
    "mood": "playful, energetic, friendly",
    "complexity_level": "low",
}


def rv(value):
    """Shorthand: resolve a value with the test configs."""
    return _resolve_value(value, GLOBAL, GRADE)


def rs(text):
    """Shorthand: resolve a string with the test configs."""
    return _resolve_string(text, GLOBAL, GRADE)


# ---------------------------------------------------------------------------
# _resolve_string / _resolve_value — token replacement
# ---------------------------------------------------------------------------

def test_resolves_global_token():
    assert rs("{{global.illustration_style}}") == "flat vector cartoon"


def test_resolves_grade_token():
    assert rs("{{grade.background_color}}") == "#FFF9C4"


def test_resolves_multiple_tokens_in_one_string():
    text = "Style: {{global.illustration_style}} on {{grade.background_color}}"
    result = rs(text)
    assert result == "Style: flat vector cartoon on #FFF9C4"


def test_non_token_string_untouched():
    assert rs("Hello world, no tokens here.") == "Hello world, no tokens here."


def test_empty_string_untouched():
    assert rs("") == ""


def test_integer_value_untouched():
    assert rv(42) == 42


def test_float_value_untouched():
    assert rv(3.14) == 3.14


def test_bool_value_untouched():
    assert rv(True) is True
    assert rv(False) is False


def test_none_value_untouched():
    assert rv(None) is None


def test_resolves_nested_dict():
    data = {"style": {"background": "{{grade.background_color}}"}}
    result = rv(data)
    assert result == {"style": {"background": "#FFF9C4"}}


def test_resolves_nested_list():
    data = ["{{global.font_style}}", "{{grade.mood}}"]
    result = rv(data)
    assert result == ["rounded sans-serif", "playful, energetic, friendly"]


def test_resolves_token_inside_dict_in_list():
    data = [{"key": "{{global.aspect_ratio}}"}]
    result = rv(data)
    assert result == [{"key": "9:16"}]


def test_dict_keys_are_not_resolved():
    """Token-like dict keys must be left as-is (only values are resolved)."""
    data = {"{{global.illustration_style}}": "literal key"}
    result = rv(data)
    # Key unchanged; value (no token) also unchanged
    assert "{{global.illustration_style}}" in result


def test_resolves_deeply_nested():
    data = {"a": {"b": {"c": "{{grade.primary_color}}"}}}
    assert rv(data) == {"a": {"b": {"c": "#FF6B35"}}}


# ---------------------------------------------------------------------------
# _resolve_string — error cases
# ---------------------------------------------------------------------------

def test_missing_global_key_raises():
    with pytest.raises(ValueError, match="global.nonexistent"):
        rs("{{global.nonexistent}}")


def test_missing_grade_key_raises():
    with pytest.raises(ValueError, match="grade.nonexistent"):
        rs("{{grade.nonexistent}}")


def test_unknown_namespace_raises():
    with pytest.raises(ValueError, match="other.key"):
        rs("{{other.key}}")


def test_error_message_contains_full_token():
    with pytest.raises(ValueError) as exc_info:
        rs("{{global.missing_key}}")
    assert "{{global.missing_key}}" in str(exc_info.value)


# ---------------------------------------------------------------------------
# resolve_topic — file I/O tests (patch resolver.ROOT to use tmp_path)
# ---------------------------------------------------------------------------

def _setup_root(tmp_path: Path) -> None:
    """Create configs and output structure under tmp_path."""
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "global_style.json").write_text(
        json.dumps(GLOBAL), encoding="utf-8"
    )
    (configs / "grade_6_style.json").write_text(
        json.dumps(GRADE), encoding="utf-8"
    )


CONTENT_PAGE = {
    "page": 1,
    "topic": "Introduction to Intelligence",
    "layout_type": "multi_column",
    "title": "What is Intelligence?",
    "style": {
        "illustration_style": "{{global.illustration_style}}",
        "background_color": "{{grade.background_color}}",
    },
    "image_prompt": "Use {{global.aspect_ratio}} with {{grade.mood}} tone.",
}


def test_resolve_topic_writes_final_json(tmp_path):
    _setup_root(tmp_path)
    topic_dir = tmp_path / "output" / "grade_6" / "module_1" / "topic_1"
    topic_dir.mkdir(parents=True)
    (topic_dir / "page_1_content.json").write_text(
        json.dumps(CONTENT_PAGE), encoding="utf-8"
    )

    with patch.object(resolver, "ROOT", tmp_path):
        paths = resolve_topic(6, 1, 1)

    assert len(paths) == 1
    final_path = topic_dir / "page_1_final.json"
    assert final_path.exists()
    resolved = json.loads(final_path.read_text(encoding="utf-8"))
    assert resolved["style"]["illustration_style"] == "flat vector cartoon"
    assert resolved["style"]["background_color"] == "#FFF9C4"
    assert "9:16" in resolved["image_prompt"]
    assert "playful, energetic, friendly" in resolved["image_prompt"]


def test_resolve_topic_resolves_two_pages(tmp_path):
    _setup_root(tmp_path)
    topic_dir = tmp_path / "output" / "grade_6" / "module_1" / "topic_1"
    topic_dir.mkdir(parents=True)

    page2 = dict(CONTENT_PAGE, page=2)
    (topic_dir / "page_1_content.json").write_text(json.dumps(CONTENT_PAGE), encoding="utf-8")
    (topic_dir / "page_2_content.json").write_text(json.dumps(page2), encoding="utf-8")

    with patch.object(resolver, "ROOT", tmp_path):
        paths = resolve_topic(6, 1, 1)

    assert len(paths) == 2
    assert (topic_dir / "page_1_final.json").exists()
    assert (topic_dir / "page_2_final.json").exists()


def test_resolve_topic_no_content_files_returns_empty(tmp_path):
    _setup_root(tmp_path)
    topic_dir = tmp_path / "output" / "grade_6" / "module_1" / "topic_1"
    topic_dir.mkdir(parents=True)

    with patch.object(resolver, "ROOT", tmp_path):
        paths = resolve_topic(6, 1, 1)

    assert paths == []


def test_resolve_topic_returns_path_list(tmp_path):
    _setup_root(tmp_path)
    topic_dir = tmp_path / "output" / "grade_6" / "module_1" / "topic_1"
    topic_dir.mkdir(parents=True)
    (topic_dir / "page_1_content.json").write_text(json.dumps(CONTENT_PAGE), encoding="utf-8")

    with patch.object(resolver, "ROOT", tmp_path):
        result = resolve_topic(6, 1, 1)

    assert isinstance(result, list)
    assert all(isinstance(p, str) for p in result)
    assert result[0].endswith("page_1_final.json")


def test_resolve_topic_bad_token_raises(tmp_path):
    _setup_root(tmp_path)
    topic_dir = tmp_path / "output" / "grade_6" / "module_1" / "topic_1"
    topic_dir.mkdir(parents=True)
    bad_content = dict(CONTENT_PAGE, image_prompt="{{global.nonexistent_key}}")
    (topic_dir / "page_1_content.json").write_text(json.dumps(bad_content), encoding="utf-8")

    with patch.object(resolver, "ROOT", tmp_path):
        with pytest.raises(ValueError, match="global.nonexistent_key"):
            resolve_topic(6, 1, 1)
