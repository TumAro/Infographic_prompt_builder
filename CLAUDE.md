# AI Infographic Picture Book Generator

Automated pipeline that converts AI/ML textbook `.docx` files (Grades 6–12) into
structured JSON image prompts for Nano Banana (Gemini image generation). One
infographic page per topic; complex topics may span multiple pages.

## Architecture

```
[book writer .md files]            [.docx files]
        │                               │
book_md_adapter.py             doc_parser.py + vision_llm.py
(Phase 0, --from-book mode)    (Phase 1, --parse-raw mode)
        │                               │
        └───────────┬───────────────────┘
                    ▼
      [topic.md in structured_data/]
                    │
           md_parser (iter_subtopics)
                    │
               plan_llm ──► [plan.md]
                    │
            prompt_llm ──► [page_N_content.json]
                    │
             resolver ──► [page_N_final.json]
```

- **doc_parser.py** — Reads `.docx` files; writes `structured_data/grade_N/module_N/topic_N/topic.md`
- **vision_llm.py** — Called inline by doc_parser for embedded images; returns `(is_code, description)` tuple; code images saved to `code_images/` subdirectory
- **book_md_adapter.py** — Reads `book_output/grade_N/module_M/topic_M.T.md`; converts to `topic.md` format; writes to `structured_data/`; no LLM calls
- **md_parser.py** — Reads `topic.md`; `iter_subtopics()` yields `(topic_name, subtopic_name, raw_markdown)` verbatim for plan_llm; `parse_topic_md()` reconstructs the dict format
- **plan_llm.py** — Iterative visual storyboard planner; processes subtopics one at a time; each call receives running plan + one subtopic's raw markdown and returns the full updated plan; outputs `plan.md`
- **prompt_llm.py** — Reads `plan.md`; decides page count; outputs `page_N_content.json` with style tokens
- **resolver.py** — No LLM; merges content JSON + style configs → `page_N_final.json`
- **pipeline.py** — CLI orchestrator with skip logic and two-phase operation

### Standalone Modules (not in main pipeline)

- **gist_llm.py** — One LLM call per subtopic; outputs `gist.md` (subtopic summaries + synopsis). Removed from main pipeline but still available as a standalone tool.

## Project Structure

```
project/
├── pipeline.py
├── doc_parser.py
├── vision_llm.py
├── md_parser.py
├── plan_llm.py
├── gist_llm.py
├── prompt_llm.py
├── resolver.py
├── prompts/
│   ├── plan_system_prompt.md
│   ├── prompt_system_prompt.md
│   ├── gist_system_prompt.md        # Used by standalone gist_llm only
│   └── vision_system_prompt.md      # System prompt for vision LLM
├── configs/
│   ├── llm_config.json              # Provider, model, temperature, max_tokens
│   ├── global_style.json
│   ├── grade_6_style.json           # Colors, mood, complexity per grade
│   ├── grade_7_style.json
│   ├── grade_8_style.json
│   ├── grade_9_style.json
│   └── omml2mml.xsl                 # Optional: OMML→MathML XSLT for equation conversion
├── data/
│   └── grade_6/
│       ├── Class_6.docx             # Syllabus: topic/subtopic map
│       └── Module_1_-_What_is_Artificial_Intelligence.docx
├── structured_data/                  # Phase 1 output (human-readable/editable)
│   └── grade_6/
│       └── module_1/
│           └── topic_1/
│               └── topic.md
└── output/                           # Phase 2 output (Nano Banana ready)
    └── grade_6/
        └── module_1/
            └── topic_1/
                ├── plan.md
                ├── page_1_content.json
                └── page_1_final.json
```

## Book Writer Input Mode

When input comes from a Book Writer system instead of `.docx` files, use `--from-book`:

```bash
# Single topic from book writer output
python pipeline.py --from-book book_output/grade_8/module_1/topic_1.2.md

# Whole module from book writer output
python pipeline.py --from-book book_output/grade_8/module_1/

# Force re-adapt then regenerate plan only
python pipeline.py --from-book book_output/grade_8/module_1/topic_1.2.md \
  --force-adapt --force-plan --plan-only
```

### book_output/ folder convention

Book Writer files live at:
```
book_output/
└── grade_8/
    └── module_1/
        ├── topic_1.1.md
        ├── topic_1.2.md
        └── topic_1.3.md
```

Each file begins with YAML frontmatter:
```
---
subject: Computer Science
grade: 8
module: 1 — Introduction to Programming
topic: 1.2 — Variables and Data Types
---
```

### Format conversion table

| Book Writer format | Pipeline topic.md format |
|---|---|
| `# M.T Topic Name` | `# Topic: Topic Name` |
| `## Any Subtopic Heading` | `## Subtopic: Any Subtopic Heading` |
| `### Worked Example` + prose + code block | `> **[Code Figure N]** Worked Example: {heading}` |
| `[IMAGE]` / `Description: ...` / `Caption: ...` | `> **[Figure N]** {description}` + `> *Caption: {caption}*` |
| `Did You Know?` / `---` / `{fact}` | `> **Fun Fact:** {fact}` |
| `Think & Reflect` / `---` / `{question}` | `> **Activity:** {question}` |
| `Key Terms` / `---` / `Term: definition` lines | `- **Term**: definition` |
| `Practice Problems` / `---` / `1. ...` lines | keep as-is |
| All other prose | keep verbatim |
| YAML frontmatter | strip entirely |

