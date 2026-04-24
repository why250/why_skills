# RAG MCP Builder — Reference

## `config.py` Full Schema

```python
from pathlib import Path

# ── Required ──────────────────────────────────────────────────────────────────

PROJECT_NAME = "my-kb"
# Used as:
#   - ChromaDB collection name (must be unique per server on the same machine)
#   - FastMCP server name (shown in Cursor's MCP panel)
#   - Log prefix

DATA_ROOT = Path(__file__).parent.parent
# Typically one level up from mcp_server/. Adjust if your layout differs.

CATEGORIES: dict[str, dict] = {
    "category-name": {
        # Required fields:
        "paths":          [DATA_ROOT / "path/to/files"],   # list of directories
        "extensions":     [".md"],                          # file suffixes to index
        "chunk_strategy": "heading",                        # see Chunk Strategies below
        "chunk_size":     1200,                             # max chars (ignored for whole_file)
        # Optional fields:
        "child_chunk_size": 300,  # enables parent-child mode; see Parent-Child Retrieval below
        "module_field":   False,  # if True, stores parent dir name as 'module' metadata
    },
}

# ── Optional ──────────────────────────────────────────────────────────────────

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "category-name": "Human-readable description shown by list_categories()",
}
# Defaults to empty string for any category not listed here.
```

## Chunk Strategies

| Strategy | `chunk_size` | Best for | How it splits |
|---|---|---|---|
| `whole_file` | ignored (set to 0) | Small focused files: function refs, code examples, FAQ entries | Each file = exactly 1 chunk |
| `heading` | 800–2000 chars | Structured Markdown docs with `##`/`###` headers | Splits at `##`/`###` boundaries; falls back to char-level if section > chunk_size |
| _(char fallback)_ | any | Overlong sections within `heading` strategy | Snaps to sentence/newline boundaries with 200-char overlap |

### Chunk Size Guidelines

| Content type | Recommended `chunk_size` |
|---|---|
| AEL / API function references (each file = 1 function) | `whole_file` |
| Code examples (.py scripts) | `whole_file` |
| Tutorial / guide pages | 1000–1500 |
| API reference docs (many methods per page) | 1500–2000 |
| Dense technical specs | 1200 |

Too small (< 500): chunks lack context, retrieval degrades.
Too large (> 3000): chunks overwhelm the context window when returned.

## Category Design Tips

**One category = one retrieval domain.** Users can call `search_docs(query, category="x")` to narrow scope.

Good category splits:
- By content type: `docs`, `examples`, `api`
- By topic: `tutorial`, `reference`, `changelog`
- By source: `official_docs`, `internal_wiki`, `code`

Avoid too many fine-grained categories (> 8); users won't remember them all.

**File-per-function pattern**: If each source file contains exactly one concept (one function, one FAQ entry, one tutorial step), use `whole_file`. This gives the cleanest retrieval — the chunk IS the answer.

## Multiple Input Paths per Category

A category can pull from multiple directories:

```python
CATEGORIES = {
    "api": {
        "paths": [
            DATA_ROOT / "processed" / "sphinx_txt",
            DATA_ROOT / "processed" / "docstring_extracts",
        ],
        "extensions": [".md"],
        "chunk_strategy": "heading",
        "chunk_size": 2000,
    },
}
```

Files from all paths are merged into the same category and searchable together.

## Module Metadata

Set `"module_field": True` for categories where the parent directory carries semantic meaning (e.g. `sphinx_txt/de/`, `sphinx_txt/dds/`). This stores the immediate parent directory name in the `module` metadata field, surfaced in search results as `(de)`, `(dds)`, etc.

```python
"api": {
    "paths":        [DATA_ROOT / "processed" / "sphinx_txt"],
    "extensions":   [".md"],
    "chunk_strategy": "heading",
    "chunk_size":   2000,
    "module_field": True,   # enables (de), (dds), etc. labels in results
},
```

## Parent-Child Retrieval

When `child_chunk_size` is set on a category, that category uses **parent-child** retrieval instead of single-level chunking. This improves search quality by separating precision (matching) from context (reading).

| Role | Size | Purpose |
|---|---|---|
| **Child chunk** | `child_chunk_size` chars (e.g. 300) | Embedded into ChromaDB + BM25; used for precise matching |
| **Parent chunk** | `chunk_size` chars (e.g. 1200) | Stored in `parent_store.json`; returned to the LLM as context |

When a query matches multiple child chunks from the same parent, they are merged into a single result (the parent text). Results with more child hits rank higher.

### When to enable it

