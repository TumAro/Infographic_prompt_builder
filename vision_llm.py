"""
vision_llm.py — Inline image describer called by doc_parser.

Public API
----------
describe_image(image_bytes, extension, caption, topic_name, subtopic_name) -> tuple[bool, str]
    Returns (is_code, description) where is_code is True when the vision LLM
    identifies the image as a code screenshot (TYPE: code prefix in response).
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import litellm

_CONFIG_PATH = Path(__file__).parent / "configs" / "llm_config.json"
_PROMPT_PATH = Path(__file__).parent / "prompts" / "vision_system_prompt.md"
_MAX_RETRIES = 5
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_THINK_EXTRACT_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)


def _load_config() -> dict:
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg


def _parse_response(raw: str) -> tuple[bool, str]:
    """Parse TYPE: prefix from vision LLM output. Returns (is_code, description)."""
    lines = raw.strip().splitlines()
    if lines and lines[0].strip().upper().startswith("TYPE:"):
        tag = lines[0].strip().upper()
        is_code = "CODE" in tag
        description = "\n".join(lines[1:]).strip()
        return is_code, description
    # No TYPE line found — default to figure (not code)
    return False, raw.strip()


def _strip_thinking(text: str) -> str:
    stripped = _THINK_RE.sub("", text).strip()
    if stripped:
        return stripped
    # Fallback: model placed entire answer inside <think> block.
    m = _THINK_EXTRACT_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def describe_image(
    image_bytes: bytes,
    extension: str,
    caption: str | None,
    topic_name: str,
    subtopic_name: str,
) -> tuple[bool, str]:
    """
    Describe an image using the vision LLM.

    Parameters
    ----------
    image_bytes : raw image data
    extension   : file extension without dot, e.g. "png", "jpeg"
    caption     : caption text from the document, or None
    topic_name  : enclosing topic name (for context)
    subtopic_name : enclosing subtopic name (for context)

    Returns
    -------
    (is_code, description) — is_code is True when the image is a code screenshot.
    description is plain text; fallback failure string returned after 5 retries.
    """
    cfg = _load_config()
    vision_cfg = cfg["vision_llm"]
    base_url = cfg.get("base_url", "http://localhost:11434")

    with open(_PROMPT_PATH, encoding="utf-8") as f:
        system_prompt = f.read()

    # Normalise extension for data URI
    ext = extension.lower().lstrip(".")
    if ext == "jpg":
        ext = "jpeg"

    b64_str = base64.b64encode(image_bytes).decode("ascii")
    data_uri = f"data:image/{ext};base64,{b64_str}"

    if caption:
        user_text = (
            "/no_think\n"
            f"Topic: {topic_name}\n"
            f"Subtopic: {subtopic_name}\n"
            f"Caption: {caption}\n"
            "Describe this image."
        )
    else:
        user_text = (
            "/no_think\n"
            f"Topic: {topic_name}\n"
            f"Subtopic: {subtopic_name}\n"
            "No caption available. Describe what you see."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_uri}},
                {"type": "text", "text": user_text},
            ],
        },
    ]

    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = litellm.completion(
                model=f"ollama/{vision_cfg['model']}",
                messages=messages,
                base_url=base_url,
                temperature=vision_cfg["temperature"],
                max_tokens=vision_cfg["max_tokens"],
            )
            raw = response.choices[0].message.content or ""
            return _parse_response(_strip_thinking(raw))
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue

    # All retries exhausted
    if caption:
        return False, f"[IMAGE DESCRIPTION FAILED: {caption}]"
    return False, "[IMAGE DESCRIPTION FAILED: no caption]"
