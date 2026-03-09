"""
gist_llm.py — One LLM call per topic; outputs gist.md (subtopic summaries + synopsis).

Reads parsed module content from doc_parser.
Writes: output/grade_N/module_M/topic_T/gist.md
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


def _is_valid_gist(text: str) -> bool:
    """Return True if text contains at least one ## subtopic header and ## Synopsis."""
    has_subtopic = bool(re.search(r"^##\s+\S", text, re.MULTILINE))
    has_synopsis = bool(re.search(r"^##\s+Synopsis", text, re.MULTILINE | re.IGNORECASE))
    return has_subtopic and has_synopsis


def _load_config() -> dict:
    """Load configs/llm_config.json relative to this file."""
    return json.loads((ROOT / "configs" / "llm_config.json").read_text(encoding="utf-8"))


def _load_system_prompt() -> str:
    """Load prompts/gist_system_prompt.md relative to this file."""
    return (ROOT / "prompts" / "gist_system_prompt.md").read_text(encoding="utf-8")


def _format_user_message(topic_content: dict, grade: int) -> str:
    """
    Convert a topic_content dict into labeled block text for the LLM.

    Format:
        Grade: 6

        # Topic Name

        ## Subtopic Name

        [paragraph] Text of paragraph.
        [story] Once upon a time...
        [table]
        Col1 | Col2
        Val1 | Val2

        ## Next Subtopic
        ...
    """
    lines: list = [f"Grade: {grade}", "", f"# {topic_content['topic']}", ""]

    for subtopic in topic_content["subtopics"]:
        lines.append(f"## {subtopic['name']}")
        lines.append("")
        for block in subtopic["blocks"]:
            btype = block["type"]
            if btype == "table":
                lines.append("[table]")
                for row in block.get("rows", []):
                    lines.append(" | ".join(str(cell) for cell in row))
            else:
                lines.append(f"[{btype}] {block['text']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_gist(topic_content: dict, grade: int, output_path) -> str:
    """
    Generate gist.md for a single topic via an Ollama LLM.

    If gist.md already exists at output_path, it is returned immediately without
    calling the LLM (skip logic). Delete the file or pass --force-gist via the
    pipeline CLI to regenerate.

    Args:
        topic_content: Dict from doc_parser.get_topic_content() with keys
                       "topic" (str) and "subtopics" (list of dicts).
        grade:         Grade number (e.g. 6). Added to the user message so the
                       LLM can calibrate reading level.
        output_path:   Directory path where gist.md will be written.
                       Created automatically if it does not exist.

    Returns:
        The gist markdown string (loaded from cache or freshly generated).
    """
    output_path = Path(output_path)
    gist_path = output_path / "gist.md"

    # Skip logic: return cached file if present
    if gist_path.exists():
        return gist_path.read_text(encoding="utf-8")

    config = _load_config()
    system_prompt = _load_system_prompt()
    user_message = _format_user_message(topic_content, grade)

    gist_cfg = config["gist_llm"]
    response = litellm.completion(
        model=f"ollama/{gist_cfg['model']}",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=gist_cfg["temperature"],
        max_tokens=gist_cfg["max_tokens"],
        api_base=config["base_url"],
    )
    gist_text = _strip_thinking(response.choices[0].message.content)

    if not _is_valid_gist(gist_text):
        retry_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
            {"role": "assistant", "content": gist_text},
            {
                "role": "user",
                "content": (
                    "Your output did not follow the required format. "
                    "You MUST use '## Subtopic Name' (double-hash) for each subtopic section "
                    "and end with a '## Synopsis' section. "
                    "Do not use bold text (**) as headings. Do not write prose paragraphs. "
                    "Output ONLY the correctly formatted gist.md now."
                ),
            },
        ]
        response2 = litellm.completion(
            model=f"ollama/{gist_cfg['model']}",
            messages=retry_messages,
            temperature=gist_cfg["temperature"],
            max_tokens=gist_cfg["max_tokens"],
            api_base=config["base_url"],
        )
        gist_text = _strip_thinking(response2.choices[0].message.content)

    if not gist_text:
        raise ValueError(
            f"gist_llm: model '{gist_cfg['model']}' returned empty output after retry. "
            "The model may be consuming all tokens in <think> blocks. "
            "Try increasing max_tokens or switching to a non-reasoning model in llm_config.json."
        )

    output_path.mkdir(parents=True, exist_ok=True)
    gist_path.write_text(gist_text, encoding="utf-8")
    return gist_text
