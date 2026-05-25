import hashlib
import io
import re
import zipfile
from pathlib import Path

import streamlit as st

_SEP = str.maketrans("›—>", "   ")  # normalize separators to spaces for search


def _norm(s: str) -> str:
    return " ".join(s.translate(_SEP).lower().split())


def _ck(p: Path) -> str:
    """Stable session-state key for a path's checkbox — survives sort-order changes."""
    return "sel_" + hashlib.md5(str(p).encode()).hexdigest()[:8]


def _zip_name(p: Path) -> str:
    """Unique ZIP entry name: G6_M1_T3_page_1_final.json avoids same-name collisions."""
    g = p.parent.parent.parent.name.split("_")[1]
    m = p.parent.parent.name.split("_")[1]
    t = p.parent.name.split("_")[1]
    return f"G{g}_M{m}_T{t}_{p.name}"


# ── helpers ───────────────────────────────────────────────────────────────────

def _topic_name_from_plan(plan_path: Path) -> str:
    """Extract topic name from '# Plan: {name}' on the first line of plan.md."""
    if not plan_path.exists():
        return ""
    first = plan_path.read_text(encoding="utf-8").splitlines()[0]
    m = re.match(r"^#\s*Plan:\s*(.+)$", first)
    return m.group(1).strip() if m else ""


def _make_zip(pages: list[tuple[str, str]]) -> bytes:
    """Pack (filename, content) pairs into an in-memory ZIP."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in pages:
            zf.writestr(name, content)
    return buf.getvalue()


# ── plan review ───────────────────────────────────────────────────────────────

def list_plans(
    project_root: Path, grade, module, topic
) -> list[tuple[str, int, int, int, Path]]:
    """Return (label, grade, module, topic, path) for every plan.md in scope."""
    base = project_root / "output"
    if grade:  base = base / f"grade_{grade}"
    if module: base = base / f"module_{module}"
    if topic:  base = base / f"topic_{topic}"

    result = []
    for plan_path in sorted(base.rglob("plan.md")) if base.exists() else []:
        rel = plan_path.relative_to(project_root / "output")
        g = int(rel.parts[0].split("_")[1])
        m = int(rel.parts[1].split("_")[1])
        t = int(rel.parts[2].split("_")[1])
        name = _topic_name_from_plan(plan_path)
        label = f"Grade {g} › Module {m} › Topic {t}" + (f" — {name}" if name else "")
        result.append((label, g, m, t, plan_path))
    return result


# ── output browser ────────────────────────────────────────────────────────────

def render_output_tree(project_root: Path) -> None:
    output_dir = project_root / "output"
    if not output_dir.exists() or not any(output_dir.iterdir()):
        st.info("No output generated yet.")
        return

    # Collect all final JSON pages, then sort newest-first by mtime
    raw: list[tuple[str, Path]] = []
    for grade_dir in output_dir.glob("grade_*"):
        g = grade_dir.name.split("_")[1]
        for module_dir in grade_dir.glob("module_*"):
            mod = module_dir.name.split("_")[1]
            for topic_dir in module_dir.glob("topic_*"):
                top = topic_dir.name.split("_")[1]
                topic_name = _topic_name_from_plan(topic_dir / "plan.md")
                # Always include numeric topic ID so "topic 4" always matches in search
                label_prefix = (
                    f"Grade {g} › Module {mod} › Topic {top}"
                    + (f" — {topic_name}" if topic_name else "")
                )
                for j in topic_dir.glob("page_*_final.json"):
                    page_num = j.stem.split("_")[1]
                    raw.append((f"{label_prefix} › Page {page_num}", j))

    all_pages = sorted(raw, key=lambda x: x[1].stat().st_mtime, reverse=True)

    if not all_pages:
        st.info("No output files yet.")
        return

    # Search filter
    query = st.text_input("Search", placeholder="e.g. Variables, Topic 4, Module 2…", key="ob_search")
    visible = [
        (d, p) for (d, p) in all_pages
        if not query or _norm(query) in _norm(d)
    ]

    # Apply "select all / deselect all" BEFORE checkboxes are instantiated
    pending = st.session_state.pop("_select_all_pending", None)
    if pending is not None:
        for k in pending:
            st.session_state[k] = True

    # Read selected from session state BEFORE rendering checkboxes (safe — just reading)
    selected = [(d, p) for (d, p) in all_pages if st.session_state.get(_ck(p), False)]

    # ── Action bar at TOP ────────────────────────────────────────────────────────
    col_info, col_all, col_desel, col_dl = st.columns([3, 1, 1, 2])
    with col_info:
        st.caption(f"{len(visible)} shown · {len(selected)} selected")
    with col_all:
        if st.button("Select all", key="sel_all"):
            st.session_state["_select_all_pending"] = [_ck(p) for _, p in visible]
            st.rerun()
    with col_desel:
        if selected and st.button("Deselect all", key="sel_none"):
            for _, p in all_pages:
                st.session_state[_ck(p)] = False
            st.rerun()
    with col_dl:
        if selected:
            st.download_button(
                label=f"⬇ Download {len(selected)} as ZIP",
                data=_make_zip([(_zip_name(p), p.read_text(encoding="utf-8")) for _, p in selected]),
                file_name="infographic_prompts.zip",
                mime="application/zip",
                type="primary",
            )

    # ── Per-page list ────────────────────────────────────────────────────────────
    for display, path in visible:
        col_chk, col_label = st.columns([1, 11])
        with col_chk:
            st.checkbox("Select", key=_ck(path), label_visibility="collapsed")
        with col_label:
            with st.expander(display):
                st.code(path.read_text(encoding="utf-8"), language="json")
