@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo First run: setting up environment (this takes ~1 minute^)...
    python -m venv .venv
)

.venv\Scripts\pip install -q -r requirements.txt
echo Starting Infographic Generator — your browser will open automatically.
.venv\Scripts\streamlit run frontend\app.py
pause
