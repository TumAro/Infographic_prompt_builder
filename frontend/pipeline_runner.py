import sys
import subprocess
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).parent.parent


def build_parse_cmd(grade, module, topic, force_parse) -> list[str]:
    cmd = [sys.executable, "pipeline.py", "--parse-raw"]
    if grade:        cmd += ["--grade", str(grade)]
    if module:       cmd += ["--module", str(module)]
    if topic:        cmd += ["--topic", str(topic)]
    if force_parse:  cmd.append("--force-parse")
    return cmd


def build_plan_cmd(grade, module, topic, force_plan) -> list[str]:
    cmd = [sys.executable, "pipeline.py", "--plan-only"]
    if grade:        cmd += ["--grade", str(grade)]
    if module:       cmd += ["--module", str(module)]
    if topic:        cmd += ["--topic", str(topic)]
    if force_plan:   cmd.append("--force-plan")
    return cmd


def build_generate_cmd(grade, module, topic, force_plan, force_prompt) -> list[str]:
    cmd = [sys.executable, "pipeline.py"]
    if grade:         cmd += ["--grade", str(grade)]
    if module:        cmd += ["--module", str(module)]
    if topic:         cmd += ["--topic", str(topic)]
    if force_plan:    cmd.append("--force-plan")
    if force_prompt:  cmd.append("--force-prompt")
    return cmd


def build_book_cmd(file_path: str, force_adapt, force_plan, force_prompt, plan_only=False) -> list[str]:
    cmd = [sys.executable, "pipeline.py", "--from-book", file_path]
    if force_adapt:   cmd.append("--force-adapt")
    if force_plan:    cmd.append("--force-plan")
    if force_prompt:  cmd.append("--force-prompt")
    if plan_only:     cmd.append("--plan-only")
    return cmd


def stream_pipeline(cmd: list[str], cwd: str, output_placeholder) -> int:
    lines = []
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=cwd,
        bufsize=1,
    )
    for line in proc.stdout:
        lines.append(line.rstrip())
        output_placeholder.code("\n".join(lines[-50:]))
    proc.wait()
    st.session_state.log_text = "\n".join(lines)
    return proc.returncode
