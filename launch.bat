@echo off
cd /d "%~dp0"

rem ── Settings access ───────────────────────────────────────────────────────────
rem Change to true to always show the Settings page, or pass --settings at launch.
set SHOW_SETTINGS=false
:parse
if "%1"=="--settings" set SHOW_SETTINGS=true
shift
if not "%1"=="" goto parse

if not exist ".venv\Scripts\python.exe" (
    echo First run: setting up environment (this takes ~1 minute)...
    python -m venv .venv
)

.venv\Scripts\pip install -q -r requirements.txt
echo Starting Infographic Generator — your browser will open automatically.

if "%SHOW_SETTINGS%"=="true" (
    copy frontend\_Settings.py frontend\pages\_Settings.py
    .venv\Scripts\streamlit run frontend\app.py -- --settings
    del frontend\pages\_Settings.py
) else (
    .venv\Scripts\streamlit run frontend\app.py
)
pause
