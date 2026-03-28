"""
pipeline.py — CLI orchestrator for the AI Infographic Picture Book Generator.

Two-phase pipeline:
    Phase 1 (parse):    doc_parser → structured_data/grade_N/module_N/topic_N/topic.md
    Phase 2 (generate): md_parser  → gist_llm → prompt_llm → resolver

Usage:
    # Parse phase only (build structured_data/)
    python pipeline.py --parse-raw
    python pipeline.py --parse-raw --grade 6 --module 1 --topic 1
    python pipeline.py --parse-raw --force-parse   # overwrite existing topic.md files

    # Generate phase (structured_data/ must already exist)
    python pipeline.py --grade 6 --module 1 --topic 1
    python pipeline.py --grade 6 --module 1
    python pipeline.py --grade 6
    python pipeline.py                              # all grades

    # Re-resolve after config edits (no LLM)
    python resolver.py --grade 6 --module 1 --topic 2

Skip logic (generate mode):
    - topic.md missing        → error (run --parse-raw first)
    - gist.md exists          → skip gist_llm  (override: --force-gist)
    - page_N_content.json exists → skip prompt_llm (override: --force-prompt)
    - resolver always runs
"""

import argparse
import re
import traceback
from pathlib import Path

import doc_parser
import gist_llm
import md_parser
import prompt_llm
import resolver

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
STRUCTURED_DIR = ROOT / "structured_data"


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def _find_syllabus(grade: int) -> Path:
    p = DATA_DIR / f"grade_{grade}" / f"Class_{grade}.docx"
    if not p.exists():
        raise FileNotFoundError(f"Syllabus not found: {p}")
    return p


def _find_module_file(grade: int, module_num: int) -> Path:
    grade_dir = DATA_DIR / f"grade_{grade}"
    matches = list(grade_dir.glob(f"Module_{module_num}_*.docx"))
    if not matches:
        raise FileNotFoundError(
            f"No module file matching Module_{module_num}_*.docx in {grade_dir}"
        )
    return matches[0]


def _discover_grades() -> list:
    grades = []
    for d in DATA_DIR.iterdir():
        if d.is_dir():
            m = re.match(r"grade_(\d+)$", d.name)
            if m:
                grades.append(int(m.group(1)))
    return sorted(grades)


def _discover_modules(grade: int) -> list:
    grade_dir = DATA_DIR / f"grade_{grade}"
    modules: set[int] = set()
    for f in grade_dir.glob("Module_*.docx"):
        m = re.match(r"Module_(\d+)_", f.name)
        if m:
            modules.add(int(m.group(1)))
    return sorted(modules)


def _discover_topics(grade: int, module_num: int) -> list:
    syllabus_path = _find_syllabus(grade)
    syllabus = doc_parser.parse_syllabus(syllabus_path)
    module_entry = next(
        (m for m in syllabus["modules"] if m["module_num"] == module_num), None
    )
    if module_entry is None:
        raise ValueError(f"Module {module_num} not found in grade {grade} syllabus")
    return sorted(t["topic_num"] for t in module_entry["topics"])


# ---------------------------------------------------------------------------
# Force-clear helpers
# ---------------------------------------------------------------------------

def _force_clear_gist(output_path: Path) -> None:
    p = output_path / "gist.md"
    if p.exists():
        p.unlink()


def _force_clear_content_jsons(output_path: Path) -> None:
    for p in output_path.glob("page_*_content.json"):
        p.unlink()


# ---------------------------------------------------------------------------
# Core: single topic
# ---------------------------------------------------------------------------

