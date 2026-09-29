---
name: marker-pdf-to-md
description: Use when converting a PDF or PDF page range to Markdown with marker, extracting a PDF section by known pages, or troubleshooting marker PDF-to-Markdown work in this repository.
---

# Marker PDF to Markdown

## Overview
Use `marker`'s Python API by default. Prefer `PdfConverter` with `ConfigParser` for page ranges and `save_output()` for writing the markdown, `_meta.json`, and extracted images together.

## When to Use
- The user asks to convert a PDF to Markdown.
- The user asks for a single page, page range, or section from a PDF.
- The user mentions `marker`, `pdf -> md`, OCR, or extracted PDF images/metadata.
- The user needs help diagnosing why `marker` conversion fails in this repo.

Do not default to local LLM/Ollama enhancements unless the user explicitly asks for them.

## Default Workflow
1. Confirm the PDF path and whether the user wants a whole document, page range, or known section pages.
2. Resolve Python via config file (see [reference.md](reference.md) → **Environment & Config**):
   - Read `.agent/config/marker-pdf-env.json`
   - Validate; if missing or stale → detect and re-save config automatically
3. Use the Python API recipe from [reference.md](reference.md):
   - `ConfigParser(...)` for `output_format`, `output_dir`, and optional `page_range`
   - `PdfConverter(...)` for conversion
   - `save_output(...)` for final files
4. Save outputs under `reference/output/<task-name>/` unless the user gives a different destination.
5. Return the markdown path first. Then mention `_meta.json` and any extracted images if relevant.

## Output Convention
- Use a stable task-specific directory under `reference/output/`.
- Let `save_output()` create:
  - `<base>.md`
  - `<base>_meta.json`
  - extracted images beside the markdown

## Quality Defaults
- Start with the default non-LLM conversion path.
- Only suggest OCR/LLM escalation when the output is clearly degraded or the user explicitly asks.
- If the user asks for Ollama, only use models with `vision` capability.

## Troubleshooting
- If config file imports fail, the most common issue is a moved/removed Python environment. Delete `.agent/config/marker-pdf-env.json` and re-run — it will auto-detect and re-save.
- On Windows with Python 3.14, `marker`'s `Pillow<11` dependency can be awkward. Prefer a validated environment first if one already exists.
- Treat `_meta.json` as metadata/debug output, not the main deliverable.

## Additional Resources
- API recipes and environment checks: [reference.md](reference.md)
- Example requests and expected handling: [examples.md](examples.md)
