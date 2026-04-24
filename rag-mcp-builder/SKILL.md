---
name: rag-mcp-builder
description: Build a local RAG MCP service (ChromaDB vector search + BM25 keyword search + RRF fusion) from any knowledge base — HTML docs, Python packages, plain text, code examples. Use when building a knowledge base MCP, setting up local document search, creating an offline RAG system, or asking "how do I make my docs searchable in Cursor".
---

# RAG MCP Builder

Bootstraps a fully working RAG MCP service from any knowledge base. The service exposes `search_docs`, `list_categories`, and `reindex_docs` tools to Cursor via stdio transport.

Architecture: ChromaDB (ONNX all-MiniLM-L6-v2, cosine) + BM25 (rank-bm25) + RRF fusion. No PyTorch required — ONNX model is ~45 MB, auto-downloaded on first run.

Reference project: `d:\Users\Documents\GitHub\ADS2025_help\` (ADS 2025 documentation, 12k+ chunks).

## Workflow (5 steps)

### Step 1 — Organize raw data

Place source files under `raw_data/` grouped by intended category:

```
my-kb/
├── raw_data/
│   ├── docs/          ← HTML, Markdown, or text files
│   ├── examples/      ← Code files (.py, .js, etc.)
│   └── api/           ← Python package source (.py/.pyi)
└── mcp_server/        ← created in Step 3
```

**Data preparation scripts** (in this skill's `scripts/` folder):

```bash
# Convert HTML docs → Markdown (MadCap Flare or Sphinx HTML)
python path/to/skill/scripts/clean_html.py \
    --input raw_data/html_docs \
    --output processed/docs \
    --format madcap   # or: sphinx

# Extract Python docstrings → Markdown
python path/to/skill/scripts/extract_docstrings.py \
    --input raw_data/my_package \
    --output processed/api
```

Both scripts are stand-alone; install `beautifulsoup4 lxml` for the HTML cleaner.

### Step 2 — Define categories in `config.py`

Copy `templates/config.py` to `my-kb/mcp_server/config.py` and edit:

```python
PROJECT_NAME = "my-kb"          # ChromaDB collection name + MCP server name
DATA_ROOT    = Path(__file__).parent.parent

CATEGORIES = {
    "docs": {
        "paths":            [DATA_ROOT / "processed" / "docs"],
        "extensions":       [".md"],
        "chunk_strategy":   "heading",   # split at ## / ### boundaries
        "chunk_size":       1200,        # parent chunk size (returned to LLM)
        "child_chunk_size": 300,         # optional: enables parent-child retrieval
    },
    "examples": {
        "paths":          [DATA_ROOT / "raw_data" / "examples"],
        "extensions":     [".py"],
        "chunk_strategy": "whole_file",  # each file = one chunk
        "chunk_size":     0,
    },
    "api": {
        "paths":          [DATA_ROOT / "processed" / "api"],
        "extensions":     [".md"],
        "chunk_strategy": "heading",
        "chunk_size":     2000,        # larger for API docs
    },
}

# Shown by list_categories() tool
CATEGORY_DESCRIPTIONS = {
    "docs":     "Documentation pages",
    "examples": "Code examples",
    "api":      "API reference",
}
```

Chunk strategies:
- `whole_file` — entire file = one chunk; best for small focused files (AEL functions, code examples)
- `heading` — split at `##`/`###` Markdown headings; best for structured docs

Optional: `child_chunk_size` — enables parent-child retrieval. Child chunks (~300 chars) are indexed for precise matching; parent chunks (`chunk_size` chars) are returned to the LLM for richer context. Omit to use standard single-level chunking. See [reference.md](reference.md) → Parent-Child Retrieval.
- `sliding` — not built-in; fall back to `heading` with a large `chunk_size`

See [reference.md](reference.md) for full config options and chunk size guidance.

### Step 3 — Copy templates to `mcp_server/`

```bash
# From this skill's templates/ folder, copy all files to your project
cp templates/config.py     my-kb/mcp_server/config.py       # ← edit this
cp templates/server.py     my-kb/mcp_server/server.py       # generic, no edits needed
cp templates/indexer.py    my-kb/mcp_server/indexer.py      # generic
cp templates/retriever.py  my-kb/mcp_server/retriever.py    # generic
cp templates/build_index.py my-kb/mcp_server/build_index.py # generic
cp templates/requirements.txt my-kb/mcp_server/requirements.txt
```

After copying, `mcp_server/` should look like:
```
mcp_server/
├── config.py          ← only file you edit
├── server.py
├── indexer.py
├── retriever.py
├── build_index.py
└── requirements.txt
```

The generated index files (`chroma_db/`, `bm25_index.pkl`, etc.) are created by Step 4.

### Step 4 — Build the index

```bash
cd my-kb/mcp_server
pip install -r requirements.txt

# Full build (first time, ~3-6 min depending on corpus size):
python build_index.py

# After adding/modifying a few files (10-30 sec):
python build_index.py --incremental
```

Expected output files:
- `chroma_db/` — ChromaDB persistent vector store
- `bm25_index.pkl` — BM25 keyword index
- `category_stats.json` — chunk counts per category
- `file_manifest.json` — mtime cache for incremental updates
- `parent_store.json` — parent texts for parent-child categories (omitted if none)

Add these to `.gitignore` (they are large and auto-regeneratable).

### Step 5 — Register in Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "my-kb": {
      "command": "python",
      "args": ["C:/path/to/my-kb/mcp_server/server.py"],
      "env": {}
    }
  }
}
```

Then reload Cursor (or use Settings → MCP → reload). Verify the server shows a green indicator.

Test:
```
search_docs("your query here")
list_categories()
```

## Incremental updates

After adding new files to any `raw_data/` or `processed/` path:

```bash
python build_index.py --incremental
```

Incremental update only re-embeds new/changed files (detected by mtime). BM25 is rebuilt from existing ChromaDB text without re-embedding.

## Memory notes

- Peak RAM during full build: ~500-800 MB (ONNX + ChromaDB + BM25)
- ChromaDB upsert batch size: 100 (keeps memory flat)
- ONNX model (~45 MB) is cached at `%USERPROFILE%\.cache\chroma\onnx_models\` after first run
- Do NOT use `sentence-transformers` (requires PyTorch, 2-3 GB)

## Additional resources

- [reference.md](reference.md) — full config options, chunk strategies, category design tips, mcp.json patterns