Enable parent-child when your documents contain sections that are dense enough to match on small spans but need surrounding context to be useful. This is common in:
- Long Markdown tutorials with subsections
- API reference pages with multiple method descriptions per page
- Technical specs with numbered steps

Avoid it for `whole_file` categories and very short files — there is no benefit when each file is already a single chunk.

### Configuration example

```python
"docs": {
    "paths":            [DATA_ROOT / "processed" / "docs"],
    "extensions":       [".md"],
    "chunk_strategy":   "heading",
    "chunk_size":       1200,       # parent size returned to LLM
    "child_chunk_size": 300,        # child size used for matching
},
```

### Child chunk size guidelines

| `chunk_size` (parent) | Recommended `child_chunk_size` |
|---|---|
| 800 | 200 |
| 1200 | 300 |
| 2000 | 400–500 |

Rule of thumb: child should be roughly 1/4 of the parent size.

### Output file

`parent_store.json` is created alongside `bm25_index.pkl` when at least one category has `child_chunk_size` set. Add it to `.gitignore`:

```gitignore
mcp_server/parent_store.json
```

## Index Files — What to Gitignore

```gitignore
mcp_server/chroma_db/
mcp_server/bm25_index.pkl
mcp_server/category_stats.json
mcp_server/file_manifest.json
mcp_server/parent_store.json
```

These are all auto-regenerated by `build_index.py`.

## `mcp.json` Registration Patterns

### Minimal (Python in PATH)
```json
{
  "mcpServers": {
    "my-kb": {
      "command": "python",
      "args": ["C:/path/to/my-kb/mcp_server/server.py"]
    }
  }
}
```

### With virtual environment (Windows)
```json
{
  "mcpServers": {
    "my-kb": {
      "command": "C:/path/to/my-kb/.venv/Scripts/python.exe",
      "args": ["C:/path/to/my-kb/mcp_server/server.py"]
    }
  }
}
```

### With virtual environment (macOS/Linux)
```json
{
  "mcpServers": {
    "my-kb": {
      "command": "/path/to/my-kb/.venv/bin/python",
      "args": ["/path/to/my-kb/mcp_server/server.py"]
    }
  }
}
```

### With environment variables
```json
{
  "mcpServers": {
    "my-kb": {
      "command": "python",
      "args": ["C:/path/to/my-kb/mcp_server/server.py"],
      "env": {
        "MY_DATA_PATH": "C:/path/to/data"
      }
    }
  }
}
```

## Troubleshooting

### "Index not found" on server startup
Run `build_index.py` first. The server starts fine without an index (logs a warning), but search will return empty results.

### `DuplicateIDError` in ChromaDB
This means two different files produced the same chunk hash. This skill uses `MD5(source_path|chunk_idx)` IDs (not content-based), so this should not happen. If it does, ensure no two files have identical relative paths across `CATEGORIES`.

### BM25 index missing / out of date
Run `build_index.py --incremental`. This rebuilds BM25 from existing ChromaDB text without re-embedding anything.

### ONNX model download fails (offline environment)
Pre-download the model and set the cache path:
```bash
# On a machine with internet:
python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction; DefaultEmbeddingFunction()"
# Copy %USERPROFILE%\.cache\chroma\onnx_models\ to the offline machine
```

### Server cold start is slow
The ONNX model loads lazily on the first `search_docs` call, not at startup. Cold start should be < 1 second. If startup is slow, check for large `chroma_db/` that needs migration.

### Results are irrelevant
1. Check `list_categories()` — are chunks being indexed?
2. Try without `category=` filter (searches all)
3. Rephrase query — BM25 is keyword-sensitive; try synonyms
4. Check `chunk_size` — very large chunks dilute the embedding signal

## Updating an Existing ADS2025_help Project to Use This Template

The template `config.py` introduces a new `CATEGORIES` schema (dict of dicts) that differs from the ADS project's flat structure. To migrate:

**Old ADS structure (in indexer.py):**
```python
CATEGORIES = {"ael": [path1, path2], "python_api": [path3]}
MAX_CHUNK_CHARS = {"ael": 0, "python_api": 2000}
CATEGORY_SUFFIXES = {"ael": {".md"}, "python_api": {".md"}}
```

**New template structure (in config.py):**
```python
CATEGORIES = {
    "ael":        {"paths": [path1, path2], "extensions": [".md"], "chunk_strategy": "whole_file", "chunk_size": 0},
    "python_api": {"paths": [path3],        "extensions": [".md"], "chunk_strategy": "heading",    "chunk_size": 2000},
}
```

The template `indexer.py` derives `MAX_CHUNK_CHARS` and `CATEGORY_SUFFIXES` automatically from the new `CATEGORIES` dict.
