import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from output_browser import render_output_tree

st.set_page_config(page_title="Output Browser", layout="wide")
st.title("Output Browser")
render_output_tree(PROJECT_ROOT)
