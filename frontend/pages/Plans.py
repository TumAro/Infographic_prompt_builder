import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from output_browser import list_plans
from pipeline_runner import build_plan_cmd, build_generate_cmd, stream_pipeline

st.set_page_config(page_title="Plans", layout="wide")
st.title("Plans")
st.caption("All plans saved on disk. Regenerate a plan or generate its prompts individually.")

# ── Sidebar: last pipeline log ────────────────────────────────────────────────
if st.session_state.get("log_text"):
    with st.sidebar:
        with st.expander("Last pipeline log", expanded=False):
            st.code(st.session_state.log_text)

# ── One-shot success banner ───────────────────────────────────────────────────
if msg := st.session_state.pop("plans_success_msg", None):
    st.success(msg)

plans = list_plans(PROJECT_ROOT, None, None, None)

if not plans:
    st.info("No plans found. Run Step 1 from the main pipeline page first.")
    st.stop()

# ── Search ────────────────────────────────────────────────────────────────────
_SEP = str.maketrans("›—>", "   ")

def _norm(s: str) -> str:
    return " ".join(s.translate(_SEP).lower().split())

query = st.text_input("Search", placeholder="e.g. Topic 3, Module 2, Variables…", key="plans_search")
visible = [(label, pg, pm, pt, path) for label, pg, pm, pt, path in plans
           if not query or _norm(query) in _norm(label)]

st.caption(f"{len(visible)} of {len(plans)} plan(s)")
st.divider()

# ── Per-plan list ─────────────────────────────────────────────────────────────
for label, pg, pm, pt, plan_path in visible:
    with st.expander(label, expanded=False):
        st.markdown(plan_path.read_text(encoding="utf-8"))

        col_redo, col_gen = st.columns(2)

        with col_redo:
            if st.button("↺  Regenerate plan", key=f"plans_redo_{pg}_{pm}_{pt}"):
                log_ph = st.empty()
                rc = stream_pipeline(
                    build_plan_cmd(pg, pm, pt, force_plan=True),
                    str(PROJECT_ROOT),
                    log_ph,
                )
                if rc == 0:
                    st.session_state["plans_success_msg"] = f"Plan regenerated: {label}"
                    st.rerun()
                else:
                    st.error(f"Regeneration failed for {label}. Check the output above.")

        with col_gen:
            if st.button("Generate prompts", type="primary", key=f"plans_gen_{pg}_{pm}_{pt}"):
                log_ph = st.empty()
                rc = stream_pipeline(
                    build_generate_cmd(pg, pm, pt, force_plan=False, force_prompt=False),
                    str(PROJECT_ROOT),
                    log_ph,
                )
                if rc == 0:
                    st.session_state["plans_success_msg"] = (
                        f"Prompts generated for {label}. "
                        "Open the Output Browser page to download."
                    )
                    st.rerun()
                else:
                    st.error(f"Prompt generation failed for {label}. Check the output above.")
