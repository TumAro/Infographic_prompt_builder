"""
resolver.py — No LLM; merges content JSON + style configs → page_N_final.json.

Replaces all {{global.key}} and {{grade.key}} tokens with values from
configs/global_style.json and configs/grade_N_style.json.
Safe to re-run after config edits without regenerating LLM outputs.

Usage:
    python resolver.py --grade 6 --module 1 --topic 2
    python resolver.py --grade 6 --module 1
    python resolver.py --grade 6
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent

_TOKEN_RE = re.compile(r"\{\{(\w+)\.(\w+)\}\}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_configs(grade: int):
    """Return (global_cfg, grade_cfg) dicts for the given grade."""
    global_cfg = json.loads(
        (ROOT / "configs" / "global_style.json").read_text(encoding="utf-8")
    )
    grade_cfg = json.loads(
        (ROOT / "configs" / f"grade_{grade}_style.json").read_text(encoding="utf-8")
    )
    return global_cfg, grade_cfg


def _resolve_string(text: str, global_cfg: dict, grade_cfg: dict) -> str:
    """Replace every {{namespace.key}} token in text; raise ValueError for unknown tokens."""
    def _sub(m):
        ns, key = m.group(1), m.group(2)
        if ns == "global":
            if key not in global_cfg:
                raise ValueError(f"Unknown token: {{{{global.{key}}}}}")
            return global_cfg[key]
        if ns == "grade":
            if key not in grade_cfg:
                raise ValueError(f"Unknown token: {{{{grade.{key}}}}}")
            return grade_cfg[key]
        raise ValueError(f"Unknown token: {{{{{ns}.{key}}}}}")

    return _TOKEN_RE.sub(_sub, text)


def _resolve_value(value, global_cfg: dict, grade_cfg: dict):
    """Recursively resolve tokens in any JSON-compatible value."""
    if isinstance(value, str):
        return _resolve_string(value, global_cfg, grade_cfg)
    if isinstance(value, dict):
        return {k: _resolve_value(v, global_cfg, grade_cfg) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_value(item, global_cfg, grade_cfg) for item in value]
    return value  # int, float, bool, None — pass through unchanged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_topic(grade: int, module: int, topic: int) -> list:
    """
    Resolve all page_N_content.json files for one topic → page_N_final.json.

    Always runs (no skip logic). Safe to re-run after config edits.

    Injects `grade`, `module`, and `synopsis` into each resolved page.
    `synopsis` is extracted from the ## Synopsis section of gist.md in the
    same topic directory; it is left as an empty string if gist.md is absent.

    Args:
        grade:  Grade number (e.g. 6).
        module: Module number (1-indexed).
        topic:  Topic number (1-indexed).

    Returns:
        List of absolute path strings for each page_N_final.json written.
    """
    global_cfg, grade_cfg = _load_configs(grade)
    topic_dir = (
        ROOT / "output" / f"grade_{grade}" / f"module_{module}" / f"topic_{topic}"
    )

    # Extract synopsis from gist.md once per topic (before the page loop)
    synopsis = ""
    gist_path = topic_dir / "gist.md"
    if gist_path.exists():
        gist_text = gist_path.read_text(encoding="utf-8")
        m = re.search(
            r"##\s+Synopsis\s*\n+(.*?)(?:\n\s*##|\Z)",
            gist_text,
            re.DOTALL | re.IGNORECASE,
        )
        if m:
            synopsis = m.group(1).strip()

    written = []
    n = 1
    while True:
        content_path = topic_dir / f"page_{n}_content.json"
        if not content_path.exists():
            break
        data = json.loads(content_path.read_text(encoding="utf-8"))
        resolved = _resolve_value(data, global_cfg, grade_cfg)
        resolved["grade"] = grade
        resolved["module"] = module
        resolved["synopsis"] = synopsis
        final_path = topic_dir / f"page_{n}_final.json"
        final_path.write_text(
            json.dumps(resolved, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        written.append(str(final_path))
        n += 1

    return written


def resolve_module(grade: int, module: int) -> list:
    """Resolve all topics in a module. Returns all written final.json paths."""
    module_dir = ROOT / "output" / f"grade_{grade}" / f"module_{module}"
    if not module_dir.exists():
        return []
    written = []
    for topic_dir in sorted(module_dir.iterdir()):
        if topic_dir.is_dir() and topic_dir.name.startswith("topic_"):
            try:
                topic_num = int(topic_dir.name.split("_")[1])
            except (IndexError, ValueError):
                continue
            written.extend(resolve_topic(grade, module, topic_num))
    return written


def resolve_grade(grade: int) -> list:
    """Resolve all modules and topics for a grade. Returns all written final.json paths."""
    grade_dir = ROOT / "output" / f"grade_{grade}"
    if not grade_dir.exists():
        return []
    written = []
    for module_dir in sorted(grade_dir.iterdir()):
        if module_dir.is_dir() and module_dir.name.startswith("module_"):
            try:
                module_num = int(module_dir.name.split("_")[1])
            except (IndexError, ValueError):
                continue
            written.extend(resolve_module(grade, module_num))
    return written


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Resolve style tokens in page_N_content.json → page_N_final.json."
    )
    parser.add_argument("--grade", type=int, required=True, help="Grade number (e.g. 6)")
    parser.add_argument("--module", type=int, help="Module number (1-indexed)")
    parser.add_argument("--topic", type=int, help="Topic number (1-indexed)")
    args = parser.parse_args()

    if args.topic is not None and args.module is None:
        parser.error("--topic requires --module")

    if args.topic is not None:
        paths = resolve_topic(args.grade, args.module, args.topic)
    elif args.module is not None:
        paths = resolve_module(args.grade, args.module)
    else:
        paths = resolve_grade(args.grade)

    for p in paths:
        print(f"Resolved: {p}")

    if not paths:
        print("No content files found to resolve.")
