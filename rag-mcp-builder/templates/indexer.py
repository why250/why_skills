"""
RAG MCP — Document Indexer

Loads all source files defined in config.CATEGORIES, splits them into chunks,
and stores them in:
  - ChromaDB vector store  (ONNX all-MiniLM-L6-v2, cosine similarity)
  - BM25 keyword index     (rank_bm25, pickled to bm25_index.pkl)

Chunking strategies (configured per category in config.py):
  whole_file  — each file = one chunk (AEL functions, code examples)
  heading     — split at ##/### Markdown boundaries, max chunk_size chars

Parent-child retrieval (optional, enabled per category via child_chunk_size):
  When child_chunk_size is set, each file is split into:
    - parent chunks (chunk_size chars) stored in parent_store.json
    - child chunks  (child_chunk_size chars) stored in ChromaDB + BM25
  Search matches on child chunks (precision), but returns parent text (context).

Memory safety rules:
  - ChromaDB upsert: BATCH=100, clear list after each batch
  - Process one category at a time
  - chunk IDs: MD5(source_path|chunk_idx) — avoids collisions on identical boilerplate text
  - Run build_index.py in an external terminal (not inside Cursor) to avoid memory pressure
"""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
import re
from pathlib import Path
from typing import Iterator

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths — all relative to mcp_server/
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent

CHROMA_DIR        = _HERE / "chroma_db"
BM25_PATH         = _HERE / "bm25_index.pkl"
STATS_PATH        = _HERE / "category_stats.json"
MANIFEST_PATH     = _HERE / "file_manifest.json"
PARENT_STORE_PATH = _HERE / "parent_store.json"
COLLECTION_NAME   = config.PROJECT_NAME

# ---------------------------------------------------------------------------
# Derived settings from config.CATEGORIES
# ---------------------------------------------------------------------------

def _get_max_chunk_chars(category: str) -> int:
    """Return max chunk size (0 = whole-file) for a category."""
    cat_cfg = config.CATEGORIES[category]
    if cat_cfg.get("chunk_strategy") == "whole_file":
        return 0
    return cat_cfg.get("chunk_size", 1200)


def _get_child_chunk_size(category: str) -> int | None:
    """Return child_chunk_size if parent-child mode is enabled, else None."""
    val = config.CATEGORIES[category].get("child_chunk_size")
    return int(val) if val else None


def _get_suffixes(category: str) -> set[str]:
    """Return the set of file extensions for a category."""
    return set(config.CATEGORIES[category].get("extensions", [".md"]))


def _uses_module_field(category: str) -> bool:
    """Return True if this category stores parent dir name as 'module' metadata."""
    return bool(config.CATEGORIES[category].get("module_field", False))


# ---------------------------------------------------------------------------
# Singletons — loaded lazily so server.py startup stays lightweight
# ---------------------------------------------------------------------------
_embed_fn: DefaultEmbeddingFunction | None = None
_client: chromadb.ClientAPI | None = None


def _get_embed_fn() -> DefaultEmbeddingFunction:
    global _embed_fn
    if _embed_fn is None:
        logger.info("Loading ONNX embedding function (all-MiniLM-L6-v2) ...")
        _embed_fn = DefaultEmbeddingFunction()
        logger.info("ONNX embedding function ready.")
    return _embed_fn


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection(create_if_missing: bool = False) -> chromadb.Collection | None:
    """Get the ChromaDB collection. Called by retriever.py."""
    client = _get_client()
    try:
        return client.get_collection(
            COLLECTION_NAME,
            embedding_function=_get_embed_fn(),
        )
    except Exception:
        if create_if_missing:
            return client.create_collection(
                COLLECTION_NAME,
                embedding_function=_get_embed_fn(),
                metadata={"hnsw:space": "cosine"},
            )
        return None


# ---------------------------------------------------------------------------
# File manifest — tracks mtime + chunk_ids per source file for incremental updates
# ---------------------------------------------------------------------------

