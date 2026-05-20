import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# sys.path is set by app.py before this module is imported
import book_md_adapter


def parse_grade_from_docx_name(filename: str) -> int | None:
    m = re.search(r"Class_(\d+)\.docx", filename, re.IGNORECASE)
    return int(m.group(1)) if m else None


def parse_module_from_docx_name(filename: str) -> int | None:
    m = re.match(r"Module_(\d+)_", filename, re.IGNORECASE)
    return int(m.group(1)) if m else None


def classify_docx_file(filename: str) -> tuple[str, int | None, int | None]:
    grade = parse_grade_from_docx_name(filename)
    if grade is not None:
        return ("syllabus", grade, None)
    module = parse_module_from_docx_name(filename)
    if module is not None:
        # grade unknown until we see the syllabus; caller reconciles
        return ("module", None, module)
    return ("unknown", None, None)


@dataclass
class StagingResult:
    grade: int | None = None
    saved_paths: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    preview_rows: list[dict] = field(default_factory=list)


def stage_docx_files(uploaded_files, project_root: Path) -> StagingResult:
    result = StagingResult()

    syllabuses = []
    modules = []
    for f in uploaded_files:
        kind, grade, module = classify_docx_file(f.name)
        if kind == "syllabus":
            syllabuses.append((f, grade))
        elif kind == "module":
            modules.append((f, module))
        else:
            print(f"[WARN] Cannot classify file: {f.name}")
            result.errors.append(f"'{f.name}' has an unexpected name. Expected something like Class_6.docx or Module_1_Introduction.docx.")

    if len(syllabuses) == 0:
        result.errors.append("No syllabus found. Upload a file named like Class_6.docx.")
    elif len(syllabuses) > 1:
        result.errors.append(f"Multiple syllabus files uploaded ({len(syllabuses)}). Upload exactly one (e.g. Class_6.docx).")

    if result.errors:
        return result

    _, grade = syllabuses[0]
    result.grade = grade

    dest_dir = project_root / "data" / f"grade_{grade}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    for f, _ in syllabuses:
        dest = dest_dir / f.name
        dest.write_bytes(f.read())
        result.saved_paths.append(dest)
        result.preview_rows.append({"File": f.name, "Type": "Syllabus", "Grade": grade, "Module": "—"})

    for f, module_num in modules:
        dest = dest_dir / f.name
        dest.write_bytes(f.read())
        result.saved_paths.append(dest)
        result.preview_rows.append({"File": f.name, "Type": "Module Content", "Grade": grade, "Module": module_num})

    return result


@dataclass
class BookStagingResult:
    filename: str
    grade: int = 0
    module: int = 0
    topic: int = 0
    dest_path: Path = None
    error: str | None = None


def stage_book_files(uploaded_files, project_root: Path) -> list[BookStagingResult]:
    results = []
    seen = set()

    for f in uploaded_files:
        content_bytes = f.read()
        content_text = content_bytes.decode("utf-8", errors="replace")
        lines = content_text.splitlines()

        try:
            fields, _ = book_md_adapter._parse_frontmatter(lines)
            grade, module_num, _, topic_num, _ = book_md_adapter._extract_metadata(fields)
        except Exception as e:
            print(f"[ERROR] Metadata read failed for {f.name}: {e}")
            results.append(BookStagingResult(filename=f.name, error=f"Could not read metadata from {f.name}. Check that it starts with a valid --- header block."))
            continue

        key = (grade, module_num, topic_num)
        if key in seen:
            results.append(BookStagingResult(
                filename=f.name, grade=grade, module=module_num, topic=topic_num,
                error=f"Duplicate topic ({grade}/{module_num}/{topic_num}) — skipped",
            ))
            continue
        seen.add(key)

        dest = project_root / "book_output" / f"grade_{grade}" / f"module_{module_num}" / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content_bytes)

        results.append(BookStagingResult(
            filename=f.name, grade=grade, module=module_num, topic=topic_num, dest_path=dest,
        ))

    return results


def check_existing_output(project_root: Path, grade: int, module: int | None, topic: int | None) -> list[str]:
    base = project_root / "output" / f"grade_{grade}"
    if module:
        base = base / f"module_{module}"
    if topic:
        base = base / f"topic_{topic}"
    if not base.exists():
        return []
    return [str(p) for p in base.glob("**/*") if p.is_file()]
