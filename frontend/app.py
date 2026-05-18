import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # must be before all local imports

import streamlit as st

from file_staging import (
    stage_docx_files,
    stage_book_files,
    check_existing_output,
)
from pipeline_runner import (
    build_parse_cmd,
    build_generate_cmd,
    build_book_cmd,
    stream_pipeline,
)
from output_browser import render_output_tree

st.set_page_config(page_title="Infographic Generator", layout="wide")
st.title("Infographic Generator")
st.caption("Converts textbook content into AI-ready infographic pages. No command line needed.")

if "log_text" not in st.session_state:
    st.session_state.log_text = ""

docx_tab, book_tab = st.tabs(["DOCX Mode", "Book Writer Mode"])

# ── DOCX MODE ───────────────────────────────────────────────────────────────
with docx_tab:
    st.markdown("Upload a **Class_N.docx** syllabus and one or more **Module_N_\\*.docx** content files.")
    uploaded_docx = st.file_uploader(
        "Upload .docx files",
        type=["docx"],
        accept_multiple_files=True,
        key="docx_upload",
    )

    staging = None
    if uploaded_docx:
        staging = stage_docx_files(uploaded_docx, PROJECT_ROOT)

        if staging.preview_rows:
            st.dataframe(staging.preview_rows, use_container_width=True)

        for err in staging.errors:
            st.error(err)

        if not staging.errors:
            col1, col2 = st.columns(2)
            with col1:
                module_val = st.number_input("Module (0 = all)", min_value=0, value=0, step=1, key="docx_module")
            with col2:
                topic_val = st.number_input("Topic (0 = all)", min_value=0, value=0, step=1, key="docx_topic",
                                            disabled=(module_val == 0))

            module_arg = int(module_val) if module_val > 0 else None
            topic_arg = int(topic_val) if (topic_val > 0 and module_arg) else None

            existing = check_existing_output(PROJECT_ROOT, staging.grade, module_arg, topic_arg)
            if existing:
                st.warning(
                    f"Output already exists for this scope ({len(existing)} file(s)). "
                    "The pipeline will skip existing stages. Use Force options below to regenerate."
                )

            with st.expander("Advanced: Force re-run options"):
                force_parse  = st.checkbox("Force re-parse  (overwrite structured data)", key="d_fp")
                force_plan   = st.checkbox("Force re-plan   (regenerate plan.md)", key="d_fpl")
                force_prompt = st.checkbox("Force re-prompt (regenerate content JSON)", key="d_fpr")

            if st.button("Stage Files and Run Pipeline", type="primary", key="docx_run"):
                log_placeholder = st.empty()

                st.info("Phase 1 — Parsing DOCX files…")
                rc1 = stream_pipeline(
                    build_parse_cmd(staging.grade, module_arg, topic_arg, force_parse),
                    str(PROJECT_ROOT),
                    log_placeholder,
                )
                if rc1 != 0:
                    st.error("Parse phase failed. See output above.")
                    st.stop()

                st.info("Phase 2 — Generating infographic content…")
                rc2 = stream_pipeline(
                    build_generate_cmd(staging.grade, module_arg, topic_arg, force_plan, force_prompt),
                    str(PROJECT_ROOT),
                    log_placeholder,
                )
                if rc2 == 0:
                    st.success("Done! Output files are ready.")
                else:
                    st.error("Generate phase failed. See output above.")

# ── BOOK WRITER MODE ─────────────────────────────────────────────────────────
with book_tab:
    st.markdown(
        "Upload one or more **topic_M.T.md** files from the Book Writer system. "
        "Grade, module, and topic are read automatically from each file's frontmatter."
    )
    uploaded_md = st.file_uploader(
        "Upload Book Writer .md files",
        type=["md"],
        accept_multiple_files=True,
        key="book_upload",
    )

    book_results = None
    if uploaded_md:
        book_results = stage_book_files(uploaded_md, PROJECT_ROOT)

        preview = []
        for r in book_results:
            preview.append({
                "File": r.filename,
                "Grade": r.grade if not r.error else "—",
                "Module": r.module if not r.error else "—",
                "Topic": r.topic if not r.error else "—",
                "Status": r.error if r.error else "✓ Ready",
            })
        st.dataframe(preview, use_container_width=True)

        runnable = [r for r in book_results if not r.error]
        if not runnable:
            st.error("No valid files to run. Fix the errors above.")
        else:
            with st.expander("Advanced: Force re-run options"):
                force_adapt_b  = st.checkbox("Force re-adapt  (overwrite structured data)", key="b_fa")
                force_plan_b   = st.checkbox("Force re-plan   (regenerate plan.md)", key="b_fpl")
                force_prompt_b = st.checkbox("Force re-prompt (regenerate content JSON)", key="b_fpr")

            if st.button("Run Pipeline", type="primary", key="book_run"):
                log_placeholder = st.empty()
                any_failed = False
                for r in runnable:
                    st.info(f"Processing {r.filename}…")
                    rc = stream_pipeline(
                        build_book_cmd(str(r.dest_path), force_adapt_b, force_plan_b, force_prompt_b),
                        str(PROJECT_ROOT),
                        log_placeholder,
                    )
                    if rc != 0:
                        st.error(f"{r.filename} failed. See output above.")
                        any_failed = True
                    else:
                        st.success(f"{r.filename} done.")
                if not any_failed:
                    st.success("All files processed successfully!")

# ── OUTPUT BROWSER ────────────────────────────────────────────────────────────
st.divider()
with st.expander("View output files", expanded=False):
    render_output_tree(PROJECT_ROOT)
