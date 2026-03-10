"""
prompt_llm.py — Reads gist.md; decides page count; outputs page_N_content.json with style tokens.

Style tokens use {{global.key}} and {{grade.key}} syntax — never hardcoded values.
Writes: output/grade_N/module_M/topic_T/page_N_content.json
"""

import json
import re
from pathlib import Path

import litellm

ROOT = Path(__file__).parent

REQUIRED_FIELDS = {
    "page", "topic", "layout_type", "title", "subtitle",
    "style", "sections", "image_prompt",
}

VALID_LAYOUT_TYPES = {
    "concept_intro", "two_section_comparison", "multi_column",
    "process_flow", "analogy_anchor",
}

EXPECTED_TOKENS = [
    "{{global.illustration_style}}",
    "{{global.aspect_ratio}}",
    "{{global.font_style}}",
    "{{global.layout_language}}",
    "{{grade.background_color}}",
    "{{grade.primary_color}}",
    "{{grade.accent_color}}",
    "{{grade.mood}}",
    "{{grade.complexity_level}}",
]

_STYLE_KEYS = {
    "illustration_style", "aspect_ratio", "font_style", "layout_language",
    "background_color", "primary_color", "accent_color", "mood", "complexity_level",
}

_TOKEN_RE = re.compile(r"^\{\{(global|grade)\.\w+\}\}$")

_STYLE_TOKENS = {
    "illustration_style": "{{global.illustration_style}}",
    "aspect_ratio":       "{{global.aspect_ratio}}",
    "font_style":         "{{global.font_style}}",
    "layout_language":    "{{global.layout_language}}",
    "background_color":   "{{grade.background_color}}",
    "primary_color":      "{{grade.primary_color}}",
    "accent_color":       "{{grade.accent_color}}",
    "mood":               "{{grade.mood}}",
    "complexity_level":   "{{grade.complexity_level}}",
}


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks produced by reasoning models."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _looks_truncated(s: str) -> bool:
    """True if the raw output appears cut off (no closing brace/bracket at end)."""
    tail = s.rstrip()
    return bool(tail) and tail[-1] not in ("}", "]")


def _load_style_configs(grade: int) -> tuple:
    """Load global_style.json and grade_N_style.json. Returns (global_cfg, grade_cfg)."""
    global_cfg = json.loads((ROOT / "configs" / "global_style.json").read_text(encoding="utf-8"))
    grade_cfg = json.loads((ROOT / "configs" / f"grade_{grade}_style.json").read_text(encoding="utf-8"))
    return global_cfg, grade_cfg


def _normalize_page(page: dict, global_cfg: dict, grade_cfg: dict) -> dict:
    """
    Enforce token compliance on style and image_prompt fields.

    1. Forcibly replaces page["style"] with the correct token object.
    2. In page["image_prompt"], substitutes known config values with their tokens.
    3. Appends any still-missing tokens to image_prompt as a style-spec suffix.

    Called after JSON parsing and before validation so validation can pass.
    """
    # Force-set style to correct tokens regardless of what the model wrote
    page["style"] = dict(_STYLE_TOKENS)

    # Build value→token replacement map from runtime configs
    value_to_token = {
        global_cfg.get("illustration_style", ""): "{{global.illustration_style}}",
        global_cfg.get("aspect_ratio", ""):        "{{global.aspect_ratio}}",
        global_cfg.get("font_style", ""):          "{{global.font_style}}",
        global_cfg.get("layout_language", ""):     "{{global.layout_language}}",
        grade_cfg.get("background_color", ""):     "{{grade.background_color}}",
        grade_cfg.get("primary_color", ""):        "{{grade.primary_color}}",
        grade_cfg.get("accent_color", ""):         "{{grade.accent_color}}",
        grade_cfg.get("mood", ""):                 "{{grade.mood}}",
        grade_cfg.get("complexity_level", ""):     "{{grade.complexity_level}}",
    }
    value_to_token.pop("", None)  # remove any empty-key entries

    if "image_prompt" in page:
        img = page["image_prompt"]
        for val, tok in value_to_token.items():
            img = img.replace(val, tok)
        # Append any tokens still missing after substitution
        missing_tokens = [t for t in EXPECTED_TOKENS if t not in img]
        if missing_tokens:
            img = img + ". Style: " + ", ".join(missing_tokens) + "."
        page["image_prompt"] = img

    return page


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """Load configs/llm_config.json relative to this file."""
    return json.loads((ROOT / "configs" / "llm_config.json").read_text(encoding="utf-8"))


