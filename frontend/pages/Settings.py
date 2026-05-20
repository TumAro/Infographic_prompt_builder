import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(page_title="Settings", layout="wide")
st.title("Settings")

st.error(
    "Changes to system prompts directly affect AI output quality. "
    "Incorrect edits may cause the pipeline to produce poor or broken results. "
    "Only edit if you know what you are changing."
)

# ── System Prompts ─────────────────────────────────────────────────────────────
st.subheader("System Prompts")
st.caption("Each prompt guides the AI at one stage of the pipeline.")

_PROMPT_LABELS = {
    "plan_system_prompt.md":   "Plan generator — controls how visual storyboards are written",
    "prompt_system_prompt.md": "Prompt generator — controls how image prompts are written",
    "vision_system_prompt.md": "Vision — controls how embedded images are described (DOCX mode)",
    "gist_system_prompt.md":   "Gist — standalone summary tool (not used in main pipeline)",
}

prompts_dir = PROJECT_ROOT / "prompts"
prompt_files = sorted(prompts_dir.glob("*.md")) if prompts_dir.exists() else []

if not prompt_files:
    st.warning("No prompt files found in prompts/.")
else:
    for pf in prompt_files:
        label = _PROMPT_LABELS.get(pf.name, pf.name)
        st.markdown(f"**{pf.stem.replace('_', ' ').title()}**")
        st.caption(label)

        current = pf.read_text(encoding="utf-8")
        edited = st.text_area(
            pf.name,
            value=current,
            height=260,
            key=f"prompt_{pf.stem}",
            label_visibility="collapsed",
        )

        col_msg, col_btn = st.columns([4, 1])
        with col_msg:
            if edited != current:
                st.warning("Unsaved changes — save before running the pipeline.")
        with col_btn:
            if st.button("Save", key=f"save_prompt_{pf.stem}", disabled=(edited == current)):
                pf.write_text(edited, encoding="utf-8")
                st.success(f"{pf.name} saved.")
                st.rerun()

        st.divider()

# ── LLM Config ────────────────────────────────────────────────────────────────
with st.expander("Advanced — LLM Config (llm_config.json)", expanded=False):
    st.caption("Model names, temperature, token limits. Edit carefully — bad JSON will be rejected.")

    llm_cfg = PROJECT_ROOT / "configs" / "llm_config.json"
    if not llm_cfg.exists():
        st.warning("configs/llm_config.json not found.")
    else:
        llm_current = llm_cfg.read_text(encoding="utf-8")
        llm_edited = st.text_area(
            "llm_config.json",
            value=llm_current,
            height=220,
            key="llm_config_text",
            label_visibility="collapsed",
        )

        col_msg, col_btn = st.columns([4, 1])
        with col_msg:
            if llm_edited != llm_current:
                st.warning("Unsaved changes.")
        with col_btn:
            if st.button("Save", key="save_llm_config", disabled=(llm_edited == llm_current)):
                try:
                    json.loads(llm_edited)  # validate before writing
                    llm_cfg.write_text(llm_edited, encoding="utf-8")
                    st.success("llm_config.json saved.")
                    st.rerun()
                except json.JSONDecodeError as e:
                    print(f"[ERROR] llm_config.json save failed: {e}")
                    st.error(f"Invalid JSON — not saved. Fix the error and try again: {e}")

# ── Feature Flags ─────────────────────────────────────────────────────────────
st.subheader("Feature Flags")
_feat_file = Path(__file__).parent.parent / "features.json"
_feat = json.loads(_feat_file.read_text()) if _feat_file.exists() else {}
docx_on = st.toggle(
    "Enable DOCX Mode",
    value=_feat.get("docx_mode", False),
    help="Show the DOCX upload tab on the main pipeline page.",
)
if docx_on != _feat.get("docx_mode", False):
    _feat["docx_mode"] = docx_on
    _feat_file.write_text(json.dumps(_feat, indent=2))
    st.success("Saved. Reload the pipeline page to apply.")
