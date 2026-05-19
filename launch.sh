#!/bin/bash
cd "$(dirname "$0")"

if [ ! -f ".venv/bin/python" ]; then
    echo "First run: setting up environment (this takes ~1 minute)..."
    python3 -m venv .venv
fi

.venv/bin/pip install -q -r requirements.txt
echo "Starting Infographic Generator — your browser will open automatically."
.venv/bin/streamlit run frontend/app.py
