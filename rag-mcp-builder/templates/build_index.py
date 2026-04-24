#!/usr/bin/env python3
"""
RAG MCP — Index Builder

Recommended: Run this script in an external terminal (not inside Cursor's embedded terminal).
Cursor IDE uses 1.5-2 GB RAM on its own; running the indexer inside Cursor can trigger
memory pressure, even with 32 GB RAM.

Usage:
    # Full rebuild (first time, or after large-scale data changes):
    python build_index.py

    # Incremental update (after adding/modifying a few files — much faster):
    python build_index.py --incremental

What this script does (full rebuild):
    1. Reads all source files from paths defined in config.CATEGORIES
    2. Chunks documents using heading-aware splitting (Markdown) or whole-file (code/small docs)
       For categories with child_chunk_size set: uses parent-child chunking (smaller child
       chunks go into the index; larger parent texts are stored in parent_store.json)
    3. Builds a ChromaDB vector index with ONNX all-MiniLM-L6-v2 (~45 MB, no PyTorch)
    4. Builds a BM25 keyword index
    5. Saves output files to mcp_server/

What --incremental does:
    - Reads file_manifest.json to find which files changed since last build (mtime-based)
    - Only re-embeds new/modified files
    - Rebuilds BM25 from existing ChromaDB text (no re-embedding needed)
    - Falls back to full rebuild if no manifest exists

Output files:
    chroma_db/             — ChromaDB vector store (HNSW, cosine similarity)
    bm25_index.pkl         — BM25 keyword index (rank_bm25, pickled)
    category_stats.json    — Chunk counts per category
    file_manifest.json     — File mtime cache for incremental updates
    parent_store.json      — Parent texts for parent-child categories (omitted if none)

Expected runtime (full):        3-10 minutes depending on corpus size
Expected runtime (incremental): 10-30 seconds when only a few files changed
Expected peak RAM:              ~500-800 MB (ONNX model + ChromaDB build + BM25)
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure mcp_server/ is on the path so we can import config, indexer
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="[build_index] %(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _verify_data_dirs() -> bool:
    """Check that all configured data directories exist before starting."""
    import config

    missing: list[Path] = []
    for category, cat_cfg in config.CATEGORIES.items():
        for path in cat_cfg.get("paths", []):
            if not Path(path).exists():
                missing.append(path)
                logger.error("  [%s] missing: %s", category, path)

    if missing:
        logger.error(
            "\nMissing %d required data directories.\n"
            "Populate them before building the index.\n"
            "See SKILL.md Step 1 for data preparation instructions.",
            len(missing),
        )
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAG MCP Index Builder",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help=(
            "Only process new/changed files; skip unchanged ones. "
            "Falls back to full rebuild if no manifest exists."
        ),
    )
    args = parser.parse_args()

    import config

    logger.info("=" * 60)
    logger.info("RAG MCP — Index Builder")
    logger.info("=" * 60)
    logger.info("Project      : %s", config.PROJECT_NAME)
    logger.info("Data root    : %s", config.DATA_ROOT)
    logger.info("Output dir   : %s", Path(__file__).parent)
    logger.info("Categories   : %s", ", ".join(config.CATEGORIES.keys()))
    logger.info("Mode         : %s", "INCREMENTAL" if args.incremental else "FULL REBUILD")
    logger.info("")

    if not _verify_data_dirs():
        sys.exit(1)

    # Show file counts per category as a sanity check
    for category, cat_cfg in config.CATEGORIES.items():
        suffixes = set(cat_cfg.get("extensions", [".md"]))
        total = 0
        for p in cat_cfg.get("paths", []):
            p = Path(p)
            if p.exists():
                total += sum(1 for f in p.rglob("*") if f.is_file() and f.suffix.lower() in suffixes)
        logger.info("  [%s] %d source files found", category, total)
    logger.info("")

    import indexer  # noqa: PLC0415  (import after path setup)

    if args.incremental:
        logger.info("Starting incremental update ...")
        logger.info("(Only new/changed files will be re-embedded)")
    else:
        logger.info("Starting full index build ...")
        logger.info("(The ONNX model downloads ~45 MB on first run; cached afterward)")
    logger.info("")

    t0      = time.time()
    stats   = indexer.build_incremental() if args.incremental else indexer.build_all()
    elapsed = time.time() - t0

    total = sum(stats.values())
    logger.info("")
    logger.info("=" * 60)
    logger.info("Index build complete in %.1f seconds (%.1f minutes).", elapsed, elapsed / 60)
    logger.info("Total chunks indexed: %d", total)
    logger.info("")
    logger.info("Category breakdown:")
    for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
        logger.info("  %-20s %6d chunks", cat, count)

    out_dir = Path(__file__).parent
    logger.info("")
    logger.info("Output files:")
    logger.info("  ChromaDB      : %s", out_dir / "chroma_db")
    logger.info("  BM25          : %s", out_dir / "bm25_index.pkl")
    logger.info("  Stats         : %s", out_dir / "category_stats.json")
    logger.info("  Manifest      : %s", out_dir / "file_manifest.json")
    parent_store_path = out_dir / "parent_store.json"
    if parent_store_path.exists():
        logger.info("  Parent store  : %s", parent_store_path)

    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Reload the MCP server in Cursor (Settings → MCP → reload)")
    logger.info("  2. Test with: search_docs(\"your query here\")")
    logger.info('  3. Test with: list_categories()')


if __name__ == "__main__":
    main()
