"""
pipeline.py — CLI orchestrator for the AI Infographic Picture Book Generator.

Two-phase pipeline:
    Phase 1 (parse):    doc_parser → structured_data/grade_N/module_N/topic_N/topic.md
    Phase 2 (generate): md_parser  → plan_llm → prompt_llm → resolver

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
    - plan.md exists          → skip plan_llm  (override: --force-plan)
    - page_N_content.json exists → skip prompt_llm (override: --force-prompt)
    - resolver always runs
"""

import argparse
import re
import traceback
from pathlib import Path

import doc_parser
import plan_llm
import md_parser
import prompt_llm
import resolver
import book_md_adapter

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
STRUCTURED_DIR = ROOT / "structured_data"
BOOK_OUTPUT_DIR = ROOT / "book_output"


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

def _force_clear_plan(output_path: Path) -> None:
    p = output_path / "plan.md"
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
    force_plan: bool = False,
    force_prompt: bool = False,
    plan_only: bool = False,
    parse_raw: bool = False,
    force_parse: bool = False,
    target_pages: set | None = None,
) -> dict:
    """
    Run the pipeline for a single topic.

    In parse_raw mode: writes structured_data/grade_N/module_N/topic_N/topic.md
    In generate mode:  reads from structured_data/ and runs plan_llm → prompt_llm → resolver

    Returns:
        {
            "grade": N, "module": M, "topic": T,
            "pages": N,       # 0 in parse_raw mode
            "skipped": bool,  # True if topic.md/plan.md already existed and was reused
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

        # Step 2: Generate plan.md (cumulative LLM call per subtopic)
        plan_path = output_path / "plan.md"
        plan_exists = plan_path.exists()
        if force_plan and plan_exists:
            _force_clear_plan(output_path)
            print(f"    [force-plan] deleted existing plan.md")
            plan_exists = False
        elif plan_exists:
            print(f"    [skip] plan.md already exists")

        if plan_exists:
            plan_text = plan_path.read_text(encoding="utf-8")
        else:
            subtopics = []
            topic_name = None
            for t_name, sub_name, sub_raw in md_parser.iter_subtopics(topic_md_path):
                if topic_name is None:
                    topic_name = t_name
                subtopics.append((sub_name, sub_raw))
            plan_text = plan_llm.generate_topic_plan(topic_name, subtopics, grade)
            plan_path.write_text(plan_text, encoding="utf-8")

        if plan_only:
            print(f"    [plan-only] skipping prompt generation and resolver")
            return result

        # Step 3: Generate page_N_content.json
        if target_pages is not None:
            if force_prompt:
                for pn in target_pages:
                    p = output_path / f"page_{pn}_content.json"
                    if p.exists():
                        p.unlink()
                        print(f"    [force-prompt] deleted page_{pn}_content.json")
            prompt_llm.generate_content_jsons(
                plan_text, grade, module, topic, output_path, target_pages=target_pages
            )
        else:
            prompt_exists = (output_path / "page_1_content.json").exists()
            if force_prompt and prompt_exists:
                _force_clear_content_jsons(output_path)
                print(f"    [force-prompt] deleted existing page_*_content.json")
            elif prompt_exists:
                print(f"    [skip] page_1_content.json already exists")
            prompt_llm.generate_content_jsons(plan_text, grade, module, topic, output_path)

        # Step 4: Resolve tokens (always runs)
        final_paths = resolver.resolve_topic(grade, module, topic)
        result["pages"] = len(final_paths)
        print(f"    -> {len(final_paths)} page(s) resolved")

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        traceback.print_exc()

    return result


def run_topic_from_book(
    file_path: Path,
    force_adapt: bool = False,
    force_plan: bool = False,
    force_prompt: bool = False,
    plan_only: bool = False,
) -> dict:
    """
    Phase 0 + Phase 2 for a single Book Writer topic file.

    Runs book_md_adapter (Phase 0) to write topic.md to structured_data/,
    then runs the normal generate phase (plan_llm → prompt_llm → resolver).
    Grade/module/topic are inferred from the file's frontmatter — no CLI flags needed.
    """
    # Parse frontmatter to extract coordinates
    text = file_path.read_text(encoding="utf-8")
    raw_lines = text.splitlines()
    meta, _ = book_md_adapter._parse_frontmatter(raw_lines)
    if not meta:
        return {
            "grade": 0, "module": 0, "topic": 0,
            "pages": 0, "skipped": False,
            "error": f"No frontmatter found in {file_path}",
        }
    grade, module_num, _module_name, topic_num, _topic_name = book_md_adapter._extract_metadata(meta)

    print(f"  [book] Grade {grade} / Module {module_num} / Topic {module_num}.{topic_num}")

    # Phase 0: adapt
    book_md_adapter.adapt_file(file_path, force=force_adapt)

    # Phase 2: generate
    return run_topic(
        grade, module_num, topic_num,
        force_plan=force_plan,
        force_prompt=force_prompt,
        plan_only=plan_only,
        parse_raw=False,
        force_parse=False,
    )


# ---------------------------------------------------------------------------
# Scope runners
# ---------------------------------------------------------------------------

def run_module(
    grade: int,
    module: int,
    force_plan: bool,
    force_prompt: bool,
    plan_only: bool = False,
    parse_raw: bool = False,
    force_parse: bool = False,
) -> list:
    topic_nums = _discover_topics(grade, module)
    results = []
    for topic_num in topic_nums:
        print(f"  Topic {topic_num}...")
        r = run_topic(
            grade, module, topic_num,
            force_plan, force_prompt, plan_only,
            parse_raw, force_parse,
        )
        results.append(r)
    return results


def run_grade(
    grade: int,
    force_plan: bool,
    force_prompt: bool,
    plan_only: bool = False,
    parse_raw: bool = False,
    force_parse: bool = False,
) -> list:
    module_nums = _discover_modules(grade)
    results = []
    for module_num in module_nums:
        print(f"Module {module_num}...")
        results.extend(
            run_module(grade, module_num, force_plan, force_prompt, plan_only, parse_raw, force_parse)
        )
    return results


def run_all(
    force_plan: bool,
    force_prompt: bool,
    plan_only: bool = False,
    parse_raw: bool = False,
    force_parse: bool = False,
) -> list:
    grades = _discover_grades()
    results = []
    for grade in grades:
        print(f"Grade {grade}...")
        results.extend(
            run_grade(grade, force_plan, force_prompt, plan_only, parse_raw, force_parse)
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
        "--force-plan",
        action="store_true",
        help="Regenerate plan.md even if it already exists",
    )
    parser.add_argument(
        "--force-prompt",
        action="store_true",
        help="Regenerate page_N_content.json even if it already exists",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Generate only plan.md; skip prompt_llm and resolver",
    )
    parser.add_argument(
        "--from-book",
        metavar="PATH",
        help="Path to a Book Writer topic_M.T.md file or folder of such files",
    )
    parser.add_argument(
        "--force-adapt",
        action="store_true",
        help="Overwrite existing topic.md files when using --from-book",
    )
    parser.add_argument(
        "--page", type=int, action="append", dest="pages", metavar="N",
        help="Process only page N (repeatable: --page 3 --page 5). Requires --grade --module --topic.",
    )
    args = parser.parse_args()

    if args.topic is not None and args.module is None:
        parser.error("--topic requires --module")
    if args.module is not None and args.grade is None:
        parser.error("--module requires --grade")
    if args.pages and (args.grade is None or args.module is None or args.topic is None):
        parser.error("--page requires --grade, --module, and --topic")

    parse_raw = args.parse_raw
    force_parse = args.force_parse
    force_plan = args.force_plan
    force_prompt = args.force_prompt
    plan_only = args.plan_only
    force_adapt = getattr(args, 'force_adapt', False)
    target_pages = set(args.pages) if args.pages else None

    # ------------------------------------------------------------------
    # --from-book mode: Phase 0 (adapter) + Phase 2 (generate)
    # ------------------------------------------------------------------
    if args.from_book:
        from_book_path = Path(args.from_book)
        book_results = []

        if from_book_path.is_file():
            print(f"[BOOK] {from_book_path.name}")
            book_results.append(
                run_topic_from_book(
                    from_book_path,
                    force_adapt=force_adapt,
                    force_plan=force_plan,
                    force_prompt=force_prompt,
                    plan_only=plan_only,
                )
            )
        elif from_book_path.is_dir():
            files = sorted(from_book_path.rglob("topic_*.md"))
            if not files:
                print(f"[WARN] No topic_*.md files found in {from_book_path}")
            for f in files:
                print(f"[BOOK] {f.name}")
                book_results.append(
                    run_topic_from_book(
                        f,
                        force_adapt=force_adapt,
                        force_plan=force_plan,
                        force_prompt=force_prompt,
                        plan_only=plan_only,
                    )
                )
        else:
            print(f"[ERROR] --from-book path not found: {from_book_path}")
            raise SystemExit(1)

        # Print summary and exit — do not fall through to legacy mode
        total = len(book_results)
        succeeded = sum(1 for r in book_results if r["error"] is None)
        total_pages = sum(r["pages"] for r in book_results)
        errors = [r for r in book_results if r["error"] is not None]
        print()
        print("=" * 60)
        print("SUMMARY (book writer mode)")
        print(f"  Topics attempted : {total}")
        print(f"  Topics succeeded : {succeeded}")
        if not plan_only:
            print(f"  Pages generated  : {total_pages}")
        print(f"  Errors           : {len(errors)}")
        if errors:
            print()
            print("Failed topics:")
            for r in errors:
                print(f"  grade {r['grade']} / module {r['module']} / topic {r['topic']} — {r['error']}")
        print("=" * 60)
        raise SystemExit(0)

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
                force_plan, force_prompt, plan_only,
                parse_raw, force_parse,
                target_pages=target_pages,
            )
        ]

    elif args.module is not None:
        print(f"[{mode_label}] Grade {args.grade} / Module {args.module}")
        results = run_module(
            args.grade, args.module,
            force_plan, force_prompt, plan_only,
            parse_raw, force_parse,
        )

    elif args.grade is not None:
        print(f"[{mode_label}] Grade {args.grade}")
        results = run_grade(
            args.grade, force_plan, force_prompt, plan_only, parse_raw, force_parse
        )

    else:
        print(f"[{mode_label}] All grades")
        results = run_all(force_plan, force_prompt, plan_only, parse_raw, force_parse)

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
    if not parse_raw and not plan_only:
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
