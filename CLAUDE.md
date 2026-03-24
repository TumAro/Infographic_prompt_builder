# AI Infographic Picture Book Generator

Automated pipeline that converts AI/ML textbook `.docx` files (Grades 6–9) into
structured JSON image prompts for Nano Banana (Gemini image generation). One
infographic page per topic; complex topics may span multiple pages.

## Architecture

```
doc_parser ──────────────────────────────► [topic.md]
  └── vision_llm (inline, images only)        │
                                           md_parser
                                               │
                                           gist_llm ──► [gist.md]
                                               │
                                           prompt_llm ──► [page_N_content.json]
                                               │
                                           resolver ──► [page_N_final.json]
```

- **doc_parser.py** — Reads `.docx` files; writes `structured_data/grade_N/module_N/topic_N/topic.md`
- **vision_llm.py** — Called inline by doc_parser for embedded images; returns plain-text descriptions
- **md_parser.py** — Reads `topic.md`; reconstructs the dict that `gist_llm` expects
- **gist_llm.py** — One LLM call per topic; outputs `gist.md` (subtopic summaries + synopsis)
- **prompt_llm.py** — Reads `gist.md`; decides page count; outputs `page_N_content.json` with style tokens
- **resolver.py** — No LLM; merges content JSON + style configs → `page_N_final.json`
- **pipeline.py** — CLI orchestrator with skip logic and two-phase operation

## Project Structure

```
project/
├── pipeline.py
├── doc_parser.py
├── vision_llm.py
├── md_parser.py
├── gist_llm.py
├── prompt_llm.py
├── resolver.py
├── prompts/
│   ├── gist_system_prompt.md
│   ├── prompt_system_prompt.md
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
                ├── gist.md
                ├── page_1_content.json
                └── page_1_final.json
```

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

**Equation conversion** requires `configs/omml2mml.xsl` (Microsoft OMML→MathML XSLT).
Place this file to enable conversion; without it every equation writes `[EQUATION: conversion failed]`.

**Style tokens** in `page_N_content.json` use `{{global.key}}` and `{{grade.key}}` syntax.
The resolver replaces all tokens. Never hardcode style values in LLM output.

**Skip logic:**
- `topic.md` exists → skip `doc_parser` (override: `--force-parse`)
- `gist.md` exists → skip `gist_llm` (override: `--force-gist`)
- `page_N_content.json` exists → skip `prompt_llm` (override: `--force-prompt`)
- `resolver` always runs (cheap, no LLM)

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

# Re-resolve after config edits only
python resolver.py --grade 6 --module 1 --topic 2
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
  "gist_llm":   { "model": "qwen3:8b",  "temperature": 0.3, "max_tokens": 4096, "num_ctx": 16384 },
  "prompt_llm": { "model": "qwen3:8b",  "temperature": 0.7, "max_tokens": 4096, "num_ctx": 16384 },
  "vision_llm": { "model": "qwen3-vl",  "temperature": 0.2, "max_tokens": 1024 }
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
