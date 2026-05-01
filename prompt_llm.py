"""
prompt_llm.py — Reads plan.md; outputs page_N_content.json with style tokens.

One LLM call per page. Each page is validated and written immediately.
Per-page skip logic: if page_N_content.json already exists it is loaded and
the LLM is not called for that page. Partial runs resume automatically.

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
    "style", "sections", "callout", "image_prompt",
}

VALID_LAYOUT_TYPES = {
    "concept_intro", "two_section_comparison", "multi_column",
    "process_flow", "analogy_anchor",
}

VALID_CALLOUT_TYPES = {"fun_fact", "activity", "story", "none"}

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

    # callout schema
    if "callout" in page:
        co = page["callout"]
        if not isinstance(co, dict):
            errors.append("callout must be an object")
        else:
            for field in ("type", "text", "visual_hint"):
                if field not in co:
                    errors.append(f"callout missing key: {field!r}")
            if "type" in co and co["type"] not in VALID_CALLOUT_TYPES:
                errors.append(
                    f"callout.type invalid: {co['type']!r}. "
                    f"Must be one of {sorted(VALID_CALLOUT_TYPES)}"
                )

    # image_prompt must contain all 9 tokens
    if "image_prompt" in page:
        img = page["image_prompt"]
        for token in EXPECTED_TOKENS:
            if token not in img:
                errors.append(f"image_prompt missing token: {token}")

    return errors


def _consolidate_callouts(block: str) -> str:
    """
    If a page block has more than one **Callout:** line, keep only the first one
    and its corresponding **Callout visual:** line. Remove subsequent callout pairs.

    Defensive guardrail: plan_llm should never emit two callouts per page, but if
    it does, this ensures prompt_llm receives a single unambiguous callout.
    """
    lines = block.splitlines(keepends=True)
    callout_indices = [i for i, l in enumerate(lines) if l.startswith("**Callout:**")]
    if len(callout_indices) <= 1:
        return block
    to_remove: set[int] = set()
    for idx in callout_indices[1:]:
        to_remove.add(idx)
        if idx + 1 < len(lines) and lines[idx + 1].startswith("**Callout visual:**"):
            to_remove.add(idx + 1)
    return "".join(l for i, l in enumerate(lines) if i not in to_remove)


def _split_plan_pages(plan_text: str) -> list:
    """
    Split plan_text on '## Page N' headings.
    Returns [(page_num, block_text), ...] in order.
    """
    pattern = re.compile(r"^(## Page \d+.*)", re.MULTILINE)
    matches = list(pattern.finditer(plan_text))
    if not matches:
        return []
    pages = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(plan_text)
        block = _consolidate_callouts(plan_text[start:end].strip())
        page_num = int(re.search(r"## Page (\d+)", m.group()).group(1))
        pages.append((page_num, block))
    return pages


def _extract_topic_name(plan_text: str) -> str:
    """Extract topic name from '# Plan: {Topic Name}' header."""
    m = re.search(r"^# Plan:\s*(.+)", plan_text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _build_page_user_message(
    grade: int,
    topic_name: str,
    page_num: int,
    total_pages: int,
    page_block: str,
) -> str:
    """Build the user message for a single page call."""
    return (
        f"Grade: {grade}\n"
        f"Topic: {topic_name}\n"
        f"Page: {page_num} of {total_pages}\n\n"
        f"{page_block}"
    )


def _generate_single_page(
    messages: list,
    cfg: dict,
    config: dict,
    global_cfg: dict,
    grade_cfg: dict,
    page_num: int,
) -> dict:
    """
    Make one LLM call for a single page block. Parse, normalize, validate.
    Retries once on parse or validation failure. Raises ValueError on second failure.
    """
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

    for attempt in range(2):
        # Parse
        try:
            # Extract JSON: find first { and last }
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                raise json.JSONDecodeError("No JSON object found", raw, 0)
            page = json.loads(_sanitize_control_chars(raw[start:end]))
        except (json.JSONDecodeError, ValueError) as exc:
            if attempt == 1:
                raise ValueError(f"Page {page_num}: JSON parse failed after retry: {exc}") from exc
            if _looks_truncated(raw):
                retry_messages = messages
            else:
                retry_messages = messages + [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": (
                            "Your response contained invalid JSON. "
                            "Output only a single valid JSON object. "
                            "No extra text before { or after }."
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

        # Normalize style tokens
        page = _normalize_page(page, global_cfg, grade_cfg)

        # Validate
        errors = _validate_page(page)
        if not errors:
            return page

        if attempt == 1:
            raise ValueError(
                f"Page {page_num}: validation failed after retry:\n" + "\n".join(errors)
            )

        error_summary = "\n".join(errors)
        retry_messages = messages + [
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
                    "Output only the corrected JSON object."
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

    # Should never reach here — loop always returns or raises
    raise ValueError(f"Page {page_num}: unexpected exit from retry loop")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_content_jsons(
    plan_text: str,
    grade: int,
    module: int,
    topic: int,
    output_path,
    target_pages: set | None = None,
) -> list:
    """
    Generate page_N_content.json files for a single topic via per-page LLM calls.

    One LLM call is made per page block in plan_text. Each page is validated and
    written to disk immediately. Per-page skip logic: if page_N_content.json already
    exists it is loaded without calling the LLM. Partial runs resume automatically.

    Args:
        plan_text:   Content of plan.md for the topic.
        grade:       Grade number (e.g. 6).
        module:      Module number (1-indexed).
        topic:       Topic number (1-indexed).
        output_path: Directory where page_N_content.json files are written.
                     Created automatically if it does not exist.

    Returns:
        List of JSON strings (raw file contents), one per page, in page order.
    """
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    config = _load_config()
    system_prompt = _load_system_prompt()
    cfg = config["prompt_llm"]
    global_cfg, grade_cfg = _load_style_configs(grade)

    topic_name = _extract_topic_name(plan_text)
    page_blocks = _split_plan_pages(plan_text)
    total = len(page_blocks)

    result = []
    for page_num, block in page_blocks:
        if target_pages is not None and page_num not in target_pages:
            continue  # not targeted — leave existing file untouched

        out_file = output_path / f"page_{page_num}_content.json"

        if out_file.exists():
            print(f"    [skip] page_{page_num}_content.json already exists")
            result.append(out_file.read_text(encoding="utf-8"))
            continue

        print(f"    [prompt] Generating page {page_num} of {total}...")
        user_msg = _build_page_user_message(grade, topic_name, page_num, total, block)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ]

        page_dict = _generate_single_page(
            messages, cfg, config, global_cfg, grade_cfg, page_num
        )

        json_str = json.dumps(page_dict, indent=2, ensure_ascii=False)
        out_file.write_text(json_str, encoding="utf-8")
        result.append(json_str)

    return result
