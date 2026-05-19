import io
import re
import zipfile
from pathlib import Path

import streamlit as st


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

    # Collect all final JSON pages across the whole output tree
    all_pages: list[tuple[str, Path]] = []  # (display_key, path)
    for grade_dir in sorted(output_dir.glob("grade_*")):
        g = grade_dir.name.split("_")[1]
        for module_dir in sorted(grade_dir.glob("module_*")):
            mod = module_dir.name.split("_")[1]
            for topic_dir in sorted(module_dir.glob("topic_*")):
                top = topic_dir.name.split("_")[1]
                topic_name = _topic_name_from_plan(topic_dir / "plan.md")
                label_prefix = (
                    f"Grade {g} › Module {mod} › "
                    + (f"{topic_name}" if topic_name else f"Topic {top}")
                )
                for j in sorted(topic_dir.glob("page_*_final.json")):
                    page_num = j.stem.split("_")[1]
                    display = f"{label_prefix} › Page {page_num}"
                    all_pages.append((display, j))

    if not all_pages:
        st.info("No output files yet.")
        return

    st.markdown("Select the pages you want, then download them all as a ZIP.")

    # Apply "select all" BEFORE checkboxes are instantiated
    if st.session_state.pop("_select_all_pending", False):
        for i in range(len(all_pages)):
            st.session_state[f"sel_{i}"] = True

    # Per-page: checkbox for download + expander for preview
    selected: list[tuple[str, Path]] = []
    for i, (display, path) in enumerate(all_pages):
        col_chk, col_label = st.columns([1, 11])
        with col_chk:
            checked = st.checkbox("", key=f"sel_{i}", label_visibility="collapsed")
        with col_label:
            with st.expander(display):
                st.code(path.read_text(encoding="utf-8"), language="json")
        if checked:
            selected.append((display, path))

    col1, col2 = st.columns([2, 1])
    with col1:
        st.caption(f"{len(selected)} of {len(all_pages)} page(s) selected for download")
    with col2:
        if st.button("Select all", key="sel_all"):
            st.session_state["_select_all_pending"] = True
            st.rerun()

    if selected:
        zip_pages = [(p.name, p.read_text(encoding="utf-8")) for _, p in selected]
        st.download_button(
            label=f"⬇ Download {len(selected)} selected page(s) as ZIP",
            data=_make_zip(zip_pages),
            file_name="infographic_prompts.zip",
            mime="application/zip",
            type="primary",
        )
