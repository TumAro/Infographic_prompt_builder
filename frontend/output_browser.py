from pathlib import Path

import streamlit as st


def render_output_tree(project_root: Path) -> None:
    output_dir = project_root / "output"
    if not output_dir.exists() or not any(output_dir.iterdir()):
        st.info("No output generated yet.")
        return

    grade_dirs = sorted(output_dir.glob("grade_*"))
    for grade_dir in grade_dirs:
        with st.expander(grade_dir.name.replace("_", " ").title()):
            for module_dir in sorted(grade_dir.glob("module_*")):
                st.markdown(f"**{module_dir.name.replace('_', ' ').title()}**")
                for topic_dir in sorted(module_dir.glob("topic_*")):
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;*{topic_dir.name.replace('_', ' ').title()}*")
                    plan_path = topic_dir / "plan.md"
                    if plan_path.exists():
                        preview = "\n".join(plan_path.read_text().splitlines()[:30])
                        st.code(preview, language="markdown")
                    for j in sorted(topic_dir.glob("*.json")):
                        st.caption(f"{j.name}  —  {j.stat().st_size:,} bytes")
