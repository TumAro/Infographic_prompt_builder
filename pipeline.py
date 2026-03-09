"""
pipeline.py — CLI orchestrator for the AI Infographic Picture Book Generator.

Usage:
    python pipeline.py                                    # all grades
    python pipeline.py --grade 6                          # all modules in grade
    python pipeline.py --grade 6 --module 1               # all topics in module
    python pipeline.py --grade 6 --module 1 --topic 2     # single topic

Skip logic:
    - gist.md exists             → skip gist_llm  (override: --force-gist)
    - page_N_content.json exists → skip prompt_llm (override: --force-prompt)
    - resolver always runs
"""

import argparse
import re
import traceback
from pathlib import Path

import doc_parser
import gist_llm
import prompt_llm
import resolver

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"


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
    modules = set()
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
) -> dict:
    """
    Run the full pipeline for a single topic.

    Returns:
        {"grade": N, "module": M, "topic": T, "pages": N, "error": None | str}
    """
    result = {"grade": grade, "module": module, "topic": topic, "pages": 0, "error": None}

    try:
        syllabus_path = _find_syllabus(grade)
        module_path = _find_module_file(grade, module)
        output_path = OUTPUT_DIR / f"grade_{grade}" / f"module_{module}" / f"topic_{topic}"
        output_path.mkdir(parents=True, exist_ok=True)

        # Step 1: Parse topic content
        topic_content = doc_parser.get_topic_content(
            module_path=module_path,
            syllabus_path=syllabus_path,
            module_num=module,
            topic_num=topic,
        )

        # Step 2: Generate gist.md
        gist_exists = (output_path / "gist.md").exists()
        if force_gist and gist_exists:
            _force_clear_gist(output_path)
            print(f"    [force-gist] deleted existing gist.md")
        elif gist_exists:
            print(f"    [skip] gist.md already exists")

        gist_text = gist_llm.generate_gist(topic_content, grade, output_path)

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

def run_module(grade: int, module: int, force_gist: bool, force_prompt: bool) -> list:
    topic_nums = _discover_topics(grade, module)
    results = []
    for topic_num in topic_nums:
        print(f"  Topic {topic_num}...")
        r = run_topic(grade, module, topic_num, force_gist, force_prompt)
        results.append(r)
    return results


def run_grade(grade: int, force_gist: bool, force_prompt: bool) -> list:
    module_nums = _discover_modules(grade)
    results = []
    for module_num in module_nums:
        print(f"Module {module_num}...")
        results.extend(run_module(grade, module_num, force_gist, force_prompt))
    return results


def run_all(force_gist: bool, force_prompt: bool) -> list:
    grades = _discover_grades()
    results = []
    for grade in grades:
        print(f"Grade {grade}...")
        results.extend(run_grade(grade, force_gist, force_prompt))
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
        "--force-gist",
        action="store_true",
        help="Regenerate gist.md even if it already exists",
    )
    parser.add_argument(
        "--force-prompt",
        action="store_true",
        help="Regenerate page_N_content.json even if it already exists",
    )
    args = parser.parse_args()

    if args.topic is not None and args.module is None:
        parser.error("--topic requires --module")
    if args.module is not None and args.grade is None:
        parser.error("--module requires --grade")

    force_gist = args.force_gist
    force_prompt = args.force_prompt

    if args.topic is not None:
        topic_content = doc_parser.get_topic_content(
            module_path=_find_module_file(args.grade, args.module),
            syllabus_path=_find_syllabus(args.grade),
            module_num=args.module,
            topic_num=args.topic,
        )
        print(
            f"Grade {args.grade} / Module {args.module} / Topic {args.topic}"
            f" — {topic_content['topic']}"
        )
        results = [run_topic(args.grade, args.module, args.topic, force_gist, force_prompt)]

    elif args.module is not None:
        print(f"Grade {args.grade} / Module {args.module}")
        results = run_module(args.grade, args.module, force_gist, force_prompt)

    elif args.grade is not None:
        print(f"Grade {args.grade}")
        results = run_grade(args.grade, force_gist, force_prompt)

    else:
        results = run_all(force_gist, force_prompt)

    # Summary
    total = len(results)
    succeeded = sum(1 for r in results if r["error"] is None)
    total_pages = sum(r["pages"] for r in results)
    errors = [r for r in results if r["error"] is not None]

    print()
    print("=" * 60)
    print("SUMMARY")
    print(f"  Topics attempted : {total}")
    print(f"  Topics succeeded : {succeeded}")
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