def _load_manifest() -> dict[str, dict]:
    """
    Load file manifest from MANIFEST_PATH.

    Structure:
        { "relative/path/file.md": {"mtime": 1710000000.0,
                                     "chunk_ids": ["abc123", ...],
                                     "category": "docs"} }

    Returns empty dict if the file does not exist or is unreadable.
    """
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Cannot read manifest (%s) — starting fresh.", exc)
    return {}


def _save_manifest(manifest: dict[str, dict]) -> None:
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    logger.info("File manifest saved: %d entries → %s", len(manifest), MANIFEST_PATH)


# ---------------------------------------------------------------------------
# Parent store — persistent dict {parent_id: parent_text}
# ---------------------------------------------------------------------------

def _load_parent_store() -> dict[str, str]:
    """Load parent_store.json. Returns empty dict if missing or unreadable."""
    if PARENT_STORE_PATH.exists():
        try:
            with open(PARENT_STORE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Cannot read parent_store.json (%s) — starting fresh.", exc)
    return {}


def _save_parent_store(store: dict[str, str]) -> None:
    with open(PARENT_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
    logger.info(
        "Parent store saved: %d entries → %s", len(store), PARENT_STORE_PATH
    )


# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------

def _doc_id(source_path: str, chunk_idx: int) -> str:
    """
    Path + position based MD5 ID.
    Using source_path + chunk_idx (not text content) avoids collisions when
    multiple files contain identical boilerplate text (e.g. "Was this page helpful?").
    """
    raw = f"{source_path}|{chunk_idx}"
    return hashlib.md5(raw.encode()).hexdigest()


def _char_split(text: str, max_chars: int, overlap: int = 200) -> list[str]:
    """
    Fallback character-level split for text that exceeds max_chars.
    Snaps to sentence or newline boundaries when possible.
    CRITICAL: always break when end >= len(text) to prevent infinite loop.
    """
    if len(text) <= max_chars:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = max(
                text.rfind(". ", start, end),
                text.rfind("\n", start, end),
            )
            if boundary > start + overlap:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):    # MUST have this to prevent infinite loop
            break
        start = end - overlap
    return chunks


def _heading_chunk(text: str, max_chars: int) -> list[str]:
    """
    Split Markdown at ## and ### heading boundaries (keeps heading in chunk).
    Sections larger than max_chars get a secondary char-level split.
    """
    sections = re.split(r"(?m)(?=^#{2,3} )", text)
    chunks: list[str] = []

    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= max_chars:
            chunks.append(section)
        else:
            subsections = re.split(r"(?m)(?=^### )", section)
            for sub in subsections:
                sub = sub.strip()
                if not sub:
                    continue
                if len(sub) <= max_chars:
                    chunks.append(sub)
                else:
                    chunks.extend(_char_split(sub, max_chars, overlap=200))

    return [c for c in chunks if c.strip()]


def _chunk_file(path: Path, category: str) -> list[str]:
    """Read a file and return its chunks according to the category strategy."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as exc:
        logger.warning("Cannot read %s: %s", path, exc)
        return []
    if not text:
        return []

    max_chars = _get_max_chunk_chars(category)
    if max_chars == 0:
        return [text]
    return _heading_chunk(text, max_chars)


def _chunk_file_parent_child(
    path: Path, rel_path: str, category: str
) -> tuple[list[dict], dict[str, str]]:
    """
    Parent-child chunking for categories with child_chunk_size set.

    Splits the file into parent chunks (chunk_size / heading strategy), then
    splits each parent into smaller child chunks (child_chunk_size / char split).
    Child chunks are stored in ChromaDB + BM25 for precise matching.
    Parent texts are stored in parent_store.json and returned at query time.

    Returns:
        child_chunks — list of {"id", "text", "parent_id"} dicts
        parent_map   — {parent_id: parent_text} for this file
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as exc:
        logger.warning("Cannot read %s: %s", path, exc)
        return [], {}
    if not text:
        return [], {}

    cat_cfg = config.CATEGORIES[category]
    parent_size = cat_cfg.get("chunk_size", 1200)
    child_size = _get_child_chunk_size(category) or 300
    strategy = cat_cfg.get("chunk_strategy", "heading")

    if strategy == "whole_file":
        parent_texts = [text]
    elif strategy == "heading":
        parent_texts = _heading_chunk(text, parent_size)
    else:
        parent_texts = _char_split(text, parent_size)

    child_chunks: list[dict] = []
    parent_map: dict[str, str] = {}

    for p_idx, parent_text in enumerate(parent_texts):
        parent_id = hashlib.md5(f"{rel_path}|p{p_idx}".encode()).hexdigest()
        parent_map[parent_id] = parent_text

        child_texts = _char_split(parent_text, child_size, overlap=50)
        if not child_texts:
            child_texts = [parent_text]

        for c_idx, child_text in enumerate(child_texts):
            child_id = hashlib.md5(
                f"{rel_path}|p{p_idx}|c{c_idx}".encode()
            ).hexdigest()
            child_chunks.append(
                {"id": child_id, "text": child_text, "parent_id": parent_id}
            )

    return child_chunks, parent_map


def _extract_module(path: Path, category: str) -> str:
    """
    Return a short module label for the file if module_field is enabled for this category.
    Returns the immediate parent directory name (e.g. 'de', 'dds', 'api').
    """
    if not _uses_module_field(category):
        return ""
    return path.parent.name


def _detect_category(file_path: Path) -> str:
    """
    Determine which category a file belongs to by matching against config.CATEGORIES dirs.
    Returns the first matching category name, or the last category as fallback.
    """
    for category, cat_cfg in config.CATEGORIES.items():
        for base_dir in cat_cfg.get("paths", []):
            try:
                file_path.relative_to(base_dir)
                return category
            except ValueError:
                continue
    return list(config.CATEGORIES.keys())[-1]


# ---------------------------------------------------------------------------
# File iteration
# ---------------------------------------------------------------------------

def _iter_category_files(category: str) -> Iterator[Path]:
    """Yield all files belonging to the given category."""
    cat_cfg  = config.CATEGORIES[category]
    suffixes = _get_suffixes(category)
    for base_dir in cat_cfg.get("paths", []):
        if not base_dir.exists():
            logger.warning("Directory not found (skipping): %s", base_dir)
            continue
        for path in sorted(base_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in suffixes:
                yield path


# ---------------------------------------------------------------------------
# Full index build
# ---------------------------------------------------------------------------

def build_all() -> dict[str, int]:
    """
    Build ChromaDB vector index and BM25 keyword index from all data sources.

    Returns {category: chunk_count}.
    Run only from build_index.py in an external terminal to avoid memory pressure.
    """
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info("Deleted existing collection '%s'.", COLLECTION_NAME)
    except Exception:
        pass

    collection = get_collection(create_if_missing=True)
    assert collection is not None

    BATCH = 100
    category_stats: dict[str, int] = {}
    total_chunks = 0

    batch_texts: list[str] = []
    batch_ids:   list[str] = []
    batch_metas: list[dict] = []

    bm25_ids:        list[str]       = []
    bm25_categories: list[str]       = []
    bm25_tokenized:  list[list[str]] = []

    file_manifest: dict[str, dict] = {}
    parent_store:  dict[str, str]  = {}

    def _flush() -> None:
        nonlocal total_chunks
        if not batch_texts:
            return
        collection.upsert(
            ids=batch_ids[:],
            documents=batch_texts[:],
            metadatas=batch_metas[:],
        )
        total_chunks += len(batch_texts)
        batch_texts.clear()
        batch_ids.clear()
        batch_metas.clear()

    for category in config.CATEGORIES:
        cat_count  = 0
        file_count = 0
        child_size = _get_child_chunk_size(category)
        logger.info("=" * 60)
        logger.info(
            "Processing category: %s%s",
            category,
            f" [parent-child, child={child_size}]" if child_size else "",
        )

        for file_path in _iter_category_files(category):
            try:
                rel_path = str(file_path.relative_to(config.DATA_ROOT)).replace("\\", "/")
            except ValueError:
                rel_path = str(file_path).replace("\\", "/")

            module = _extract_module(file_path, category)
            file_chunk_ids: list[str] = []
            file_parent_ids: list[str] = []

            if child_size:
                # Parent-child mode: index child chunks, store parent texts
                child_chunks, parent_map = _chunk_file_parent_child(
                    file_path, rel_path, category
                )
                if not child_chunks:
                    continue
                file_count += 1
                parent_store.update(parent_map)
                file_parent_ids = list(parent_map.keys())

                for item in child_chunks:
                    doc_id = item["id"]
                    chunk  = item["text"]
                    file_chunk_ids.append(doc_id)
                    meta = {
                        "category":    category,
                        "source":      file_path.name,
                        "source_path": rel_path,
                        "module":      module,
                        "parent_id":   item["parent_id"],
                    }
                    batch_texts.append(chunk)
                    batch_ids.append(doc_id)
                    batch_metas.append(meta)
                    bm25_ids.append(doc_id)
                    bm25_categories.append(category)
                    bm25_tokenized.append(re.findall(r"\w+", chunk.lower()))
                    cat_count += 1
                    if len(batch_texts) >= BATCH:
                        _flush()
                        logger.info("  [%s] %d chunks upserted ...", category, cat_count)
            else:
                # Standard mode: index chunks directly
                chunks = _chunk_file(file_path, category)
                if not chunks:
                    continue
                file_count += 1

                for chunk_idx, chunk in enumerate(chunks):
                    doc_id = _doc_id(rel_path, chunk_idx)
                    file_chunk_ids.append(doc_id)
                    meta = {
                        "category":    category,
                        "source":      file_path.name,
                        "source_path": rel_path,
                        "module":      module,
                    }
                    batch_texts.append(chunk)
                    batch_ids.append(doc_id)
                    batch_metas.append(meta)
                    bm25_ids.append(doc_id)
                    bm25_categories.append(category)
                    bm25_tokenized.append(re.findall(r"\w+", chunk.lower()))
                    cat_count += 1
                    if len(batch_texts) >= BATCH:
                        _flush()
                        logger.info("  [%s] %d chunks upserted ...", category, cat_count)

            manifest_entry: dict = {
                "mtime":     file_path.stat().st_mtime,
                "chunk_ids": file_chunk_ids,
                "category":  category,
            }
            if file_parent_ids:
                manifest_entry["parent_ids"] = file_parent_ids
            file_manifest[rel_path] = manifest_entry

        _flush()
        category_stats[category] = cat_count
        logger.info(
            "Category '%s' done: %d files → %d chunks.", category, file_count, cat_count
        )

    logger.info("=" * 60)
    logger.info("ChromaDB indexing complete. Total chunks: %d", total_chunks)

    logger.info("Building BM25 index over %d chunks ...", len(bm25_tokenized))
    from rank_bm25 import BM25Okapi  # noqa: PLC0415

    bm25 = BM25Okapi(bm25_tokenized)
    bm25_payload = {
        "bm25":       bm25,
        "ids":        bm25_ids,
        "categories": bm25_categories,
    }
    with open(BM25_PATH, "wb") as f:
        pickle.dump(bm25_payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info("BM25 index saved: %d KB", BM25_PATH.stat().st_size // 1024)

    if parent_store:
        _save_parent_store(parent_store)
    elif PARENT_STORE_PATH.exists():
        PARENT_STORE_PATH.unlink()
        logger.info("Removed stale parent_store.json (no parent-child categories).")

    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(category_stats, f, ensure_ascii=False, indent=2)

    _save_manifest(file_manifest)

    return category_stats


# ---------------------------------------------------------------------------
# Incremental update helpers
# ---------------------------------------------------------------------------

def _rebuild_bm25_from_chroma(collection: chromadb.Collection) -> None:
    """
    Rebuild BM25 by reading all chunk texts from ChromaDB.
    Uses paginated reads (PAGE=500) to keep memory usage flat.
    Avoids re-reading source files or re-generating embeddings.
    """
    from rank_bm25 import BM25Okapi  # noqa: PLC0415

    PAGE = 500
    offset = 0
    bm25_ids:        list[str]       = []
    bm25_categories: list[str]       = []
    bm25_tokenized:  list[list[str]] = []

    logger.info("Reading all chunks from ChromaDB for BM25 rebuild ...")
    while True:
        result = collection.get(
            limit=PAGE,
            offset=offset,
            include=["documents", "metadatas"],
        )
        if not result["ids"]:
            break
        for doc_id, doc, meta in zip(
            result["ids"], result["documents"], result["metadatas"]
        ):
            bm25_ids.append(doc_id)
            bm25_categories.append(meta.get("category", ""))
            bm25_tokenized.append(re.findall(r"\w+", doc.lower()))
        offset += PAGE
        logger.info("  BM25 read: %d chunks so far ...", len(bm25_ids))

    logger.info("Building BM25 index over %d chunks ...", len(bm25_tokenized))
    bm25 = BM25Okapi(bm25_tokenized)
    bm25_payload = {
        "bm25":       bm25,
        "ids":        bm25_ids,
        "categories": bm25_categories,
    }
    with open(BM25_PATH, "wb") as f:
        pickle.dump(bm25_payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info("BM25 index saved: %d KB", BM25_PATH.stat().st_size // 1024)


def build_incremental() -> dict[str, int]:
    """
    Incrementally update ChromaDB and BM25 indexes.

    Only processes files whose mtime has changed since the last build.
    Falls back to build_all() if no manifest exists.

    Algorithm:
      1. Load manifest  (rel_path → {mtime, chunk_ids, category})
      2. Scan all source files; compare mtimes
      3. Delete chunks for removed files
      4. Upsert chunks for new/changed files (ONNX embedding only for these)
      5. Rebuild BM25 from ChromaDB text (no re-embedding needed)
      6. Save updated manifest + category stats
    """
    if not MANIFEST_PATH.exists():
        logger.warning("No manifest found — falling back to full rebuild.")
        return build_all()

    manifest = _load_manifest()

    collection = get_collection(create_if_missing=True)
    if collection is None:
        logger.warning("No ChromaDB collection found — falling back to full rebuild.")
        return build_all()

    # Collect all current source files
    current_files: dict[str, Path] = {}
    for category in config.CATEGORIES:
        for fp in _iter_category_files(category):
            try:
                rel = str(fp.relative_to(config.DATA_ROOT)).replace("\\", "/")
            except ValueError:
                rel = str(fp).replace("\\", "/")
            current_files[rel] = fp

    # Load existing parent store (may be empty if no parent-child categories)
    parent_store = _load_parent_store()

    # Delete chunks for files that no longer exist
    deleted_count = 0
    for rel_path in list(manifest.keys()):
        if rel_path not in current_files:
            old_ids = manifest[rel_path].get("chunk_ids", [])
            if old_ids:
                try:
                    collection.delete(ids=old_ids)
                except Exception as exc:
                    logger.warning("Could not delete chunks for %s: %s", rel_path, exc)
            for pid in manifest[rel_path].get("parent_ids", []):
                parent_store.pop(pid, None)
            del manifest[rel_path]
            deleted_count += 1
            logger.info("  Removed (deleted file): %s", rel_path)

    # Upsert new / changed files
    added = modified = skipped = 0
    BATCH = 100
    batch_texts: list[str] = []
    batch_ids:   list[str] = []
    batch_metas: list[dict] = []

    def _flush_batch() -> None:
        if batch_texts:
            collection.upsert(
                ids=batch_ids[:],
                documents=batch_texts[:],
                metadatas=batch_metas[:],
            )
            batch_texts.clear()
            batch_ids.clear()
            batch_metas.clear()

    for rel_path, fp in current_files.items():
        mtime = fp.stat().st_mtime
        old   = manifest.get(rel_path)

        if old and abs(old["mtime"] - mtime) < 1.0:
            skipped += 1
            continue

        if old and old.get("chunk_ids"):
            try:
                collection.delete(ids=old["chunk_ids"])
            except Exception as exc:
                logger.warning("Could not delete old chunks for %s: %s", rel_path, exc)
            for pid in old.get("parent_ids", []):
                parent_store.pop(pid, None)

        category   = _detect_category(fp)
        module     = _extract_module(fp, category)
        child_size = _get_child_chunk_size(category)
        new_ids: list[str] = []
        new_parent_ids: list[str] = []

        if child_size:
            child_chunks, parent_map = _chunk_file_parent_child(fp, rel_path, category)
            if not child_chunks:
                continue
            parent_store.update(parent_map)
            new_parent_ids = list(parent_map.keys())

            for item in child_chunks:
                new_ids.append(item["id"])
                batch_texts.append(item["text"])
                batch_ids.append(item["id"])
                batch_metas.append({
                    "category":    category,
                    "source":      fp.name,
                    "source_path": rel_path,
                    "module":      module,
                    "parent_id":   item["parent_id"],
                })
                if len(batch_texts) >= BATCH:
                    _flush_batch()
        else:
            chunks = _chunk_file(fp, category)
            if not chunks:
                continue

            for chunk_idx, chunk in enumerate(chunks):
                doc_id = _doc_id(rel_path, chunk_idx)
                new_ids.append(doc_id)
                batch_texts.append(chunk)
                batch_ids.append(doc_id)
                batch_metas.append({
                    "category":    category,
                    "source":      fp.name,
                    "source_path": rel_path,
                    "module":      module,
                })
                if len(batch_texts) >= BATCH:
                    _flush_batch()

        _flush_batch()

        manifest_entry: dict = {
            "mtime": mtime, "chunk_ids": new_ids, "category": category,
        }
        if new_parent_ids:
            manifest_entry["parent_ids"] = new_parent_ids
        manifest[rel_path] = manifest_entry

        if old:
            modified += 1
            logger.info("  Updated: %s  (%d chunks)", rel_path, len(new_ids))
        else:
            added += 1
            logger.info("  Added:   %s  (%d chunks)", rel_path, len(new_ids))

    logger.info("=" * 60)
    logger.info(
        "Incremental update: %d added, %d modified, %d deleted, %d skipped.",
        added, modified, deleted_count, skipped,
    )

    _rebuild_bm25_from_chroma(collection)

    if parent_store:
        _save_parent_store(parent_store)
    elif PARENT_STORE_PATH.exists():
        PARENT_STORE_PATH.unlink()

    _save_manifest(manifest)

    category_stats: dict[str, int] = {}
    for info in manifest.values():
        cat = info.get("category", "")
        if cat:
            category_stats[cat] = category_stats.get(cat, 0) + len(info.get("chunk_ids", []))

    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(category_stats, f, ensure_ascii=False, indent=2)
    logger.info("Category stats updated: %s", category_stats)

    return category_stats


# ---------------------------------------------------------------------------
# Public helpers for server.py / retriever.py
# ---------------------------------------------------------------------------

def get_index_stats() -> dict[str, int]:
    """Return chunk counts per category from the stats file."""
    if STATS_PATH.exists():
        with open(STATS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def rebuild() -> dict[str, int]:
    """Force a full rebuild. Used by the reindex_docs MCP tool."""
    return build_all()
