#!/bin/bash
cd "$(dirname "$0")"

# ── Settings access ───────────────────────────────────────────────────────────
# Change to true to always show the Settings page, or pass --settings at launch.
SHOW_SETTINGS=false
for arg in "$@"; do
    [ "$arg" = "--settings" ] && SHOW_SETTINGS=true
done

if [ ! -f ".venv/bin/python" ]; then
    echo "First run: setting up environment (this takes ~1 minute)..."
    python3 -m venv .venv
fi

.venv/bin/pip install -q -r requirements.txt
echo "Starting Infographic Generator — your browser will open automatically."

if [ "$SHOW_SETTINGS" = "true" ]; then
    cp frontend/_Settings.py frontend/pages/_Settings.py
    trap "rm -f frontend/pages/_Settings.py" EXIT INT TERM
    .venv/bin/streamlit run frontend/app.py -- --settings
else
    .venv/bin/streamlit run frontend/app.py
fi