def run_topic(
    grade: int,
    module: int,
    topic: int,
    force_gist: bool = False,
    force_prompt: bool = False,
    gist_only: bool = False,
    parse_raw: bool = False,
    force_parse: bool = False,
) -> dict:
    """
    Run the pipeline for a single topic.

    In parse_raw mode: writes structured_data/grade_N/module_N/topic_N/topic.md
    In generate mode:  reads from structured_data/ and runs gist_llm → prompt_llm → resolver

    Returns:
        {
            "grade": N, "module": M, "topic": T,
            "pages": N,       # 0 in parse_raw mode
            "skipped": bool,  # True if topic.md/gist.md already existed and was reused
            "error": None | str
        }
    """
    result: dict = {
        "grade": grade, "module": module, "topic": topic,
        "pages": 0, "skipped": False, "error": None,
    }

    try:
        # ------------------------------------------------------------------
        # PARSE PHASE
        # ------------------------------------------------------------------
        if parse_raw:
            syllabus_path = _find_syllabus(grade)
            module_path = _find_module_file(grade, module)
            out = doc_parser.write_topic_md(
                module_path=module_path,
                syllabus_path=syllabus_path,
                module_num=module,
                topic_num=topic,
                structured_base=STRUCTURED_DIR,
                grade=grade,
                force=force_parse,
            )
            if out is None:
                print(f"    [skip] topic.md already exists")
                result["skipped"] = True
            else:
                print(f"    -> written: {out.relative_to(ROOT)}")
            return result

        # ------------------------------------------------------------------
        # GENERATE PHASE
        # ------------------------------------------------------------------
        output_path = OUTPUT_DIR / f"grade_{grade}" / f"module_{module}" / f"topic_{topic}"
        output_path.mkdir(parents=True, exist_ok=True)

        # Step 1: Locate topic.md in structured_data/
        topic_md_path = (
            STRUCTURED_DIR
            / f"grade_{grade}"
            / f"module_{module}"
            / f"topic_{topic}"
            / "topic.md"
        )

        # Step 2: Generate gist.md (one LLM call per subtopic)
        gist_path = output_path / "gist.md"
        gist_exists = gist_path.exists()
        if force_gist and gist_exists:
            _force_clear_gist(output_path)
            print(f"    [force-gist] deleted existing gist.md")
            gist_exists = False
        elif gist_exists:
            print(f"    [skip] gist.md already exists")

        if gist_exists:
            gist_text = gist_path.read_text(encoding="utf-8")
        else:
            sections = []
            topic_name = None
            for t_name, sub_name, sub_raw in md_parser.iter_subtopics(topic_md_path):
                topic_name = t_name
                print(f"      [gist] subtopic: {sub_name}")
                section = gist_llm.generate_subtopic_gist(t_name, sub_name, sub_raw, grade)
                sections.append(section)
            gist_text = f"# {topic_name}\n\n" + "\n\n---\n\n".join(sections)
            gist_path.write_text(gist_text, encoding="utf-8")

        if gist_only:
            print(f"    [gist-only] skipping prompt generation and resolver")
            return result

        # Step 3: Generate page_N_content.json
        prompt_exists = (output_path / "page_1_content.json").exists()
        if force_prompt and prompt_exists:
            _force_clear_content_jsons(output_path)
            print(f"    [force-prompt] deleted existing page_*_content.json")
        elif prompt_exists:
            print(f"    [skip] page_1_content.json already exists")

        prompt_llm.generate_content_jsons(gist_text, grade, module, topic, output_path)

        # Step 4: Resolve tokens (always runs)
        final_paths = resolver.resolve_topic(grade, module, topic)
        result["pages"] = len(final_paths)
        print(f"    -> {len(final_paths)} page(s) resolved")

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        traceback.print_exc()

    return result


# ---------------------------------------------------------------------------
# Scope runners
# ---------------------------------------------------------------------------

def run_module(
    grade: int,
    module: int,
    force_gist: bool,
    force_prompt: bool,
    gist_only: bool = False,
    parse_raw: bool = False,
    force_parse: bool = False,
) -> list:
    topic_nums = _discover_topics(grade, module)
    results = []
    for topic_num in topic_nums:
        print(f"  Topic {topic_num}...")
        r = run_topic(
            grade, module, topic_num,
            force_gist, force_prompt, gist_only,
            parse_raw, force_parse,
        )
        results.append(r)
    return results


def run_grade(
    grade: int,
    force_gist: bool,
    force_prompt: bool,
    gist_only: bool = False,
    parse_raw: bool = False,
    force_parse: bool = False,
) -> list:
    module_nums = _discover_modules(grade)
    results = []
    for module_num in module_nums:
        print(f"Module {module_num}...")
        results.extend(
            run_module(grade, module_num, force_gist, force_prompt, gist_only, parse_raw, force_parse)
        )
    return results