Figure counter is global across the file. `[Figure N]` and `[Code Figure N]` share the same counter.

### Flags

- `--from-book PATH` — path to a single `topic_M.T.md` file or a folder
- `--force-adapt` — overwrite existing `topic.md` files; otherwise skip if exists
- `--grade`, `--module`, `--topic` — not required when `--from-book` is set (inferred from frontmatter)

### Legacy mode note

`doc_parser.py` and `vision_llm.py` remain fully functional for `.docx` input via `--parse-raw`. They are not used in `--from-book` mode.

## Key Conventions

**`topic.md` format** in `structured_data/`:
- `# Topic: {name}` at top
- `## Subtopic: {name}` per subtopic
- Bullets as `- text`, numbered lists as `1. text`
- Stories/analogies as `> text`
- Fun facts as `> **Fun Fact:** text`
- Activities as `> **Activity:** text`
- Tables as markdown tables
- Equations: `$...$` (inline) or `$$...$$` (block); `[EQUATION: conversion failed]` on error
- Images: `> **[Figure N]** {vision_llm output}` and `> *Caption: {caption}*`
- Code images: `> **[Code Figure N]** {description}` (saved to `code_images/` subdirectory)

**`plan.md` format** in `output/`:
```
# Plan: {Topic Name}
Grade: {N} | Pages: {N}

---

## Page N — "{Page Title}"
**Layout:** layout_type
**Covers:** Subtopic Name(s)

**Visual narrative:** [spatial description]

**Content to show:** [full content preservation]

**Sections:**
1. Heading — [content + visual directions]
...

**Callout:** [Fun Fact | Story | Activity | None]
```

**Equation conversion** requires `configs/omml2mml.xsl` (Microsoft OMML→MathML XSLT).
Place this file to enable conversion; without it every equation writes `[EQUATION: conversion failed]`.

**Style tokens** in `page_N_content.json` use `{{global.key}}` and `{{grade.key}}` syntax.
The resolver replaces all tokens. Never hardcode style values in LLM output.

**Skip logic:**
- `topic.md` exists → skip `book_md_adapter` (override: `--force-adapt`)
- `topic.md` exists → skip `doc_parser` (override: `--force-parse`)
- `plan.md` exists → skip `plan_llm` (override: `--force-plan`)
- `page_N_content.json` exists → skip `prompt_llm` (override: `--force-prompt`)
- `resolver` always runs (cheap, no LLM)
- `gist.md` exists → skip `gist_llm` *(standalone only; not in main pipeline)*

**Doc parsing** relies on text-pattern matching against syllabus topic/subtopic names.
All paragraphs in module `.docx` files use `Normal` style — no heading hierarchy.

## CLI

```bash
# Phase 1 — build structured_data/ (call vision_llm for images)
python pipeline.py --parse-raw                                  # all grades
python pipeline.py --parse-raw --grade 6 --module 1 --topic 1  # single topic
python pipeline.py --parse-raw --force-parse                    # overwrite existing topic.md

# Phase 2 — generate output/ (structured_data/ must exist first)
python pipeline.py --grade 6 --module 1 --topic 1
python pipeline.py --grade 6 --module 1
python pipeline.py --grade 6
python pipeline.py

# Force-regenerate specific stages
python pipeline.py --grade 6 --module 1 --topic 1 --force-plan    # regenerate plan.md
python pipeline.py --grade 6 --module 1 --topic 1 --force-prompt  # regenerate page_N_content.json
python pipeline.py --grade 6 --module 1 --topic 1 --plan-only     # stop after plan.md

# Re-resolve after config edits only
python resolver.py --grade 6 --module 1 --topic 2

# Book writer input mode
python pipeline.py --from-book book_output/grade_8/module_1/topic_1.2.md
python pipeline.py --from-book book_output/grade_8/module_1/
python pipeline.py --from-book book_output/grade_8/module_1/topic_1.2.md --force-adapt --force-plan --plan-only
```

## Tech Stack

- **Python 3.11+**
- **python-docx** — `.docx` parsing
- **litellm** — unified LLM interface (provider: Ollama, `base_url: http://localhost:11434`)
- **lxml** — OMML→MathML equation conversion (optional; install with `pip install lxml`)
- **Configs**: JSON only (llm_config, global_style, grade_N_style)
- **System prompts**: `.md` files in `prompts/`

## LLM Config Shape

```json
{
  "provider": "ollama",
  "base_url": "http://localhost:11434",
  "plan_llm":   { "model": "gpt-oss:20b", "temperature": 0.7, "max_tokens": 4096, "num_ctx": 16384 },
  "prompt_llm": { "model": "gpt-oss:20b", "temperature": 0.5, "max_tokens": 4096, "num_ctx": 16384 },
  "vision_llm": { "model": "qwen3-vl:8b", "temperature": 0.2, "max_tokens": 2048 }
}
```

## Style Config Shape

`global_style.json`: `illustration_style`, `aspect_ratio`, `font_style`, `layout_language`
`grade_N_style.json`: `background_color`, `primary_color`, `accent_color`, `mood`, `complexity_level`

## Data Naming Convention

- Data folders: `grade_6/`, `grade_7/` etc.
- Module inferred from filename prefix `Module_N_`
- `structured_data/` folders: `structured_data/grade_6/module_1/topic_1/`
- Output folders: `output/grade_6/module_1/topic_1/`
- Topic numbered from syllabus table order (1-indexed)
