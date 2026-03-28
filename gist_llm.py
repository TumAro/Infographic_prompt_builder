"""
gist_llm.py — One LLM call per subtopic; assembles gist.md (subtopic summaries).

Called by pipeline.py once per subtopic via generate_subtopic_gist().
File I/O (writing gist.md) is handled by pipeline.py.
"""

import json
import re
from pathlib import Path

import litellm

ROOT = Path(__file__).parent


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks produced by reasoning models."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _is_valid_subtopic_gist(text: str) -> bool:
    """Return True if text starts with a ## heading and has no template placeholder text."""
    has_heading = bool(re.search(r"^##\s+\S", text, re.MULTILINE))
    is_template = bool(re.search(r"\[Reproduce|\[One sentence|\[A student", text))
    return has_heading and not is_template


def _load_config() -> dict:
    """Load configs/llm_config.json relative to this file."""
    return json.loads((ROOT / "configs" / "llm_config.json").read_text(encoding="utf-8"))


def _load_system_prompt() -> str:
    """Load prompts/gist_system_prompt.md relative to this file."""
    return (ROOT / "prompts" / "gist_system_prompt.md").read_text(encoding="utf-8")


def _build_user_message(topic_name: str, subtopic_name: str, subtopic_raw: str, grade: int) -> str:
    """
    Format a single subtopic's raw markdown text for the LLM.

    Format:
        Grade: 7
        Topic: Functions in Programming

        ## Subtopic: What is a Function?

        <verbatim lines from topic.md>
    """
    return (
        f"Grade: {grade}\n"
        f"Topic: {topic_name}\n\n"
        f"## Subtopic: {subtopic_name}\n\n"
        f"{subtopic_raw}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_subtopic_gist(
    topic_name: str,
    subtopic_name: str,
    subtopic_raw: str,
    grade: int,
) -> str:
    """
    Generate a gist section for a single subtopic via an Ollama LLM.

    Called once per subtopic by pipeline.py. File I/O (assembling and writing
    the final gist.md) is handled by the caller.

    Args:
        topic_name:    Name of the parent topic (included for LLM context).
        subtopic_name: Name of this subtopic.
        subtopic_raw:  Verbatim markdown text of this subtopic from topic.md.
        grade:         Grade number (e.g. 7). Used to calibrate reading level.

    Returns:
        A markdown string beginning with '## <subtopic name>' followed by
        the summarised content for that subtopic.
    """
    config = _load_config()
    system_prompt = _load_system_prompt()
    user_message = _build_user_message(topic_name, subtopic_name, subtopic_raw, grade)

    gist_cfg = config["gist_llm"]
    _ollama_opts = {"options": {"num_ctx": gist_cfg["num_ctx"]}}
    response = litellm.completion(
        model=f"ollama/{gist_cfg['model']}",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=gist_cfg["temperature"],
        max_tokens=gist_cfg["max_tokens"],
        api_base=config["base_url"],
        extra_body=_ollama_opts,
    )
    gist_text = _strip_thinking(response.choices[0].message.content)

    if not _is_valid_subtopic_gist(gist_text):
        retry_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
            {"role": "assistant", "content": gist_text},
            {
                "role": "user",
                "content": (
                    "Your output did not follow the required format. "
                    "Start your response with '## <subtopic name>' (double-hash heading). "
                    "Do not use bold text (**) as headings. "
                    "Output ONLY the correctly formatted subtopic gist now."
                ),
            },
        ]
        response2 = litellm.completion(
            model=f"ollama/{gist_cfg['model']}",
            messages=retry_messages,
            temperature=gist_cfg["temperature"],
            max_tokens=gist_cfg["max_tokens"],
            api_base=config["base_url"],
            extra_body=_ollama_opts,
        )
        gist_text = _strip_thinking(response2.choices[0].message.content)

    if not gist_text:
        raise ValueError(
            f"gist_llm: model '{gist_cfg['model']}' returned empty output for subtopic "
            f"'{subtopic_name}' after retry. "
            "Try increasing max_tokens or switching to a non-reasoning model in llm_config.json."
        )

    if not _is_valid_subtopic_gist(gist_text):
        raise ValueError(
            f"gist_llm: model '{gist_cfg['model']}' returned invalid format for subtopic "
            f"'{subtopic_name}' after retry. "
            "Output is missing required '## SubtopicName' heading. "
            "Check the model's instruction-following capability."
        )

    return gist_text
