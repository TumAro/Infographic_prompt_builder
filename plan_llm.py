"""
plan_llm.py — Iterative visual storyboard planner; assembles plan.md.

Called by pipeline.py once per topic via generate_topic_plan().
Iterates subtopics one at a time: each LLM call receives the current
running plan plus the next subtopic's full verbatim content, then returns
the full updated plan. File I/O (writing plan.md) is handled by pipeline.py.
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


def _is_valid_plan(text: str) -> bool:
    """Return True if text contains at least one ## Page N heading."""
    return bool(re.search(r"^##\s+Page\s+\d+", text, re.MULTILINE))


def _load_config() -> dict:
    """Load configs/llm_config.json relative to this file."""
    return json.loads((ROOT / "configs" / "llm_config.json").read_text(encoding="utf-8"))


def _load_system_prompt() -> str:
    """Load prompts/plan_system_prompt.md relative to this file."""
    return (ROOT / "prompts" / "plan_system_prompt.md").read_text(encoding="utf-8")


def _build_user_message(
    plan_so_far: str,
    topic_name: str,
    subtopic_name: str,
    subtopic_raw: str,
    grade: int,
) -> str:
    """
    Build the user message for one planning iteration.

    Format:
        Grade: 8
        Topic: Understanding Supervised Learning

        Plan so far:
        <current plan.md content, or "(none — this is the first subtopic)">

        Next subtopic to plan: What is Supervised Learning?

        <verbatim subtopic markdown>
    """
    plan_block = plan_so_far if plan_so_far else "(none — this is the first subtopic)"
    return (
        f"Grade: {grade}\n"
        f"Topic: {topic_name}\n\n"
        f"Plan so far:\n{plan_block}\n\n"
        f"Next subtopic to plan: {subtopic_name}\n\n"
        f"{subtopic_raw}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_topic_plan(
    topic_name: str,
    subtopics: list,
    grade: int,
) -> str:
    """
    Generate a complete visual storyboard plan for a topic.

    Iterates subtopics one at a time using a cumulative running-plan approach.
    Each LLM call receives:
        - The current running plan (compact, structured decisions so far)
        - The next subtopic's full verbatim content from topic.md

    The LLM returns the full updated plan after each subtopic. Context window
    stays bounded: system + plan_so_far + one_subtopic_content.

    Args:
        topic_name: Name of the parent topic.
        subtopics:  List of (subtopic_name, subtopic_raw_markdown) tuples,
                    in the order they appear in topic.md.
        grade:      Grade number (6–12). Used to calibrate visual complexity.

    Returns:
        Complete plan.md string containing ## Page N headings and full
        visual storyboard details for all subtopics.
    """
    if not subtopics:
        raise ValueError(
            f"plan_llm: no subtopics provided for topic '{topic_name}'."
        )

    config = _load_config()
    system_prompt = _load_system_prompt()
    plan_cfg = config["plan_llm"]
    ollama_opts = {"options": {"num_ctx": plan_cfg["num_ctx"]}}

    plan_so_far = ""
    total = len(subtopics)

    for idx, (subtopic_name, subtopic_raw) in enumerate(subtopics, start=1):
        print(f"      [plan] {idx}/{total} — {subtopic_name}")
        user_message = _build_user_message(
            plan_so_far, topic_name, subtopic_name, subtopic_raw, grade
        )

        response = litellm.completion(
            model=f"ollama/{plan_cfg['model']}",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=plan_cfg["temperature"],
            max_tokens=plan_cfg["max_tokens"],
            api_base=config["base_url"],
            extra_body=ollama_opts,
        )
        plan_text = _strip_thinking(response.choices[0].message.content)

        if not _is_valid_plan(plan_text):
            retry_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
                {"role": "assistant", "content": plan_text},
                {
                    "role": "user",
                    "content": (
                        "Your output did not include a valid page heading. "
                        "The plan must contain at least one '## Page N — \"Title\"' heading. "
                        "Output ONLY the complete, correctly formatted updated plan now."
                    ),
                },
            ]
            response2 = litellm.completion(
                model=f"ollama/{plan_cfg['model']}",
                messages=retry_messages,
                temperature=plan_cfg["temperature"],
                max_tokens=plan_cfg["max_tokens"],
                api_base=config["base_url"],
                extra_body=ollama_opts,
            )
            plan_text = _strip_thinking(response2.choices[0].message.content)

        if not plan_text:
            raise ValueError(
                f"plan_llm: model '{plan_cfg['model']}' returned empty output "
                f"while planning subtopic '{subtopic_name}'. "
                "Try increasing max_tokens or switching models in llm_config.json."
            )

        if not _is_valid_plan(plan_text):
            raise ValueError(
                f"plan_llm: model '{plan_cfg['model']}' returned invalid plan "
                f"for subtopic '{subtopic_name}' after retry. "
                "Output is missing required '## Page N' heading. "
                "Check the model's instruction-following capability."
            )

        plan_so_far = plan_text

    return plan_so_far
