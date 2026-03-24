"""Tests for doc_parser.py using Grade 6 data files."""

import io
import struct
import zlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import doc_parser
import vision_llm
from doc_parser import parse_syllabus, write_topic_md

DATA = Path(__file__).parent.parent / "data" / "grade_6"
SYLLABUS = DATA / "Class_6.docx"
MODULE_1 = DATA / "Module_1_-_What_is_Artificial_Intelligence.docx"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_1px_png() -> bytes:
    """Return bytes of a valid minimal 1×1 white PNG."""
    def chunk(ctype: bytes, data: bytes) -> bytes:
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
    iend = chunk(b"IEND", b"")
    return header + ihdr + idat + iend


def _fake_module_with_image(image_bytes: bytes) -> dict:
    """Return a synthetic _parse_module result that includes one image block."""
    return {
        "module_num": 1,
        "topics": [
            {
                "topic_num": 1,
                "name": "Introduction to Intelligence",
                "subtopics": [
                    {
                        "name": "Human Intelligence vs. Machine Intelligence",
                        "blocks": [
                            {"type": "paragraph", "text": "Some content here."},
                            {"type": "image", "rId": "rId1", "extension": "png"},
                        ],
                    }
                ],
            }
        ],
    }


def _fake_syllabus() -> dict:
    return {
        "grade": 6,
        "modules": [
            {
                "module_num": 1,
                "name": "What is Artificial Intelligence",
                "topics": [
                    {
                        "topic_num": 1,
                        "name": "Introduction to Intelligence",
                        "subtopics": ["Human Intelligence vs. Machine Intelligence"],
                    }
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# parse_syllabus — unchanged API, tests kept
# ---------------------------------------------------------------------------

class TestParseSyllabus:
    @pytest.fixture(scope="class")
    def syllabus(self):
        return parse_syllabus(SYLLABUS)

    def test_grade(self, syllabus):
        assert syllabus["grade"] == 6

    def test_module_count(self, syllabus):
        assert len(syllabus["modules"]) == 6

    def test_module_1_num(self, syllabus):
        assert syllabus["modules"][0]["module_num"] == 1

    def test_module_1_topic_count(self, syllabus):
        assert len(syllabus["modules"][0]["topics"]) == 4

    def test_module_1_topic_1_name(self, syllabus):
        t1 = syllabus["modules"][0]["topics"][0]
        assert t1["name"] == "Introduction to Intelligence"
        assert t1["topic_num"] == 1

    def test_module_1_topic_1_subtopics(self, syllabus):
        subtopics = syllabus["modules"][0]["topics"][0]["subtopics"]
        assert "Human Intelligence vs. Machine Intelligence" in subtopics

    def test_module_1_topic_2_name(self, syllabus):
        t2 = syllabus["modules"][0]["topics"][1]
        assert t2["name"] == "The Evolution of AI"
        assert t2["topic_num"] == 2

    def test_module_1_topic_3_name(self, syllabus):
        t3 = syllabus["modules"][0]["topics"][2]
        assert t3["name"] == "Types of AI Around Us"

    def test_module_1_topic_4_name(self, syllabus):
        t4 = syllabus["modules"][0]["topics"][3]
        assert "AI" in t4["name"] and "ML" in t4["name"] and "DL" in t4["name"]

    def test_module_2_exists(self, syllabus):
        m2 = syllabus["modules"][1]
        assert m2["module_num"] == 2
        assert len(m2["topics"]) == 4

    def test_subtopics_are_list(self, syllabus):
        for module in syllabus["modules"]:
            for topic in module["topics"]:
                assert isinstance(topic["subtopics"], list)


# ---------------------------------------------------------------------------
# write_topic_md — integration tests against real Grade 6 data
# ---------------------------------------------------------------------------

class TestWriteTopicMd:
    """Tests that use real Grade 6 docx files with vision_llm mocked out."""

    @pytest.fixture(autouse=True)
    def mock_vision(self, monkeypatch):
        """Prevent any real LLM calls during tests."""
        monkeypatch.setattr(vision_llm, "describe_image", lambda *a, **kw: "mock image description")

    @pytest.fixture
    def topic_md(self, tmp_path):
        result = write_topic_md(
            module_path=MODULE_1,
            syllabus_path=SYLLABUS,
            module_num=1,
            topic_num=1,
            structured_base=tmp_path / "structured_data",
            grade=6,
        )
        assert result is not None, "write_topic_md should return a Path, not None"
        return result

    def test_creates_file(self, topic_md):
        assert topic_md.exists()
        assert topic_md.name == "topic.md"

    def test_output_path_structure(self, topic_md):
        parts = topic_md.parts
        assert "grade_6" in parts
        assert "module_1" in parts
        assert "topic_1" in parts

    def test_topic_heading(self, topic_md):
        content = topic_md.read_text(encoding="utf-8")
        assert "# Topic: Introduction to Intelligence" in content

    def test_subtopic_headings_present(self, topic_md):
        content = topic_md.read_text(encoding="utf-8")
        assert "## Subtopic: " in content

    def test_subtopic_name_from_syllabus(self, topic_md):
        content = topic_md.read_text(encoding="utf-8")
        assert "## Subtopic: Human Intelligence vs. Machine Intelligence" in content

    def test_markdown_blockquotes(self, topic_md):
        content = topic_md.read_text(encoding="utf-8")
        # Topic 1 has stories, fun_facts, and activities — all render as "> ..." blockquotes
        has_blockquote = any(line.startswith("> ") for line in content.splitlines())
        assert has_blockquote, "Expected at least one blockquote line (story/fun_fact/activity)"

    def test_markdown_table(self, tmp_path, mock_vision):
        # Tables exist in topic 3 of module 1 (not topic 1)
        result = write_topic_md(
            module_path=MODULE_1,
            syllabus_path=SYLLABUS,
            module_num=1,
            topic_num=3,
            structured_base=tmp_path / "structured_data",
            grade=6,
        )
        assert result is not None
        content = result.read_text(encoding="utf-8")
        has_table = any(line.startswith("|") for line in content.splitlines())
        assert has_table, "Expected at least one markdown table row in topic 3"

    def test_no_raw_block_type_labels(self, topic_md):
        content = topic_md.read_text(encoding="utf-8")
        # The old gist_llm format labels like [paragraph] must NOT appear
        for label in ("[paragraph]", "[bullet]", "[story]", "[fun_fact]", "[activity]"):
            assert label not in content, f"Raw block label found in topic.md: {label!r}"

    def test_skip_if_exists(self, tmp_path, mock_vision):
        base = tmp_path / "structured_data"
        kwargs = dict(module_path=MODULE_1, syllabus_path=SYLLABUS,
                      module_num=1, topic_num=1, structured_base=base, grade=6)
        first = write_topic_md(**kwargs)
        assert first is not None
        first_mtime = first.stat().st_mtime

        # Second call without force → skip
        second = write_topic_md(**kwargs)
        assert second is None, "Second call without force should return None"
        assert first.stat().st_mtime == first_mtime, "File should not be modified"

    def test_force_overwrite(self, tmp_path, mock_vision):
        base = tmp_path / "structured_data"
        kwargs = dict(module_path=MODULE_1, syllabus_path=SYLLABUS,
                      module_num=1, topic_num=1, structured_base=base, grade=6)
        first = write_topic_md(**kwargs)
        assert first is not None
        first_mtime = first.stat().st_mtime

        # Second call with force=True → file overwritten
        second = write_topic_md(**kwargs, force=True)
        assert second is not None
        assert second.stat().st_mtime >= first_mtime

    def test_invalid_topic_raises(self, tmp_path, mock_vision):
        with pytest.raises((ValueError, Exception)):
            write_topic_md(
                module_path=MODULE_1,
                syllabus_path=SYLLABUS,
                module_num=1,
                topic_num=99,
                structured_base=tmp_path / "structured_data",
                grade=6,
            )


# ---------------------------------------------------------------------------
# write_topic_md — figure block format (fully mocked)
# ---------------------------------------------------------------------------

class TestFigureBlock:
    """Verifies [Figure N] block output format using fully mocked document data."""

    def test_figure_block_format(self, tmp_path, monkeypatch):
        image_bytes = _make_1px_png()

        # Mock _parse_module to inject one image block
        monkeypatch.setattr(
            doc_parser, "_parse_module",
            lambda doc, entry: _fake_module_with_image(image_bytes),
        )

        # Mock parse_syllabus
        monkeypatch.setattr(doc_parser, "parse_syllabus", lambda path: _fake_syllabus())

        # Mock Document to expose fake related_parts
        class _FakePart:
            blob = image_bytes

        class _FakeRelatedParts:
            def __contains__(self, key):
                return True
            def __getitem__(self, key):
                return _FakePart()

        class _FakeDocPart:
            related_parts = _FakeRelatedParts()

        class _FakeDoc:
            part = _FakeDocPart()

        monkeypatch.setattr(doc_parser, "Document", lambda path: _FakeDoc())

        # Mock vision_llm
        monkeypatch.setattr(vision_llm, "describe_image", lambda *a, **kw: "test description")

        result = write_topic_md(
            module_path="fake.docx",
            syllabus_path="fake_syllabus.docx",
            module_num=1,
            topic_num=1,
            structured_base=tmp_path / "structured_data",
            grade=6,
        )

        assert result is not None
        content = result.read_text(encoding="utf-8")
        assert "> **[Figure 1]** test description" in content

    def test_figure_caption_included(self, tmp_path, monkeypatch):
        image_bytes = _make_1px_png()

        # Image block followed by a caption block
        fake_module = {
            "module_num": 1,
            "topics": [
                {
                    "topic_num": 1,
                    "name": "Introduction to Intelligence",
                    "subtopics": [
                        {
                            "name": "Human Intelligence vs. Machine Intelligence",
                            "blocks": [
                                {"type": "image", "rId": "rId1", "extension": "png"},
                                {"type": "figure_caption", "text": "Figure 1 Comparison chart"},
                            ],
                        }
                    ],
                }
            ],
        }

        monkeypatch.setattr(doc_parser, "_parse_module", lambda doc, entry: fake_module)
        monkeypatch.setattr(doc_parser, "parse_syllabus", lambda path: _fake_syllabus())

        class _FakePart:
            blob = image_bytes

        class _FakeRelatedParts:
            def __contains__(self, key): return True
            def __getitem__(self, key): return _FakePart()

        class _FakeDoc:
            class part:
                related_parts = _FakeRelatedParts()

        monkeypatch.setattr(doc_parser, "Document", lambda path: _FakeDoc())
        monkeypatch.setattr(vision_llm, "describe_image", lambda *a, **kw: "test description")

        result = write_topic_md(
            module_path="fake.docx",
            syllabus_path="fake_syllabus.docx",
            module_num=1,
            topic_num=1,
            structured_base=tmp_path / "structured_data",
            grade=6,
        )

        content = result.read_text(encoding="utf-8")
        assert "> **[Figure 1]** test description" in content
        assert "*Caption: Figure 1 Comparison chart*" in content

    def test_figure_counter_increments(self, tmp_path, monkeypatch):
        image_bytes = _make_1px_png()

        fake_module = {
            "module_num": 1,
            "topics": [
                {
                    "topic_num": 1,
                    "name": "Introduction to Intelligence",
                    "subtopics": [
                        {
                            "name": "Human Intelligence vs. Machine Intelligence",
                            "blocks": [
                                {"type": "image", "rId": "rId1", "extension": "png"},
                                {"type": "image", "rId": "rId2", "extension": "png"},
                            ],
                        }
                    ],
                }
            ],
        }

        monkeypatch.setattr(doc_parser, "_parse_module", lambda doc, entry: fake_module)
        monkeypatch.setattr(doc_parser, "parse_syllabus", lambda path: _fake_syllabus())

        class _FakePart:
            blob = image_bytes

        class _FakeRelatedParts:
            def __contains__(self, key): return True
            def __getitem__(self, key): return _FakePart()

        class _FakeDoc:
            class part:
                related_parts = _FakeRelatedParts()

        monkeypatch.setattr(doc_parser, "Document", lambda path: _FakeDoc())
        monkeypatch.setattr(vision_llm, "describe_image", lambda *a, **kw: "desc")

        result = write_topic_md(
            module_path="fake.docx",
            syllabus_path="fake_syllabus.docx",
            module_num=1,
            topic_num=1,
            structured_base=tmp_path / "structured_data",
            grade=6,
        )

        content = result.read_text(encoding="utf-8")
        assert "> **[Figure 1]** desc" in content
        assert "> **[Figure 2]** desc" in content
