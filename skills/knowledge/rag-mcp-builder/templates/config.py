"""
config.py — RAG MCP Configuration

This is THE ONLY FILE you need to edit for a new knowledge base.
All other files (server.py, indexer.py, retriever.py, build_index.py) import from here.

Quick setup:
  1. Set PROJECT_NAME to something unique (used as ChromaDB collection name + MCP server name)
  2. Set DATA_ROOT if your mcp_server/ is not one level inside the project root
  3. Define CATEGORIES — one entry per searchable domain
  4. Optionally add CATEGORY_DESCRIPTIONS for nicer list_categories() output
"""

from pathlib import Path

# ── Core settings ─────────────────────────────────────────────────────────────

PROJECT_NAME = "my-kb"
# Used as ChromaDB collection name and FastMCP server name.
# Must be unique per machine if you run multiple RAG MCP servers.
# Use lowercase letters, numbers, and hyphens only.

DATA_ROOT = Path(__file__).parent.parent
# Root of the project. Defaults to one level above mcp_server/.
# Adjust if your layout differs, e.g.:
#   DATA_ROOT = Path("C:/Users/me/my-project")

# ── Category definitions ───────────────────────────────────────────────────────
#
# Each key becomes a valid value for search_docs(category=...).
# Fields:
#   paths            — list of directories to scan (recursively)
#   extensions       — file suffixes to include (e.g. [".md", ".txt"] or [".py"])
#   chunk_strategy   — "whole_file" | "heading"
#                      whole_file: each file = one chunk (best for small focused files)
#                      heading:    split at ##/### Markdown headings (best for long docs)
#   chunk_size       — max characters per chunk (ignored for whole_file, set to 0)
#                      guidance: 800-1200 for tutorials, 1500-2000 for API docs
#   child_chunk_size — (optional) enables parent-child retrieval mode.
#                      When set, chunk_size is the PARENT size (returned to LLM for context)
#                      and child_chunk_size is the CHILD size (used for embedding/matching).
#                      Child chunks are ~3-5x smaller than the parent. Good default: 300.
#                      Omit (or set to None/0) to use standard single-level chunking.
#   module_field     — (optional, default False) if True, stores the parent directory
#                      name as a "module" label in search results

CATEGORIES: dict[str, dict] = {
    # Example: Markdown documentation files with parent-child retrieval
    "docs": {
        "paths":            [DATA_ROOT / "processed" / "docs"],
        "extensions":       [".md"],
        "chunk_strategy":   "heading",
        "chunk_size":       1200,      # parent chunk size (context returned to LLM)
        "child_chunk_size": 300,       # optional: enables parent-child mode
    },

    # Example: Python code examples — whole_file, no parent-child needed
    "examples": {
        "paths":          [DATA_ROOT / "raw_data" / "examples"],
        "extensions":     [".py"],
        "chunk_strategy": "whole_file",
        "chunk_size":     0,
    },

    # Example: API reference (larger chunks, parent-child optional)
    # "api": {
    #     "paths":            [DATA_ROOT / "processed" / "api"],
    #     "extensions":       [".md"],
    #     "chunk_strategy":   "heading",
    #     "chunk_size":       2000,
    #     "child_chunk_size": 400,    # optional: enable parent-child
    #     "module_field":     True,   # shows (subdir-name) label in results
    # },
}

# ── Human-readable descriptions (optional) ────────────────────────────────────
#
# Shown by list_categories(). Any category not listed here shows an empty description.

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "docs":     "Documentation pages",
    "examples": "Code examples",
    # "api":    "API reference",
}
