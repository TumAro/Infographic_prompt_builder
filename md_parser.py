"""
md_parser.py — Reads structured topic.md files and reconstructs the dict format
that gist_llm.generate_gist() expects.

The topic.md files are written by doc_parser.write_topic_md() and live at:
    structured_data/grade_N/module_N/topic_N/topic.md

Public API
----------
parse_topic_md(md_path) -> dict
    Parses a topic.md file and returns:
        {
            "topic": "Topic Name",
            "subtopics": [
                {"name": "Subtopic Name", "blocks": [{"type": ..., "text": ...}, ...]},
                ...
            ]
        }

get_topic_content_from_md(grade, module_num, topic_num, structured_base) -> dict
    Convenience wrapper: locates the topic.md and calls parse_topic_md().
    Raises FileNotFoundError if the file does not exist.
"""
from __future__ import annotations

import re
from pathlib import Path


def parse_topic_md(md_path: "str | Path") -> dict:
    """
    Parse a structured topic.md file into the dict format that gist_llm expects.

    Markdown constructs are mapped back to block types:
        ## Subtopic: name   → new subtopic
        - text / * text     → bullet block
        1. text             → bullet block (numbered list)
        > **Fun Fact:** …   → fun_fact block
        > **Activity:** …   → activity block
        > **[Figure N]** …         → figure_caption block (image description)
        > *Caption: …*             → merged into previous figure_caption block
        > **[Code Figure N]**      → code_image block (header only, no inline text)
        > CODE: line               → appended to code_image["code"]
        > DESCRIPTION: text        → stored as code_image["description"]
        > *Code Image: path*       → stored as code_image["code_file"]
        > text              → story block
        | col | col |       → accumulated into table block
        ### text            → paragraph block (sub-heading as plain text)
        blank line          → ignored
        other text          → paragraph block
    """
    md_path = Path(md_path)
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    topic_name = ""
    subtopics: list[dict] = []
    cur_subtopic: str | None = None
    cur_blocks: list[dict] = []
    table_rows: list[list[str]] = []
    in_code_fence = False

    def _flush_table() -> None:
        nonlocal table_rows
        if table_rows:
            cur_blocks.append({"type": "table", "rows": table_rows})
            table_rows = []

    def _flush_subtopic() -> None:
        nonlocal cur_subtopic, cur_blocks, table_rows
        _flush_table()
        if cur_subtopic is not None:
            subtopics.append({"name": cur_subtopic, "blocks": cur_blocks})
        cur_subtopic = None
        cur_blocks = []

    for line in lines:
        # --- Topic heading ---
        if line.startswith("# Topic:"):
            topic_name = line[len("# Topic:"):].strip()
            continue

        # --- Subtopic heading ---
        if line.startswith("## Subtopic:"):
            _flush_subtopic()
            cur_subtopic = line[len("## Subtopic:"):].strip()
            cur_blocks = []
            in_code_fence = False
            continue

        # Skip lines before the first subtopic
        if cur_subtopic is None:
            continue

        # --- Blank line (flush any open table) ---
        if not line.strip():
            _flush_table()
            continue

        # --- Table row ---
        if line.startswith("|"):
            # Skip separator rows like | --- | --- |
            if re.match(r"^\|\s*[-:]+\s*(\|\s*[-:]+\s*)+\|?\s*$", line):
                continue
            cols = [c.strip() for c in line.strip("|").split("|")]
            table_rows.append(cols)
            continue

        # Non-table line: flush any open table first
        _flush_table()

        # --- Blockquote lines ---
        if line.startswith(">"):
            # Inside a fenced code block — accumulate raw content preserving indentation
            if in_code_fence and cur_blocks and cur_blocks[-1]["type"] == "code_image":
                code_content = line[1:]
                if code_content.startswith(" "):
                    code_content = code_content[1:]
                existing = cur_blocks[-1]["code"]
                cur_blocks[-1]["code"] = (existing + "\n" + code_content) if existing else code_content
                continue

            content = line[1:].strip()

            # Fenced code block: > ``` (toggle open/close)
            if content.startswith("```") and cur_blocks and cur_blocks[-1]["type"] == "code_image":
                in_code_fence = not in_code_fence
                continue

            # Code figure block: > **[Code Figure N]**
            if re.match(r"\*\*\[Code Figure\s+\d+\]\*\*", content):
                m = re.search(r"\[Code Figure\s+(\d+)\]", content)
                label = f"Code Figure {m.group(1)}" if m else "Code Figure"
                cur_blocks.append({"type": "code_image", "text": label, "code": ""})
                continue

            # CODE: line — append to current code_image block
            if content.startswith("CODE:") and cur_blocks and cur_blocks[-1]["type"] == "code_image":
                suffix = content[5:]  # after "CODE:"
                code_line = suffix[1:] if suffix.startswith(" ") else suffix
                existing = cur_blocks[-1]["code"]
                cur_blocks[-1]["code"] = (existing + "\n" + code_line) if existing else code_line
                continue

            # DESCRIPTION: line — store on current code_image block
            if content.startswith("DESCRIPTION:") and cur_blocks and cur_blocks[-1]["type"] == "code_image":
                cur_blocks[-1]["description"] = content[len("DESCRIPTION:"):].strip()
                continue

            # Code image file reference: > *Code Image: path*
            if content.startswith("*Code Image:") and content.endswith("*"):
                file_ref = content[len("*Code Image:"):].rstrip("*").strip()
                if cur_blocks and cur_blocks[-1]["type"] == "code_image":
                    cur_blocks[-1]["code_file"] = file_ref
                continue

            # Figure block: > **[Figure N]** description
            if re.match(r"\*\*\[Figure\s+\d+\]\*\*", content):
                cur_blocks.append({"type": "figure_caption", "text": content})
                continue

            # Caption continuation: > *Caption: ...*
            if content.startswith("*Caption:") and content.endswith("*"):
                caption_text = content[len("*Caption:"):].rstrip("*").strip()
                # Attach to last figure_caption or code_image block if present
                if cur_blocks and cur_blocks[-1]["type"] in ("figure_caption", "code_image"):
                    cur_blocks[-1]["text"] += f"  [Caption: {caption_text}]"
                else:
                    cur_blocks.append({"type": "paragraph", "text": caption_text})
                continue

            # Fun fact: > **Fun Fact:** ...
            if content.startswith("**Fun Fact:**"):
                body = content[len("**Fun Fact:**"):].strip()
                cur_blocks.append({"type": "fun_fact", "text": f"Fun Fact: {body}"})
                continue

            # Activity: > **Activity:** ...
            if content.startswith("**Activity:**"):
                body = content[len("**Activity:**"):].strip()
                cur_blocks.append({"type": "activity", "text": f"Activity: {body}"})
                continue

            # Plain blockquote → story
            cur_blocks.append({"type": "story", "text": content})
            continue

        # --- Bullet (unordered) ---
        if re.match(r"^[-*]\s+", line):
            body = re.sub(r"^[-*]\s+", "", line)
            cur_blocks.append({"type": "bullet", "text": body})
            continue

        # --- Bullet (ordered / numbered) ---
        if re.match(r"^\d+\.\s+", line):
            body = re.sub(r"^\d+\.\s+", "", line)
            cur_blocks.append({"type": "bullet", "text": body})
            continue

        # --- Sub-heading (###) treated as paragraph ---
        if line.startswith("###"):
            body = line.lstrip("#").strip()
            cur_blocks.append({"type": "paragraph", "text": body})
            continue

        # --- Equation line (inline or block) ---
        if line.startswith("$$") or (line.startswith("$") and line.endswith("$")):
            cur_blocks.append({"type": "paragraph", "text": line})
            continue

        # --- [EQUATION: ...] fallback marker ---
        if line.startswith("[EQUATION:"):
            cur_blocks.append({"type": "paragraph", "text": line})
            continue

        # --- Default: paragraph ---
        cur_blocks.append({"type": "paragraph", "text": line})

    _flush_subtopic()

    return {"topic": topic_name, "subtopics": subtopics}


def get_topic_content_from_md(
    grade: int,
    module_num: int,
    topic_num: int,
    structured_base: "str | Path",
) -> dict:
    """
    Locate structured_data/grade_N/module_N/topic_N/topic.md and parse it.

    Raises FileNotFoundError if the file does not exist (run --parse-raw first).
    """
    md_path = (
        Path(structured_base)
        / f"grade_{grade}"
        / f"module_{module_num}"
        / f"topic_{topic_num}"
        / "topic.md"
    )
    if not md_path.exists():
        raise FileNotFoundError(
            f"topic.md not found: {md_path}\n"
            "Run the pipeline with --parse-raw first to generate structured_data/."
        )
    return parse_topic_md(md_path)
