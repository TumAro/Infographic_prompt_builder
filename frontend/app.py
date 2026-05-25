import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # must be before all local imports

import streamlit as st

_features = json.loads((Path(__file__).parent / "features.json").read_text())
_DOCX_ENABLED = _features.get("docx_mode", False)

from file_staging import (
    stage_docx_files,
    stage_book_files,
    check_existing_output,
)
from pipeline_runner import (
    build_parse_cmd,
    build_plan_cmd,
    build_generate_cmd,
    build_book_cmd,
    stream_pipeline,
)
from output_browser import list_plans

st.set_page_config(page_title="Infographic Generator", layout="wide")

st.markdown(
    "<style>header {visibility: hidden;} footer {visibility: hidden;} [data-testid='stStatusWidget'] {visibility: visible;}</style>",
    unsafe_allow_html=True,
)

st.title("Infographic Generator")
st.caption("Converts textbook content into AI-ready infographic pages. No command line needed.")

# ── Session state defaults ────────────────────────────────────────────────────
_DEFAULTS = {
    "log_text":         "",
    "app_success_msg":  None,     # shown once after a successful pipeline run
    "docx_phase":       "idle",   # idle | plan_ready
    "docx_last_grade":  None,
    "docx_last_module": None,
    "docx_last_topic":  None,
    "book_phase":       "idle",   # idle | plan_ready
    "book_last_paths":  [],
    "book_last_scope":  [],      # [(grade, module, topic)] from last book_plan run
    "running":          False,    # True while any pipeline is executing
    "pending":          None,     # name of the action to run
    "pending_params":   {},       # params for that action
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Pipeline execution dispatch ───────────────────────────────────────────────
# Runs BEFORE rendering so buttons are already disabled on the first post-click render.
if st.session_state.running:
    action = st.session_state.pending
    p      = st.session_state.pending_params
    log_ph = st.empty()

    if action == "docx_plan":
        g, m, t = p["grade"], p["module"], p["topic"]
        rc1 = stream_pipeline(build_parse_cmd(g, m, t, p["force_parse"]), str(PROJECT_ROOT), log_ph)
        if rc1 != 0:
            st.error("Reading the .docx files failed. Check the output above for details.")
        else:
            rc2 = stream_pipeline(build_plan_cmd(g, m, t, p["force_plan"]), str(PROJECT_ROOT), log_ph)
            # Always save scope so disk-based plan review can find partial results
            st.session_state.docx_last_grade  = g
            st.session_state.docx_last_module = m
            st.session_state.docx_last_topic  = t
            if rc2 == 0:
                st.session_state.docx_phase = "plan_ready"
            else:
                partial = list_plans(PROJECT_ROOT, g, m, t)
                if partial:
                    st.warning(f"Plan generation had errors, but {len(partial)} plan(s) exist. Review below and proceed or redo.")
                    st.session_state.docx_phase = "plan_ready"
                else:
                    st.error("Plan generation failed. No plans found. See output above.")

    elif action == "docx_approve":
        g, m, t = p["grade"], p["module"], p["topic"]
        rc = stream_pipeline(build_generate_cmd(g, m, t, False, p["force_prompt"]), str(PROJECT_ROOT), log_ph)
        if rc == 0:
            st.session_state.docx_phase = "idle"
            st.session_state.docx_last_grade = None  # hide Step 2 — work is done
            st.session_state.app_success_msg = "Prompts generated! Open the **Output Browser** page in the left sidebar to download your files."
        else:
            st.error("Prompt generation failed. Check the output above for details.")

    elif action == "docx_redo":
        g, m, t = p["grade"], p["module"], p["topic"]
        rc = stream_pipeline(build_plan_cmd(g, m, t, force_plan=True), str(PROJECT_ROOT), log_ph)
        if rc != 0:
            st.error("Plan regeneration failed. See output above.")

    elif action == "redo_single_plan":
        g, m, t = p["grade"], p["module"], p["topic"]
        rc = stream_pipeline(build_plan_cmd(g, m, t, force_plan=True), str(PROJECT_ROOT), log_ph)
        if rc != 0:
            st.error(f"Plan regeneration failed for topic {t}. See output above.")

    elif action == "book_plan":
        any_failed = False
        for path_str in p["paths"]:
            rc = stream_pipeline(
                build_book_cmd(path_str, p["force_adapt"], p["force_plan"],
                               force_prompt=False, plan_only=True),
                str(PROJECT_ROOT), log_ph,
            )
            if rc != 0:
                st.error(f"{Path(path_str).name} failed.")
                any_failed = True
        # Always save paths/scope; transition to plan_ready if at least some plans exist
        st.session_state.book_last_paths = p["paths"]
        st.session_state.book_last_scope = p.get("scope", [])
        partial_book = list_plans(PROJECT_ROOT, grade=None, module=None, topic=None)
        if not any_failed:
            st.session_state.book_phase = "plan_ready"
        elif partial_book:
            st.warning(f"{len(partial_book)} plan(s) exist despite errors. Review below.")
            st.session_state.book_phase = "plan_ready"

    elif action == "book_approve":
        if not p["paths"]:
            st.error("No source files available. Re-upload the .md files and try again.")
        else:
            any_failed = False
            for path_str in p["paths"]:
                rc = stream_pipeline(
                    build_book_cmd(path_str, p["force_adapt"], False, p["force_prompt"]),
                    str(PROJECT_ROOT), log_ph,
                )
                if rc != 0:
                    st.error(f"{Path(path_str).name} failed.")
                    any_failed = True
                else:
                    st.success(f"{Path(path_str).name} done.")
            if not any_failed:
                st.session_state.book_phase = "idle"
                st.session_state.app_success_msg = "Prompts generated! Open the **Output Browser** page in the left sidebar to download your files."

    elif action == "book_redo":
        if not p["paths"]:
            st.error("No source files available. Re-upload the .md files and try again.")
        else:
            any_failed = False
            for path_str in p["paths"]:
                rc = stream_pipeline(
                    build_book_cmd(path_str, p["force_adapt"], force_plan=True,
                                   force_prompt=False, plan_only=True),
                    str(PROJECT_ROOT), log_ph,
                )
                if rc != 0:
                    any_failed = True
            if any_failed:
                st.error("Plan regeneration failed for one or more files.")

    st.session_state.running       = False
    st.session_state.pending       = None
    st.session_state.pending_params = {}
    st.rerun()

# Convenience shorthand
_busy = st.session_state.running

# ── One-shot success banner ───────────────────────────────────────────────────
if msg := st.session_state.pop("app_success_msg", None):
    st.success(msg)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    if "--settings" in sys.argv:
        st.page_link("pages/_Settings.py", label="⚙️ Settings")
    if st.session_state.log_text:
        with st.expander("Last pipeline log", expanded=False):
            st.code(st.session_state.log_text)

# ── Tab layout ────────────────────────────────────────────────────────────────
if _DOCX_ENABLED:
    docx_tab, book_tab = st.tabs(["DOCX Mode", "Book Writer Mode"])
else:
    book_tab = st.container()

# ── DOCX MODE (disabled via Settings → Feature Flags) ─────────────────────────
if _DOCX_ENABLED:
    with docx_tab:
        st.markdown(
            "Upload a syllabus file and one or more content files.  \n"
            "**Naming required:** `Class_6.docx` (syllabus) · `Module_1_Introduction.docx`, `Module_2_AI_Basics.docx` … (content)"
        )
        uploaded_docx = st.file_uploader(
            "Upload .docx files",
            type=["docx"],
            accept_multiple_files=True,
            key="docx_upload",
        )

        if uploaded_docx:
            staging = stage_docx_files(uploaded_docx, PROJECT_ROOT)

            if staging.preview_rows:
                st.dataframe(staging.preview_rows, width='stretch')

            for err in staging.errors:
                st.error(err)

            if not staging.errors:
                col1, col2 = st.columns(2)
                with col1:
                    module_val = st.number_input("Module (0 = all)", min_value=0, value=0, step=1,
                                                 key="docx_module", disabled=_busy)
                with col2:
                    topic_val = st.number_input("Topic (0 = all)", min_value=0, value=0, step=1,
                                                key="docx_topic", disabled=(_busy or module_val == 0),
                                                help="Select a specific module first to filter by topic.")

                module_arg = int(module_val) if module_val > 0 else None
                topic_arg  = int(topic_val)  if (topic_val > 0 and module_arg) else None

                existing = check_existing_output(PROJECT_ROOT, staging.grade, module_arg, topic_arg)
                if existing:
                    st.warning(
                        f"Output already exists for this scope ({len(existing)} file(s)). "
                        "The pipeline will skip existing stages. Use Force options below to regenerate."
                    )

                with st.expander("Advanced: Force re-run options"):
                    force_parse  = st.checkbox("Force re-parse  (overwrite structured data)", key="d_fp",  disabled=_busy)
                    force_plan   = st.checkbox("Force re-plan   (regenerate plan.md)",        key="d_fpl", disabled=_busy)
                    force_prompt = st.checkbox("Force re-prompt (regenerate content JSON)",   key="d_fpr", disabled=_busy)

                if st.button("Step 1 — Generate Plans", type="primary", key="docx_plan", disabled=_busy):
                    st.session_state.running       = True
                    st.session_state.pending       = "docx_plan"
                    st.session_state.pending_params = {
                        "grade": staging.grade, "module": module_arg, "topic": topic_arg,
                        "force_parse": force_parse, "force_plan": force_plan,
                    }
                    st.rerun()

        # ── Plan review ───────────────────────────────────────────────────────
        if st.session_state.docx_phase == "plan_ready":
            g = st.session_state.docx_last_grade
            m = st.session_state.docx_last_module
            t = st.session_state.docx_last_topic
            st.divider()
            st.subheader("Step 2 — Review Plans")
            plans = list_plans(PROJECT_ROOT, g, m, t)
            if not plans:
                st.warning("No plans found on disk. Try generating again.")
            else:
                st.success(f"{len(plans)} plan(s) ready for review.")
                for label, pg, pm, pt, plan_path in plans:
                    with st.expander(label, expanded=True):
                        st.markdown(plan_path.read_text(encoding="utf-8"))
                        if st.button("↺  Redo this plan", key=f"d_redo_{pg}_{pm}_{pt}", disabled=_busy):
                            st.session_state.running        = True
                            st.session_state.pending        = "redo_single_plan"
                            st.session_state.pending_params = {"grade": pg, "module": pm, "topic": pt}
                            st.rerun()

            col_approve, col_redo = st.columns(2)
            with col_approve:
                if g is None:
                    st.info("Upload files above and run Step 1 to enable prompt generation.")
                elif st.button("✓  Plans look good — Generate Prompts", type="primary",
                               key="docx_approve", disabled=_busy):
                    st.session_state.running       = True
                    st.session_state.pending       = "docx_approve"
                    st.session_state.pending_params = {
                        "grade": g, "module": m, "topic": t,
                        "force_prompt": st.session_state.get("d_fpr", False),
                    }
                    st.rerun()
            with col_redo:
                if g is not None and st.button("↺  Redo All Plans", key="docx_redo", disabled=_busy):
                    st.session_state.running       = True
                    st.session_state.pending       = "docx_redo"
                    st.session_state.pending_params = {"grade": g, "module": m, "topic": t}
                    st.rerun()

# ── BOOK WRITER MODE ──────────────────────────────────────────────────────────
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

    if uploaded_md:
        book_results = stage_book_files(uploaded_md, PROJECT_ROOT)

        preview = []
        for r in book_results:
            preview.append({
                "File":   r.filename,
                "Grade":  r.grade  if not r.error else "—",
                "Module": r.module if not r.error else "—",
                "Topic":  r.topic  if not r.error else "—",
                "Status": r.error  if r.error     else "✓ Ready",
            })
        st.dataframe(preview, width='stretch')

        runnable = [r for r in book_results if not r.error]
        if not runnable:
            st.error("No valid files to run. Fix the errors above.")
        else:
            with st.expander("Advanced: Force re-run options"):
                force_adapt_b  = st.checkbox("Force re-adapt  (overwrite structured data)", key="b_fa",  disabled=_busy)
                force_plan_b   = st.checkbox("Force re-plan   (regenerate plan.md)",        key="b_fpl", disabled=_busy)
                force_prompt_b = st.checkbox("Force re-prompt (regenerate content JSON)",   key="b_fpr", disabled=_busy)

            if st.button("Step 1 — Generate Plans", type="primary", key="book_plan", disabled=_busy):
                st.session_state.running       = True
                st.session_state.pending       = "book_plan"
                st.session_state.pending_params = {
                    "paths":       [str(r.dest_path) for r in runnable],
                    "force_adapt": force_adapt_b,
                    "force_plan":  force_plan_b,
                    "scope":       [(r.grade, r.module, r.topic) for r in runnable],
                }
                st.rerun()

    # ── Plan review ───────────────────────────────────────────────────────────
    if st.session_state.book_phase == "plan_ready":
        st.divider()
        st.subheader("Step 2 — Review Plans")
        _scope = set(map(tuple, st.session_state.book_last_scope))
        plans = [
            (label, g, m, t, path)
            for label, g, m, t, path in list_plans(PROJECT_ROOT, grade=None, module=None, topic=None)
            if not _scope or (g, m, t) in _scope
        ]
        if not plans:
            st.warning("No plans found on disk. Try generating again.")
        else:
            st.success(f"{len(plans)} plan(s) ready for review.")
            for label, pg, pm, pt, plan_path in plans:
                with st.expander(label, expanded=True):
                    st.markdown(plan_path.read_text(encoding="utf-8"))
                    if st.button("↺  Redo this plan", key=f"b_redo_{pg}_{pm}_{pt}", disabled=_busy):
                        st.session_state.running        = True
                        st.session_state.pending        = "redo_single_plan"
                        st.session_state.pending_params = {"grade": pg, "module": pm, "topic": pt}
                        st.rerun()

        _has_paths = bool(st.session_state.book_last_paths)
        col_approve, col_redo = st.columns(2)
        with col_approve:
            if not _has_paths:
                st.info("Re-upload the source .md files above to enable prompt generation.")
            elif st.button("✓  Plans look good — Generate Prompts", type="primary",
                           key="book_approve", disabled=_busy):
                st.session_state.running       = True
                st.session_state.pending       = "book_approve"
                st.session_state.pending_params = {
                    "paths":         st.session_state.book_last_paths,
                    "force_adapt":   st.session_state.get("b_fa",  False),
                    "force_prompt":  st.session_state.get("b_fpr", False),
                }
                st.rerun()
        with col_redo:
            if _has_paths and st.button("↺  Redo All Plans", key="book_redo", disabled=_busy):
                st.session_state.running       = True
                st.session_state.pending       = "book_redo"
                st.session_state.pending_params = {
                    "paths":       st.session_state.book_last_paths,
                    "force_adapt": st.session_state.get("b_fa", False),
                }
                st.rerun()