def _load_system_prompt() -> str:
    """Load prompts/prompt_system_prompt.md relative to this file."""
    return (ROOT / "prompts" / "prompt_system_prompt.md").read_text(encoding="utf-8")


def _sanitize_control_chars(s: str) -> str:
    """
    Escape literal control characters (ASCII < 0x20) inside JSON string values.

    qwen3:8b sometimes emits a bare newline or tab directly inside a JSON string
    instead of the required escape sequence (\\n, \\t), causing JSONDecodeError:
    'Invalid control character'. Walks char-by-char tracking string context.
    """
    _escapes = {'\n': '\\n', '\r': '\\r', '\t': '\\t', '\b': '\\b', '\f': '\\f'}
    result = []
    in_string = False
    escape_next = False
    for ch in s:
        if escape_next:
            result.append(ch)
            escape_next = False
        elif ch == '\\' and in_string:
            result.append(ch)
            escape_next = True
        elif ch == '"':
            result.append(ch)
            in_string = not in_string
        elif in_string and ord(ch) < 0x20:
            result.append(_escapes.get(ch, f'\\u{ord(ch):04x}'))
        else:
            result.append(ch)
    return ''.join(result)


def _parse_pages(raw: str) -> list:
    """Split raw LLM output on '---' separator lines and parse each chunk as JSON."""
    chunks = re.split(r"^\s*---\s*$", raw, flags=re.MULTILINE)
    return [json.loads(_sanitize_control_chars(chunk.strip())) for chunk in chunks if chunk.strip()]