def run_all(
    force_gist: bool,
    force_prompt: bool,
    gist_only: bool = False,
    parse_raw: bool = False,
    force_parse: bool = False,
) -> list:
    grades = _discover_grades()
    results = []
    for grade in grades:
        print(f"Grade {grade}...")
        results.extend(
            run_grade(grade, force_gist, force_prompt, gist_only, parse_raw, force_parse)
        )
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Infographic Picture Book pipeline orchestrator."
    )
    parser.add_argument("--grade", type=int, help="Grade number (e.g. 6)")
    parser.add_argument("--module", type=int, help="Module number (1-indexed)")
    parser.add_argument("--topic", type=int, help="Topic number (1-indexed)")
    parser.add_argument(
        "--parse-raw",
        action="store_true",
        help="Run only the doc_parser phase (build structured_data/), then stop",
    )
    parser.add_argument(
        "--force-parse",
        action="store_true",
        help="Overwrite existing topic.md files during --parse-raw",
    )
    parser.add_argument(
        "--force-gist",
        action="store_true",
        help="Regenerate gist.md even if it already exists",
    )
    parser.add_argument(
        "--force-prompt",
        action="store_true",
        help="Regenerate page_N_content.json even if it already exists",
    )
    parser.add_argument(
        "--gist-only",
        action="store_true",
        help="Generate only gist.md; skip prompt_llm and resolver",
    )
    args = parser.parse_args()

    if args.topic is not None and args.module is None:
        parser.error("--topic requires --module")
    if args.module is not None and args.grade is None:
        parser.error("--module requires --grade")

    parse_raw = args.parse_raw
    force_parse = args.force_parse
    force_gist = args.force_gist
    force_prompt = args.force_prompt
    gist_only = args.gist_only

    mode_label = "PARSE" if parse_raw else "GENERATE"

    if args.topic is not None:
        # Print topic name from syllabus (no full parse required)
        try:
            syllabus = doc_parser.parse_syllabus(_find_syllabus(args.grade))
            mod_entry = next(
                (m for m in syllabus["modules"] if m["module_num"] == args.module), None
            )
            topic_name = ""
            if mod_entry:
                t_entry = next(
                    (t for t in mod_entry["topics"] if t["topic_num"] == args.topic), None
                )
                if t_entry:
                    topic_name = f" — {t_entry['name']}"
        except Exception:
            topic_name = ""

        print(
            f"[{mode_label}] Grade {args.grade} / Module {args.module}"
            f" / Topic {args.topic}{topic_name}"
        )
        results = [
            run_topic(
                args.grade, args.module, args.topic,
                force_gist, force_prompt, gist_only,
                parse_raw, force_parse,
            )
        ]

    elif args.module is not None:
        print(f"[{mode_label}] Grade {args.grade} / Module {args.module}")
        results = run_module(
            args.grade, args.module,
            force_gist, force_prompt, gist_only,
            parse_raw, force_parse,
        )

    elif args.grade is not None:
        print(f"[{mode_label}] Grade {args.grade}")
        results = run_grade(
            args.grade, force_gist, force_prompt, gist_only, parse_raw, force_parse
        )

    else:
        print(f"[{mode_label}] All grades")
        results = run_all(force_gist, force_prompt, gist_only, parse_raw, force_parse)

    # Summary
    total = len(results)
    succeeded = sum(1 for r in results if r["error"] is None)
    skipped = sum(1 for r in results if r.get("skipped"))
    total_pages = sum(r["pages"] for r in results)
    errors = [r for r in results if r["error"] is not None]

    print()
    print("=" * 60)
    print("SUMMARY")
    print(f"  Mode             : {'parse-raw' if parse_raw else 'generate'}")
    print(f"  Topics attempted : {total}")
    print(f"  Topics succeeded : {succeeded}")
    print(f"  Topics skipped   : {skipped}")
    if not parse_raw and not gist_only:
        print(f"  Pages generated  : {total_pages}")
    print(f"  Errors           : {len(errors)}")

    if errors:
        print()
        print("Failed topics:")
        for r in errors:
            print(
                f"  grade {r['grade']} / module {r['module']} / topic {r['topic']}"
                f" — {r['error']}"
            )

    print("=" * 60)
