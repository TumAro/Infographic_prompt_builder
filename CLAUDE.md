# AI Infographic Picture Book Generator

Automated pipeline that converts AI/ML textbook `.docx` files (Grades 6–9) into
structured JSON image prompts for Nano Banana (Gemini image generation). One
infographic page per topic; complex topics may span multiple pages.

## Architecture

```
doc_parser → gist_llm → [gist.md] → prompt_llm → [page_N_content.json] → resolver → [page_N_final.json]
```

- **doc_parser.py** — Parses syllabus + module `.docx` files into structured in-memory dicts
- **gist_llm.py** — One LLM call per topic; outputs `gist.md` (subtopic summaries + synopsis)
- **prompt_llm.py** — Reads `gist.md`; decides page count; outputs `page_N_content.json` with style tokens
- **resolver.py** — No LLM; merges content JSON + style configs → `page_N_final.json`. Re-run after config edits without regenerating prompts.
- **pipeline.py** — CLI orchestrator with skip logic

## Project Structure

```
project/
├── pipeline.py
├── doc_parser.py
├── gist_llm.py
├── prompt_llm.py
├── resolver.py
├── prompts/
│   ├── gist_system_prompt.md       # System prompt for gist LLM
│   └── prompt_system_prompt.md     # System prompt for prompt LLM
├── configs/
│   ├── llm_config.json             # Provider, model, temperature, max_tokens
│   ├── global_style.json           # Illustration style, aspect ratio, font
│   ├── grade_6_style.json          # Colors, mood, complexity per grade
│   ├── grade_7_style.json
│   ├── grade_8_style.json
│   └── grade_9_style.json
├── data/
│   └── grade_6/
│       ├── Class_6.docx            # Syllabus: topic/subtopic map
│       └── Module_1_-_What_is_Artificial_Intelligence.docx
└── output/
    └── grade_6/
        └── module_1/
            └── topic_1/
                ├── gist.md                 # Intermediate — inspectable/editable
                ├── page_1_content.json     # Style tokens (LLM output, stable)
                ├── page_1_final.json       # Resolved — Nano Banana ready
                └── page_2_*.json           # If multi-page topic
```

## Key Conventions

**Style tokens** in `page_N_content.json` use `{{global.key}}` and `{{grade.key}}` syntax.
The resolver replaces all tokens. Never hardcode style values in LLM output.

**Skip logic in pipeline.py:**
- `gist.md` exists → skip `gist_llm` (override: `--force-gist`)
- `page_N_content.json` exists → skip `prompt_llm` (override: `--force-prompt`)
- resolver always runs (cheap, no LLM)

**Doc parsing** relies on text-pattern matching against syllabus topic/subtopic names.
All paragraphs in module `.docx` files use `Normal` style — no heading hierarchy.
Content block types: `paragraph`, `bullet`, `story`, `fun_fact`, `activity`,
`figure_caption`, `image_caption`, `table`.

## CLI

```bash
python pipeline.py                                    # all grades
python pipeline.py --grade 6                          # all modules in grade
python pipeline.py --grade 6 --module 1               # all topics in module
python pipeline.py --grade 6 --module 1 --topic 2     # single topic
python resolver.py --grade 6 --module 1 --topic 2     # re-resolve after config edit
```

## Tech Stack

- **Python 3.11+**
- **python-docx** — `.docx` parsing
- **litellm** — unified LLM interface (provider: Ollama, `base_url: http://localhost:11434`)
- **Configs**: JSON only (llm_config, global_style, grade_N_style)
- **System prompts**: `.md` files in `prompts/`

## LLM Config Shape

```json
{
  "provider": "ollama",
  "base_url": "http://localhost:11434",
  "gist_llm": { "model": "llama3.1", "temperature": 0.3, "max_tokens": 2048 },
  "prompt_llm": { "model": "llama3.1", "temperature": 0.7, "max_tokens": 4096 }
}
```

## Style Config Shape

`global_style.json`: `illustration_style`, `aspect_ratio`, `font_style`, `layout_language`
`grade_N_style.json`: `background_color`, `primary_color`, `accent_color`, `mood`, `complexity_level`

## Data Naming Convention

- Data folders: `grade_6/`, `grade_7/` etc.
- Module inferred from filename prefix `Module_N_`
- Output folders: `output/grade_6/module_1/topic_1/`
- Topic numbered from syllabus table order (1-indexed)