def _validate_page(page: dict) -> list:
    """Return a list of validation error strings (empty list = valid)."""
    errors = []

    # Required top-level fields
    missing = REQUIRED_FIELDS - set(page.keys())
    if missing:
        errors.append(f"Missing required fields: {sorted(missing)}")

    # layout_type
    if "layout_type" in page and page["layout_type"] not in VALID_LAYOUT_TYPES:
        errors.append(f"Invalid layout_type: {page['layout_type']!r}")

    # style tokens
    if "style" in page:
        style = page["style"]
        for key in _STYLE_KEYS:
            if key not in style:
                errors.append(f"style missing key: {key!r}")
            elif not _TOKEN_RE.match(str(style[key])):
                errors.append(f"style.{key} is not a valid token: {style[key]!r}")

    # sections schema
    if "sections" in page:
        for i, sec in enumerate(page["sections"]):
            for field in ("heading", "body", "visual_hint"):
                if field not in sec:
                    errors.append(f"sections[{i}] missing {field!r}")

    # image_prompt must contain all 9 tokens
    if "image_prompt" in page:
        img = page["image_prompt"]
        for token in EXPECTED_TOKENS:
            if token not in img:
                errors.append(f"image_prompt missing token: {token}")

    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_content_jsons(
    gist_md: str,
    grade: int,
    module: int,
    topic: int,
    output_path,
) -> list:
    """
    Generate page_N_content.json files for a single topic via an Ollama LLM.

    If page_1_content.json already exists at output_path, all existing page files
    are returned immediately without calling the LLM (skip logic).

    On JSON parse failure the call is retried once with an explicit JSON reminder.
    Parsed pages are validated for required fields and style token correctness.

    Args:
        gist_md:     Content of gist.md for the topic.
        grade:       Grade number (e.g. 6). Prepended to the user message.
        module:      Module number (1-indexed).
        topic:       Topic number (1-indexed).
        output_path: Directory where page_N_content.json files are written.
                     Created automatically if it does not exist.

    Returns:
        List of JSON strings (raw file contents), one per page.
    """
    output_path = Path(output_path)

    # Skip logic: if page_1_content.json exists, load and return all existing pages
    page_1 = output_path / "page_1_content.json"
    if page_1.exists():
        result = []
        n = 1
        while True:
            p = output_path / f"page_{n}_content.json"
            if not p.exists():
                break
            result.append(p.read_text(encoding="utf-8"))
            n += 1
        return result

    config = _load_config()
    system_prompt = _load_system_prompt()
    cfg = config["prompt_llm"]
    global_cfg, grade_cfg = _load_style_configs(grade)

    user_msg = f"Grade: {grade}\n\n{gist_md}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_msg},
    ]

    # num_ctx gives qwen3-family thinking models enough context window to finish
    # internal reasoning AND still produce full JSON output.
    _ollama_opts = {"options": {"num_ctx": cfg["num_ctx"]}}

    response = litellm.completion(
        model=f"ollama/{cfg['model']}",
        messages=messages,
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
        api_base=config["base_url"],
        extra_body=_ollama_opts,
    )
    raw = _strip_thinking(response.choices[0].message.content)
    messages_so_far = messages

    # Up to 1 retry for either parse failure or validation failure
    for attempt in range(2):
        try:
            pages = _parse_pages(raw)
        except (json.JSONDecodeError, ValueError):
            if attempt == 1:
                raise
            if _looks_truncated(raw):
                # Output was cut off mid-JSON (likely hit max_tokens during thinking).
                # Start fresh — don't pass the truncated output back; it only wastes context.
                retry_messages = messages_so_far
            else:
                retry_messages = messages_so_far + [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": (
                            "Your response contained invalid JSON. "
                            "Output only valid JSON objects separated by --- on its own line. "
                            "No extra text before the first { or after the last }."
                        ),
                    },
                ]
            response2 = litellm.completion(
                model=f"ollama/{cfg['model']}",
                messages=retry_messages,
                temperature=cfg["temperature"],
                max_tokens=cfg["max_tokens"],
                api_base=config["base_url"],
                extra_body=_ollama_opts,
            )
            raw = _strip_thinking(response2.choices[0].message.content)
            continue

        # Normalize style tokens before validation (model may have used hardcoded values)
        pages = [_normalize_page(p, global_cfg, grade_cfg) for p in pages]

        # Validate all pages
        all_errors = []
        for i, page in enumerate(pages):
            errs = _validate_page(page)
            if errs:
                all_errors.append(f"Page {i + 1}:\n" + "\n".join(errs))

        if not all_errors:
            break  # all pages valid

        if attempt == 1:
            raise ValueError("Page validation failed after retry:\n" + "\n\n".join(all_errors))

        # Retry with specific validation errors
        error_summary = "\n\n".join(all_errors)
        retry_messages = messages_so_far + [
            {"role": "assistant", "content": raw},
            {
                "role": "user",
                "content": (
                    f"Your JSON output failed validation:\n\n{error_summary}\n\n"
                    "Fix ALL errors above. layout_type must be one of: "
                    "concept_intro, two_section_comparison, multi_column, "
                    "process_flow, analogy_anchor. "
                    "All 9 style fields must use {{global.*}} or {{grade.*}} tokens. "
                    "image_prompt must contain all 9 tokens. "
                    "Output only the corrected JSON."
                ),
            },
        ]
        response2 = litellm.completion(
            model=f"ollama/{cfg['model']}",
            messages=retry_messages,
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
            api_base=config["base_url"],
            extra_body=_ollama_opts,
        )
        raw = _strip_thinking(response2.choices[0].message.content)

    output_path.mkdir(parents=True, exist_ok=True)
    result = []
    for i, page in enumerate(pages, 1):
        json_str = json.dumps(page, indent=2, ensure_ascii=False)
        (output_path / f"page_{i}_content.json").write_text(json_str, encoding="utf-8")
        result.append(json_str)
    return result
