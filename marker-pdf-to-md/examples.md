# Examples

## Convert One PDF to Markdown

**User asks:**  
`把 reference/foo.pdf 转成 md`

**Default handling:**
1. Confirm the PDF path.
2. Check the active Python interpreter and core imports.
3. Use the whole-document Python API recipe from `reference.md`.
4. Save under `reference/output/<task-name>/`.
5. Return the `.md` path first.

## Convert a Single Page

**User asks:**  
`把 reference/foo.pdf 的第 48 页转成 md`

**Default handling:**
1. Treat the user page number as 1-based.
2. Convert it to marker's zero-based page index (`48 -> 47`) when building `page_range`.
3. Use the page-range Python API recipe.
4. Save under a stable task-specific directory.

## Convert a Section by Known Pages

**User asks:**  
`把 4.3.1 General Model 小节（p75~p78）转成 md`

**Default handling:**
1. Confirm the page span if needed.
2. Convert `p75~p78` to marker page range `74-77`.
3. Use `ConfigParser` with `page_range`.
4. Save the section under a named output directory such as `reference/output/section_4_3_1_general_model/`.

## Missing Package in the Current Interpreter

**Symptom:**  
`ModuleNotFoundError: No module named 'pydantic'`

**Default handling:**
1. Check `python -c "import sys; print(sys.executable)"`.
2. Check `python -m pip show marker-pdf`.
3. Install packages into that same interpreter, not whichever Python happens to be first on the machine.

## Windows Multi-Python Pitfall

**Symptom:**  
`python` in one terminal points to a different interpreter than the environment where `marker` was installed.

**Default handling:**
1. Compare `python -c "import sys; print(sys.executable)"` and `where python`.
2. If needed, call the intended interpreter explicitly.
3. Re-run the import checks before attempting conversion again.

## Python 3.14 / Pillow Pitfall

**Symptom:**  
`pip install -e .` fails on Windows while building `Pillow 10.4.0`.

**Default handling:**
1. Prefer a previously validated environment first.
2. If the user insists on Python 3.14, explain that `marker`'s dependency pin may need a compatibility workaround.
3. Keep this as troubleshooting guidance, not the default setup path.

## Ollama Requests

**User asks:**  
`用本地 ollama 提高质量`

**Default handling:**
1. Do not enable Ollama by default.
2. First explain that only `vision` models are suitable for `marker`'s image-based LLM path.
3. If the user still wants it, treat it as an optional quality experiment rather than the primary workflow.
