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
2. Check the active Python interpreter before suggesting installs:
   - `python -c "import sys; print(sys.executable)"`
   - `python -m pip show marker-pdf`
3. Validate core imports in the same interpreter:
   - `python -c "import marker, pydantic, pdftext, surya, cv2"`
4. Use the Python API recipe from [reference.md](reference.md):
   - `ConfigParser(...)` for `output_format`, `output_dir`, and optional `page_range`
   - `PdfConverter(...)` for conversion
   - `save_output(...)` for final files
5. Save outputs under `reference/output/<task-name>/` unless the user gives a different destination.
6. Return the markdown path first. Then mention `_meta.json` and any extracted images if relevant.

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
- If imports fail, the most common issue is using a different `python` than the one where packages were installed.
- If `pydantic`, `pdftext`, `surya`, or `cv2` is missing, install into the current interpreter, not a different Python on the machine.
- On Windows with Python 3.14, `marker`'s `Pillow<11` dependency can be awkward. Prefer a validated environment first if one already exists.
- Treat `_meta.json` as metadata/debug output, not the main deliverable.

## Additional Resources
- API recipes and environment checks: [reference.md](reference.md)
- Example requests and expected handling: [examples.md](examples.md)
