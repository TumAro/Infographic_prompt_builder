"""book_md_adapter.py

Converts Book Writer `topic_M.T.md` files into the pipeline's internal
`topic.md` format used by structured_data/.

No LLM calls are made — this is a pure text transformation.

Input location:  book_output/grade_N/module_M/topic_M.T.md
Output location: structured_data/grade_N/module_M/topic_T/topic.md

Usage
-----
    python book_md_adapter.py --file book_output/grade_8/module_1/topic_1.2.md
    python book_md_adapter.py --grade 8 --module 1
    python book_md_adapter.py --grade 8
    python book_md_adapter.py --force-adapt
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
BOOK_OUTPUT_DIR = ROOT / "book_output"
STRUCTURED_DIR = ROOT / "structured_data"

# Separator: three or more dashes on a line by themselves
_SEP_RE = re.compile(r"^-{3,}\s*$")


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def _parse_frontmatter(lines: list[str]) -> tuple[dict[str, str], list[str]]:
    """Strip and parse the YAML frontmatter block.

    Returns (fields, remaining_lines).  If no frontmatter is found the fields
    dict is empty and all lines are returned as-is.
    """
    if not lines or lines[0].strip() != "---":
        return {}, lines

    fields: dict[str, str] = {}
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()

    if end_idx is None:
        # Malformed frontmatter — return everything
        return fields, lines

    return fields, lines[end_idx + 1 :]


def _split_em_dash(value: str) -> tuple[str, str]:
    """Split a frontmatter value on ' \u2014 ' (em-dash) or ' - ' (hyphen fallback).

    Returns (left, right).  If no separator is found returns (value, "").
    """
    # Try em-dash first
    em_dash = "\u2014"
    if f" {em_dash} " in value:
        left, _, right = value.partition(f" {em_dash} ")
        return left.strip(), right.strip()
    # Hyphen fallback — only split on " - " to avoid false positives
    if " - " in value:
        left, _, right = value.partition(" - ")
        return left.strip(), right.strip()
    return value.strip(), ""


def _extract_metadata(fields: dict[str, str]) -> tuple[int, int, str, int, str]:
    """Return (grade, module_num, module_name, topic_num, topic_name)."""
    grade = int(fields.get("grade", 0))

    module_raw = fields.get("module", "")
    module_left, module_name = _split_em_dash(module_raw)
    try:
        module_num = int(module_left)
    except ValueError:
        module_num = 0

    topic_raw = fields.get("topic", "")
    topic_left, topic_name = _split_em_dash(topic_raw)
    # topic_left is like "1.2" — take the part after the dot
    parts = topic_left.split(".")
    try:
        topic_num = int(parts[1]) if len(parts) >= 2 else int(parts[0])
    except (ValueError, IndexError):
        topic_num = 0

    return grade, module_num, module_name, topic_num, topic_name


# ---------------------------------------------------------------------------
# Line-by-line state machine
# ---------------------------------------------------------------------------

class _State:
    NORMAL = "normal"
    WORKED_EXAMPLE = "worked_example"
    IMAGE_DESC = "image_desc"
    IMAGE_CAPTION = "image_caption"
    DID_YOU_KNOW = "did_you_know"
    THINK_REFLECT = "think_reflect"
    KEY_TERMS = "key_terms"
    PRACTICE = "practice"


def _convert_body(lines: list[str]) -> list[str]:
    """Transform body lines (after frontmatter) into topic.md format."""
    out: list[str] = []
    figure_counter = 0
    state = _State.NORMAL

    # Pending data for multi-line constructs
    pending_image_desc: str = ""
    pending_did_you_know: bool = False
    pending_think_reflect: bool = False
    pending_key_terms: bool = False
    pending_practice: bool = False

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip("\n")
        stripped = line.strip()

        # ------------------------------------------------------------------
        # Detect block-start keywords (before state dispatch)
        # ------------------------------------------------------------------

        # H1 — strip numeric prefix like "1.2 "
        if re.match(r"^#\s+\d+\.\d+\s+", line):
            # e.g. "# 1.2 Variables and Data Types"
            title = re.sub(r"^#\s+\d+\.\d+\s+", "", line)
            out.append(f"# Topic: {title}")
            state = _State.NORMAL
            i += 1
            continue

        # H3 Worked Example — must come before generic H3 check
        if re.match(r"^###\s+Worked Example:", line):
            figure_counter += 1
            heading_text = re.sub(r"^###\s+", "", line)
            out.append(f"> **[Code Figure {figure_counter}]** {heading_text}")
            state = _State.WORKED_EXAMPLE
            i += 1
            continue

        # H2 resets worked-example state and converts to subtopic heading
        if re.match(r"^##\s+", line) and not re.match(r"^###", line):
            state = _State.NORMAL
            subtopic = re.sub(r"^##\s+", "", line)
            out.append(f"## Subtopic: {subtopic}")
            i += 1
            continue

        # H3 other (not Worked Example) — treat as normal heading passthrough
        if re.match(r"^###\s+", line):
            state = _State.NORMAL
            out.append(line)
            i += 1
            continue

        # ------------------------------------------------------------------
        # Worked Example body: skip all lines until next ##/###
        # ------------------------------------------------------------------
        if state == _State.WORKED_EXAMPLE:
            if re.match(r"^#{2,3}\s+", line):
                # Reprocess this line without consuming it
                state = _State.NORMAL
                continue  # do NOT increment i
            # Skip body lines of the worked example block
            i += 1
            continue

        # ------------------------------------------------------------------
        # [IMAGE] block
        # ------------------------------------------------------------------
        if stripped == "[IMAGE]":
            state = _State.IMAGE_DESC
            pending_image_desc = ""
            i += 1
            continue

        if state == _State.IMAGE_DESC:
            if stripped.startswith("Description:"):
                pending_image_desc = stripped[len("Description:"):].strip()
                state = _State.IMAGE_CAPTION
            else:
                # Unexpected line — abandon image block
                state = _State.NORMAL
                out.append(line)
            i += 1
            continue

        if state == _State.IMAGE_CAPTION:
            if stripped.startswith("Caption:"):
                caption = stripped[len("Caption:"):].strip()
                figure_counter += 1
                out.append(f"> **[Figure {figure_counter}]** {pending_image_desc}")
                out.append(f"> *Caption: {caption}*")
            else:
                # No caption line — emit figure without caption and reprocess
                figure_counter += 1
                out.append(f"> **[Figure {figure_counter}]** {pending_image_desc}")
                state = _State.NORMAL
                # Reprocess current line
                continue
            state = _State.NORMAL
            i += 1
            continue

        # ------------------------------------------------------------------
        # "Did You Know?" block
        # ------------------------------------------------------------------
        if stripped == "Did You Know?":
            pending_did_you_know = True
            i += 1
            continue

        if pending_did_you_know:
            if _SEP_RE.match(stripped):
                # Next non-empty line(s) are the fact text
                state = _State.DID_YOU_KNOW
                pending_did_you_know = False
                i += 1
                continue
            else:
                # Not followed by separator — emit as plain text
                pending_did_you_know = False
                out.append("Did You Know?")
                out.append(line)
                i += 1
                continue

        if state == _State.DID_YOU_KNOW:
            if stripped == "" or _SEP_RE.match(stripped):
                # End of fact block
                state = _State.NORMAL
                i += 1
                continue
            out.append(f"> **Fun Fact:** {stripped}")
            state = _State.NORMAL
            i += 1
            continue

        # ------------------------------------------------------------------
        # "Think & Reflect" block
        # ------------------------------------------------------------------
        if stripped == "Think & Reflect":
            pending_think_reflect = True
            i += 1
            continue

        if pending_think_reflect:
            if _SEP_RE.match(stripped):
                state = _State.THINK_REFLECT
                pending_think_reflect = False
                i += 1
                continue
            else:
                pending_think_reflect = False
                out.append("Think & Reflect")
                out.append(line)
                i += 1
                continue

        if state == _State.THINK_REFLECT:
            if stripped == "" or _SEP_RE.match(stripped):
                state = _State.NORMAL
                i += 1
                continue
            out.append(f"> **Activity:** {stripped}")
            state = _State.NORMAL
            i += 1
            continue

        # ------------------------------------------------------------------
        # "Key Terms" block
        # ------------------------------------------------------------------
        if stripped == "Key Terms":
            pending_key_terms = True
            i += 1
            continue

        if pending_key_terms:
            if _SEP_RE.match(stripped):
                state = _State.KEY_TERMS
                pending_key_terms = False
                i += 1
                continue
            else:
                pending_key_terms = False
                out.append("Key Terms")
                out.append(line)
                i += 1
                continue

        if state == _State.KEY_TERMS:
            if stripped == "" or _SEP_RE.match(stripped):
                state = _State.NORMAL
                i += 1
                continue
            # Expect "Term: definition"
            if ":" in stripped:
                term, _, definition = stripped.partition(":")
                out.append(f"- **{term.strip()}**: {definition.strip()}")
            else:
                out.append(f"- {stripped}")
            i += 1
            continue

        # ------------------------------------------------------------------
        # "Practice Problems" block
        # ------------------------------------------------------------------
        if stripped == "Practice Problems":
            pending_practice = True
            i += 1
            continue

        if pending_practice:
            if _SEP_RE.match(stripped):
                state = _State.PRACTICE
                pending_practice = False
                i += 1
                continue
            else:
                pending_practice = False
                out.append("Practice Problems")
                out.append(line)
                i += 1
                continue

        if state == _State.PRACTICE:
            if stripped == "" or _SEP_RE.match(stripped):
                state = _State.NORMAL
                i += 1
                continue
            # Keep numbered lines verbatim
            out.append(line)
            i += 1
            continue

        # ------------------------------------------------------------------
        # Standalone separator lines in NORMAL state — pass through
        # ------------------------------------------------------------------
        if _SEP_RE.match(stripped) and state == _State.NORMAL:
            out.append(line)
            i += 1
            continue

        # ------------------------------------------------------------------
        # Default: emit line verbatim
        # ------------------------------------------------------------------
        out.append(line)
        i += 1

    return out


# ---------------------------------------------------------------------------
# Core adapt_file function
# ---------------------------------------------------------------------------

def adapt_file(
    file_path: str | Path,
    structured_base: str | Path = STRUCTURED_DIR,
    force: bool = False,
) -> Path | None:
    """Convert a single Book Writer topic file to topic.md format.

    Parameters
    ----------
    file_path:
        Path to the input ``topic_M.T.md`` file.
    structured_base:
        Root of the ``structured_data/`` tree.
    force:
        If True, overwrite an existing ``topic.md``.

    Returns
    -------
    Path to the written ``topic.md``, or None if skipped.
    """
    file_path = Path(file_path)
    structured_base = Path(structured_base)

    raw_lines = file_path.read_text(encoding="utf-8").splitlines(keepends=False)

    fields, body_lines = _parse_frontmatter(raw_lines)
    if not fields:
        print(f"[WARN] No frontmatter found in {file_path}; skipping.", file=sys.stderr)
        return None

    try:
        grade, module_num, _module_name, topic_num, _topic_name = _extract_metadata(fields)
    except Exception as exc:
        print(f"[WARN] Could not parse frontmatter in {file_path}: {exc}", file=sys.stderr)
        return None

    out_dir = structured_base / f"grade_{grade}" / f"module_{module_num}" / f"topic_{topic_num}"
    out_path = out_dir / "topic.md"

    if out_path.exists() and not force:
        print(f"[SKIP] topic.md already exists for topic {module_num}.{topic_num}")
        return None

    converted = _convert_body(body_lines)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(converted) + "\n", encoding="utf-8")
    print(f"[DONE] Wrote {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Batch helpers
# ---------------------------------------------------------------------------

def adapt_module(
    grade: int,
    module_num: int,
    book_output_base: str | Path = BOOK_OUTPUT_DIR,
    structured_base: str | Path = STRUCTURED_DIR,
    force: bool = False,
) -> list[Path]:
    """Adapt all topic files within a single module.

    Globs ``book_output/grade_{N}/module_{M}/topic_*.md``.
    """
    book_output_base = Path(book_output_base)
    module_dir = book_output_base / f"grade_{grade}" / f"module_{module_num}"
    topic_files = sorted(module_dir.glob("topic_*.md"))
    results: list[Path] = []
    for f in topic_files:
        result = adapt_file(f, structured_base=structured_base, force=force)
        if result is not None:
            results.append(result)
    return results


def adapt_grade(
    grade: int,
    book_output_base: str | Path = BOOK_OUTPUT_DIR,
    structured_base: str | Path = STRUCTURED_DIR,
    force: bool = False,
) -> list[Path]:
    """Adapt all topic files across all modules for a grade.

    Globs ``book_output/grade_{N}/module_*/topic_*.md``.
    """
    book_output_base = Path(book_output_base)
    grade_dir = book_output_base / f"grade_{grade}"
    topic_files = sorted(grade_dir.glob("module_*/topic_*.md"))
    results: list[Path] = []
    for f in topic_files:
        result = adapt_file(f, structured_base=structured_base, force=force)
        if result is not None:
            results.append(result)
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert Book Writer topic_M.T.md files to pipeline topic.md format.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--file",
        metavar="PATH",
        help="Adapt a single topic file (e.g. book_output/grade_8/module_1/topic_1.2.md).",
    )
    group.add_argument(
        "--grade",
        type=int,
        metavar="N",
        help="Adapt all modules for a grade (requires --module for single-module scope).",
    )
    parser.add_argument(
        "--module",
        type=int,
        metavar="M",
        help="When combined with --grade, adapt only this module number.",
    )
    parser.add_argument(
        "--force-adapt",
        action="store_true",
        help="Overwrite existing topic.md files.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    force = args.force_adapt

    if args.file:
        adapt_file(args.file, force=force)
    elif args.grade is not None and args.module is not None:
        adapt_module(args.grade, args.module, force=force)
    elif args.grade is not None:
        adapt_grade(args.grade, force=force)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
