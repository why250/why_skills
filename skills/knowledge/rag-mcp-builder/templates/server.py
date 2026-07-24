"""
RAG MCP Server

Provides hybrid BM25 + vector search over a local knowledge base via FastMCP stdio transport.

Tools:
  search_docs       — Hybrid search across all or a specific category
  list_categories   — Show available categories and chunk counts
  reindex_docs      — Force rebuild of the search index (prefer external terminal)

Configuration: edit config.py (project name, categories, paths).
Transport: stdio (Cursor launches this as a child process)
Logging:   stderr (does not pollute the MCP JSON-RPC channel)
"""

from __future__ import annotations

import logging
import sys
import textwrap
from typing import Annotated, Optional

from mcp.server.fastmcp import FastMCP

import config
import indexer
import retriever

# ---------------------------------------------------------------------------
# Logging — write to stderr only
# ---------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format=f"[{config.PROJECT_NAME}-mcp] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------
_category_list = ", ".join(sorted(config.CATEGORIES.keys()))
_category_details = "\n".join(
    f"  {name:<15} — {config.CATEGORY_DESCRIPTIONS.get(name, '')}"
    for name in sorted(config.CATEGORIES.keys())
)

mcp = FastMCP(
    name=config.PROJECT_NAME,
    instructions=textwrap.dedent(f"""\
        You have access to the {config.PROJECT_NAME} knowledge base.

        Available categories:
{_category_details}

        Usage tips:
          - Use search_docs for any question; add category= to narrow results.
          - Use list_categories to check what knowledge is indexed and chunk counts.
          - Use reindex_docs only if index is stale (prefer running build_index.py externally).
    """),
)

# ---------------------------------------------------------------------------
# Startup check — lightweight, NO model loading, keeps cold start < 1 second
# ---------------------------------------------------------------------------

def _check_index_ready() -> None:
    """Verify the index exists without loading the embedding model."""
    import chromadb
    from chromadb.config import Settings

    chroma_dir = indexer.CHROMA_DIR
    if not chroma_dir.exists():
        logger.warning(
            "Index not found. Run build_index.py first:\n"
            '  python "%s/build_index.py"',
            indexer._HERE,
        )
        return

    client = chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=Settings(anonymized_telemetry=False),
    )
    try:
        col   = client.get_collection(indexer.COLLECTION_NAME)
        count = col.count()
        bm25_ok = indexer.BM25_PATH.exists()
        if count > 0:
            logger.info(
                "Index ready: %d chunks in ChromaDB | BM25=%s.",
                count,
                "OK" if bm25_ok else "MISSING (run build_index.py)",
            )
        else:
            logger.warning("ChromaDB collection is empty. Run build_index.py to populate it.")
    except Exception:
        logger.warning(
            "Index not found or empty. Run build_index.py:\n"
            '  python "%s/build_index.py"',
            indexer._HERE,
        )


_check_index_ready()
logger.info("%s MCP server ready.", config.PROJECT_NAME)


# ---------------------------------------------------------------------------
# Tool: search_docs
# ---------------------------------------------------------------------------

_VALID_CATEGORIES = set(config.CATEGORIES.keys())


@mcp.tool()
def search_docs(
    query: Annotated[
        str,
        "Natural-language question or keywords to search for in the knowledge base",
    ],
    category: Annotated[
        Optional[str],
        f"Optional category filter. One of: {_category_list}. "
        "Leave empty to search all categories.",
    ] = None,
    n_results: Annotated[int, "Number of results to return (1–15, default 8)"] = 8,
) -> str:
    """
    Hybrid BM25 + semantic search with RRF fusion.

    Returns ranked results with source file, category, and chunk text.
    Add category= to limit search to a specific domain.
    """
    n_results = max(1, min(n_results, 15))

    if category and category not in _VALID_CATEGORIES:
        return (
            f"Invalid category '{category}'.\n"
            f"Valid options: {', '.join(sorted(_VALID_CATEGORIES))}\n"
            "Use list_categories() to see available categories with chunk counts."
        )

    results = retriever.hybrid_search(query, category=category, n_results=n_results)

    if not results:
        cat_hint = f" in category '{category}'" if category else ""
        return (
            f"No results found{cat_hint} for: \"{query}\"\n\n"
            "Suggestions:\n"
            "  - Rephrase the query or try different keywords\n"
            "  - Remove the category filter to search all documentation\n"
            "  - Ensure build_index.py has been run (check index with list_categories)"
        )

    lines: list[str] = [f"Found {len(results)} result(s) for: \"{query}\"\n"]
    for i, r in enumerate(results, start=1):
        cat_label = f"[{r['category']}]"
        mod_label = f" ({r['module']})" if r.get("module") else ""
        lines.append(f"--- Result {i} | {cat_label}{mod_label} | {r['source']} ---")
        text = r["text"]
        if len(text) > 2000:
            text = text[:2000] + "\n... [truncated]"
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: list_categories
# ---------------------------------------------------------------------------

@mcp.tool()
def list_categories() -> str:
    """
    List available knowledge base categories with chunk counts.

    Use this to understand what is indexed and choose the right category for search_docs.
    """
    stats = retriever.get_category_stats()

    if not stats:
        return (
            "Index not built yet.\n"
            "Run build_index.py:\n"
            f'  python "{indexer._HERE / "build_index.py"}"'
        )

    total = sum(stats.values())
    lines: list[str] = [f"{config.PROJECT_NAME} knowledge base — {total} total chunks\n"]
    for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
        desc = config.CATEGORY_DESCRIPTIONS.get(cat, "")
        lines.append(f"  {cat:<15} {count:>6,} chunks  {('— ' + desc) if desc else ''}")

    lines.append(
        "\nUsage: search_docs(query, category=\"<name>\") to search within a category."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: reindex_docs
# ---------------------------------------------------------------------------

@mcp.tool()
def reindex_docs() -> str:
    """
    Force a full rebuild of the search index.

    WARNING: Takes several minutes and uses ~500-800 MB RAM at peak.

    RECOMMENDED: Run build_index.py in an external terminal instead:
      python "path/to/mcp_server/build_index.py"
    """
    logger.info("Reindex requested via MCP tool.")
    try:
        stats = indexer.rebuild()
        total = sum(stats.values())
        lines: list[str] = [f"Re-indexing complete. {total} total chunks.\n"]
        for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat}: {count:,} chunks")
        return "\n".join(lines)
    except Exception as exc:
        logger.exception("Reindex failed.")
        return (
            f"Reindex failed: {exc}\n\n"
            "Recommended: run build_index.py in an external terminal:\n"
            f'  python "{indexer._HERE / "build_index.py"}"'
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
