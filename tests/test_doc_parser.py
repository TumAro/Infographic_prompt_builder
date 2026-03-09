"""Tests for doc_parser.py using Grade 6 data files."""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from doc_parser import parse_syllabus, parse_module, get_topic_content

DATA = Path(__file__).parent.parent / "data" / "grade_6"
SYLLABUS = DATA / "Class_6.docx"
MODULE_1 = DATA / "Module_1_-_What_is_Artificial_Intelligence.docx"


# ---------------------------------------------------------------------------
# parse_syllabus
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
# parse_module
# ---------------------------------------------------------------------------

class TestParseModule:
    @pytest.fixture(scope="class")
    def syllabus(self):
        return parse_syllabus(SYLLABUS)

    @pytest.fixture(scope="class")
    def module(self, syllabus):
        return parse_module(MODULE_1, syllabus, 1)

    @pytest.fixture(scope="class")
    def all_blocks(self, module):
        return [b for t in module["topics"] for st in t["subtopics"] for b in st["blocks"]]

    def test_module_num(self, module):
        assert module["module_num"] == 1

    def test_topic_count(self, module):
        assert len(module["topics"]) == 4

    def test_topic_1_name(self, module):
        assert module["topics"][0]["name"] == "Introduction to Intelligence"
        assert module["topics"][0]["topic_num"] == 1

    def test_topic_2_name(self, module):
        assert module["topics"][1]["name"] == "The Evolution of AI"

    def test_topic_order(self, module):
        nums = [t["topic_num"] for t in module["topics"]]
        assert nums == [1, 2, 3, 4]

    def test_each_topic_has_subtopics(self, module):
        for topic in module["topics"]:
            assert len(topic["subtopics"]) > 0, f"Topic '{topic['name']}' has no subtopics"

    def test_blocks_non_empty(self, all_blocks):
        assert len(all_blocks) > 0

    def test_paragraph_type_present(self, all_blocks):
        types = {b["type"] for b in all_blocks}
        assert "paragraph" in types

    def test_figure_caption_present(self, all_blocks):
        types = {b["type"] for b in all_blocks}
        assert "figure_caption" in types

    def test_table_type_present(self, all_blocks):
        types = {b["type"] for b in all_blocks}
        assert "table" in types

    def test_table_count(self, all_blocks):
        tables = [b for b in all_blocks if b["type"] == "table"]
        assert len(tables) >= 2  # Module 1 has 2 tables

    def test_block_schema_text_blocks(self, all_blocks):
        for b in all_blocks:
            assert "type" in b
            if b["type"] != "table":
                assert "text" in b, f"Non-table block missing 'text': {b}"

    def test_block_schema_table_blocks(self, all_blocks):
        for b in all_blocks:
            if b["type"] == "table":
                assert "rows" in b, f"Table block missing 'rows': {b}"
                assert isinstance(b["rows"], list)

    def test_valid_block_types(self, all_blocks):
        valid = {"paragraph", "bullet", "story", "fun_fact", "activity",
                 "figure_caption", "image_caption", "table"}
        for b in all_blocks:
            assert b["type"] in valid, f"Unknown block type: {b['type']}"

    def test_missing_module_raises(self, syllabus):
        with pytest.raises(ValueError):
            parse_module(MODULE_1, syllabus, 99)


# ---------------------------------------------------------------------------
# get_topic_content
# ---------------------------------------------------------------------------

class TestGetTopicContent:
    @pytest.fixture(scope="class")
    def topic_1(self):
        return get_topic_content(MODULE_1, SYLLABUS, module_num=1, topic_num=1)

    def test_topic_name(self, topic_1):
        assert topic_1["topic"] == "Introduction to Intelligence"

    def test_has_subtopics(self, topic_1):
        assert len(topic_1["subtopics"]) > 0

    def test_subtopic_schema(self, topic_1):
        for st in topic_1["subtopics"]:
            assert "name" in st
            assert "blocks" in st
            assert isinstance(st["blocks"], list)

    def test_topic_2_name(self):
        result = get_topic_content(MODULE_1, SYLLABUS, module_num=1, topic_num=2)
        assert result["topic"] == "The Evolution of AI"

    def test_topic_3_name(self):
        result = get_topic_content(MODULE_1, SYLLABUS, module_num=1, topic_num=3)
        assert result["topic"] == "Types of AI Around Us"

    def test_topic_4_name(self):
        result = get_topic_content(MODULE_1, SYLLABUS, module_num=1, topic_num=4)
        assert "AI" in result["topic"] and "ML" in result["topic"] and "DL" in result["topic"]

    def test_nonexistent_topic_raises(self):
        with pytest.raises(ValueError):
            get_topic_content(MODULE_1, SYLLABUS, module_num=1, topic_num=99)

    def test_subtopics_have_blocks(self, topic_1):
        for st in topic_1["subtopics"]:
            assert len(st["blocks"]) > 0, f"Subtopic '{st['name']}' has no blocks"
