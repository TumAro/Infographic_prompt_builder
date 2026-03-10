"""
doc_parser.py — Parses syllabus + module .docx files into structured in-memory dicts.

Relies on text-pattern matching against syllabus topic/subtopic names.
All paragraphs in module .docx files use Normal style — no heading hierarchy.

Content block types: paragraph, bullet, story, fun_fact, activity,
                     figure_caption, image_caption, table.
"""

import re
from pathlib import Path

from docx import Document


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _iter_body_items(doc):
    """Yield ('paragraph', para) or ('table', tbl) in document order."""
    para_idx = 0
    table_idx = 0
    paras = doc.paragraphs
    tables = doc.tables
    for child in doc.element.body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "p":
            if para_idx < len(paras):
                yield "paragraph", paras[para_idx]
                para_idx += 1
        elif tag == "tbl":
            if table_idx < len(tables):
                yield "table", tables[table_idx]
                table_idx += 1


def _normalize(text: str) -> str:
    """Lowercase, normalise smart quotes, strip trailing punctuation, collapse whitespace."""
    # Replace common Unicode punctuation variants
    text = (
        text
        .replace("\u2019", "'").replace("\u2018", "'")
        .replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u2013", "-").replace("\u2014", "-")
        .replace("\u2026", "...")
    )
    text = text.strip().lower()
    text = re.sub(r"[?!.,:;]+$", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


_STORY_STARTERS = (
    "once upon",
    "one day,",
    "one day ",
    "imagine ",
    "in a land",
    "in the land",
    "long ago",
)

_BULLET_CHARS = set("•–-*◦→")


def _classify_block(text: str, in_story: bool) -> str:
    """Return the block type for a paragraph of plain body text."""
    stripped = text.strip()
    lower = stripped.lower()

    if re.match(r"figure\s+\d+", lower):
        return "figure_caption"
    if re.match(r"image\s+\d+", lower):
        return "image_caption"
    if re.match(r"(a\s+)?quick\s+activity", lower) or lower.startswith("activity:") or lower.startswith("activity "):
        return "activity"
    if lower.startswith("fun fact"):
        return "fun_fact"
    if any(lower.startswith(s) for s in _STORY_STARTERS):
        return "story"
    if in_story:
        return "story"
    if stripped and stripped[0] in _BULLET_CHARS:
        return "bullet"
    if re.match(r"^\d+[.)]\s", stripped):
        return "bullet"
    return "paragraph"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_syllabus(path) -> dict:
    """
    Parse a syllabus .docx (e.g. Class_6.docx) into a grade/module/topic/subtopic map.

    Returns:
        {
            "grade": 6,
            "modules": [
                {
                    "module_num": 1,
                    "name": "What is Artificial Intelligence?",
                    "topics": [
                        {
                            "topic_num": 1,
                            "name": "Introduction to Intelligence",
                            "subtopics": ["Human Intelligence vs. Machine Intelligence", ...]
                        },
                        ...
                    ]
                },
                ...
            ]
        }
    """
    path = Path(path)
    doc = Document(str(path))

    # Extract grade from filename "Class_N.docx"
    m = re.search(r"Class_(\d+)", path.stem, re.IGNORECASE)
    grade = int(m.group(1)) if m else 0

    modules = []
    current_module = None

    for item_type, item in _iter_body_items(doc):
        if item_type == "paragraph":
            text = item.text.strip()
            m = re.match(r"Module\s+(\d+)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
            if m:
                if current_module is not None:
                    modules.append(current_module)
                current_module = {
                    "module_num": int(m.group(1)),
                    "name": m.group(2).strip().rstrip("?!."),
                    "topics": [],
                }

        elif item_type == "table" and current_module is not None:
            for row in item.rows:
                cells = [c.text.strip() for c in row.cells]
                if not cells:
                    continue
                # Skip header row or empty first cell
                try:
                    topic_num = int(cells[0])
                except (ValueError, IndexError):
                    continue
                topic_name = cells[1] if len(cells) > 1 else ""
                if not topic_name:
                    continue
                subtopics = []
                if len(cells) > 2:
                    subtopics = [s.strip() for s in cells[2].split("\n") if s.strip()]
                current_module["topics"].append(
                    {
                        "topic_num": topic_num,
                        "name": topic_name,
                        "subtopics": subtopics,
                    }
                )

    if current_module is not None:
        modules.append(current_module)

    return {"grade": grade, "modules": modules}


def parse_module(path, syllabus: dict, module_num: int) -> dict:
    """
    Parse a module .docx into content blocks grouped by topic → subtopic.

    Topic and subtopic boundaries are detected by matching paragraph text against
    the names listed in the syllabus (case-insensitive, smart-quote normalised).
    Bold formatting is NOT required — all boundary paragraphs use Normal style.
    When a subtopic from a new topic is encountered before an explicit topic header,
    the new topic is started implicitly.

    Args:
        path:       Path to the module .docx file.
        syllabus:   Dict returned by parse_syllabus().
        module_num: 1-indexed module number.

    Returns:
        {
            "module_num": 1,
            "topics": [
                {
                    "topic_num": 1,
                    "name": "Introduction to Intelligence",
                    "subtopics": [
                        {
                            "name": "Human Intelligence vs. Machine Intelligence",
                            "blocks": [
                                {"type": "paragraph", "text": "..."},
                                {"type": "story",     "text": "..."},
                                {"type": "table",     "rows": [...]},
                            ]
                        },
                        ...
                    ]
                },
                ...
            ]
        }
    """
    module_entry = next(
        (m for m in syllabus["modules"] if m["module_num"] == module_num), None
    )
    if module_entry is None:
        raise ValueError(f"Module {module_num} not found in syllabus")

    # Build lookup tables
    # topic_lookup: norm_name → topic dict (from syllabus)
    topic_lookup: dict = {}
    # subtopic_lookup: norm_name → list of (topic_num, canonical_subtopic_name)
    # A list is used because multiple topics may share the same subtopic name
    # (e.g. "Recap and What's Next" in topic 3 and topic 4). At lookup time the
    # parser prefers the candidate that matches the current topic context, so each
    # "Recap" paragraph is attributed to the correct topic.
    subtopic_lookup: dict = {}
    # topic_by_num: topic_num → topic dict (for implicit topic creation)
    topic_by_num: dict = {}

    for topic in module_entry["topics"]:
        topic_lookup[_normalize(topic["name"])] = topic
        topic_by_num[topic["topic_num"]] = topic
        for st_name in topic["subtopics"]:
            subtopic_lookup.setdefault(_normalize(st_name), []).append(
                (topic["topic_num"], st_name)
            )

    # --- Mutable parsing state (via list cells to allow mutation inside closures) ---
    result_topics: list = []
    state = {
        "cur_topic": None,       # dict being built
        "cur_st_name": None,     # canonical subtopic name
        "cur_blocks": [],        # accumulating blocks for current subtopic
        "in_story": False,
    }

    def _flush_subtopic() -> None:
        if state["cur_topic"] is None or not state["cur_blocks"]:
            state["cur_blocks"] = []
            return
        if state["cur_st_name"] is None:
            # Content before the first subtopic header — discard rather than
            # create a spurious subtopic named after the topic itself.
            state["cur_blocks"] = []
            return
        state["cur_topic"]["subtopics"].append(
            {"name": state["cur_st_name"], "blocks": state["cur_blocks"]}
        )
        state["cur_blocks"] = []

    def _flush_topic() -> None:
        _flush_subtopic()
        if state["cur_topic"] is not None:
            result_topics.append(state["cur_topic"])

    def _start_topic(topic_num: int) -> None:
        _flush_topic()
        syl = topic_by_num[topic_num]
        state["cur_topic"] = {
            "topic_num": topic_num,
            "name": syl["name"],
            "subtopics": [],
        }
        state["cur_st_name"] = None
        state["cur_blocks"] = []
        state["in_story"] = False

    def _start_subtopic(topic_num: int, st_name: str) -> None:
        # Implicitly start parent topic if needed
        if state["cur_topic"] is None or state["cur_topic"]["topic_num"] != topic_num:
            _start_topic(topic_num)
        else:
            _flush_subtopic()
        state["cur_st_name"] = st_name
        state["cur_blocks"] = []
        state["in_story"] = False

    doc = Document(str(path))

    for item_type, item in _iter_body_items(doc):
        if item_type == "paragraph":
            text = item.text.strip()
            if not text:
                continue
            norm = _normalize(text)

            if norm in topic_lookup:
                _start_topic(topic_lookup[norm]["topic_num"])

            elif norm in subtopic_lookup:
                candidates = subtopic_lookup[norm]
                cur = state["cur_topic"]["topic_num"] if state["cur_topic"] else None
                # Prefer the candidate belonging to the current topic so that shared
                # subtopic names (e.g. "Recap and What's Next" in both topic 3 and 4)
                # are attributed correctly without switching topics.
                topic_num, st_name = next(
                    (c for c in candidates if c[0] == cur), candidates[0]
                )
                _start_subtopic(topic_num, st_name)

            else:
                if state["cur_topic"] is not None:
                    block_type = _classify_block(text, state["in_story"])
                    if block_type == "story":
                        state["in_story"] = True
                    elif block_type != "paragraph":
                        state["in_story"] = False
                    state["cur_blocks"].append({"type": block_type, "text": text})

        elif item_type == "table":
            if state["cur_topic"] is not None:
                state["in_story"] = False
                rows = [
                    [cell.text.strip() for cell in row.cells]
                    for row in item.rows
                ]
                state["cur_blocks"].append({"type": "table", "rows": rows})

    _flush_topic()

    return {"module_num": module_num, "topics": result_topics}


def get_topic_content(module_path, syllabus_path, module_num: int, topic_num: int) -> dict:
    """
    Return the content dict for a single topic.

    Args:
        module_path:   Path to the module .docx file.
        syllabus_path: Path to the syllabus .docx file.
        module_num:    1-indexed module number.
        topic_num:     1-indexed topic number.

    Returns:
        {
            "topic": "Introduction to Intelligence",
            "subtopics": [
                {"name": "...", "blocks": [...]},
                ...
            ]
        }
    """
    syllabus = parse_syllabus(syllabus_path)
    module = parse_module(module_path, syllabus, module_num)

    # Collect ALL instances of this topic — the module docx may have topics appearing
    # out of linear order (e.g. topic 2 content, then topic 4 overview, then topic 2
    # resumes). Each re-start creates a separate instance in result_topics; merging
    # them ensures no subtopics are silently dropped.
    instances = [t for t in module["topics"] if t["topic_num"] == topic_num]
    if not instances:
        raise ValueError(f"Topic {topic_num} not found in module {module_num}")

    merged_subtopics = []
    for inst in instances:
        merged_subtopics.extend(inst["subtopics"])

    # Warn about subtopics listed in the syllabus but not found anywhere in the docx.
    syl_module = next(m for m in syllabus["modules"] if m["module_num"] == module_num)
    syl_topic = next(t for t in syl_module["topics"] if t["topic_num"] == topic_num)
    found_names = {s["name"] for s in merged_subtopics}
    for expected in syl_topic["subtopics"]:
        if expected not in found_names:
            print(
                f"[doc_parser] WARNING: subtopic not found in module docx "
                f"(grade {syllabus['grade']}, module {module_num}, topic {topic_num}): {expected!r}"
            )

    return {"topic": instances[0]["name"], "subtopics": merged_subtopics}
