---
name: pdf-to-markdown
description: >-
  Converts PDF files (datasheets, manuals, application notes, papers) to
  AI-readable Markdown using pymupdf4llm. Preserves tables as pipe tables and
  headings as Markdown headings. Use when asked to convert a PDF to Markdown,
  make a PDF easier for AI to read, extract content from a PDF for LLM
  consumption, or when the user mentions "PDF转MD"、"PDF转Markdown"、"把PDF转成文字"。
---

# PDF to Markdown

Converts digital PDFs to clean Markdown using **pymupdf4llm** — rule-based, no GPU, ~0.5s/page.

> Best for: technical datasheets, instrument manuals, application notes, spec sheets.  
> Not ideal for: scanned/image-only PDFs (use marker instead — see [when-to-use-marker](#when-to-use-marker)).

## Setup

```bash
# uv (recommended)
uv add pymupdf4llm

# or pip
pip install pymupdf4llm
```

Copy the bundled script to your project:

```
scripts/pdf_to_markdown.py   ← from this skill's scripts/ folder
```

## Usage

```bash
# Convert entire PDF (output: same folder, same name, .md extension)
uv run python scripts/pdf_to_markdown.py path/to/file.pdf

# Custom output path
uv run python scripts/pdf_to_markdown.py path/to/file.pdf --output notes/file.md

# Convert specific pages only
uv run python scripts/pdf_to_markdown.py path/to/file.pdf --pages 1-5
uv run python scripts/pdf_to_markdown.py path/to/file.pdf --pages 1,3,5-10
```

## What the script does

- Calls `pymupdf4llm.to_markdown()` with `table_strategy="lines_strict"` to produce pipe tables
- Shows a tqdm progress bar (suppress with `--no-progress`)
- Prints elapsed time and output file size on completion
- Output is UTF-8 encoded Markdown

## Output quality

Tables are converted to standard Markdown pipe tables:

```markdown
| Model    | Bandwidth | Sample Rate |
|----------|-----------|-------------|
| UXR1104A | 110 GHz   | 256 GSa/s   |
```

Images are replaced with `**==> picture [W x H] intentionally omitted <==**`.

## When to use Marker

Use [marker](https://github.com/datalab-to/marker) instead when:

- PDF is scanned / image-only (needs OCR)
- Document contains math equations (marker converts to LaTeX)
- Complex multi-column layout (academic papers)
- You need structured JSON output for RAG chunking

Marker requires PyTorch (~2-3 GB) and is significantly slower on CPU.

## Additional resources

- [pymupdf4llm docs](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/)
- [marker GitHub](https://github.com/datalab-to/marker)
