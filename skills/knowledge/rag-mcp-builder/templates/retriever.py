"""
RAG MCP — Retriever

Implements hybrid search: BM25 (keyword) + vector (semantic) with RRF fusion.
Supports parent-child retrieval: child chunks are matched for precision, but
the parent text (larger context) is returned to the caller.

Public API:
  hybrid_search(query, category, n_results)  — main search used by search_docs tool
  get_category_stats()                       — chunk counts per category
"""

from __future__ import annotations

import json
import logging
import pickle
import re
from typing import Optional

import indexer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parent store — loaded lazily for parent-child retrieval
# ---------------------------------------------------------------------------
_parent_store: dict[str, str] | None = None
_parent_store_load_attempted: bool = False


def _load_parent_store() -> dict[str, str]:
    """
    Load parent_store.json lazily. Returns empty dict if the file does not exist
    (meaning no parent-child categories are configured).
    """
    global _parent_store, _parent_store_load_attempted
    if _parent_store_load_attempted:
        return _parent_store or {}
    _parent_store_load_attempted = True

    p = indexer.PARENT_STORE_PATH
    if not p.exists():
        _parent_store = {}
        return {}

    logger.info("Loading parent store from %s ...", p)
    try:
        with open(p, encoding="utf-8") as f:
            _parent_store = json.load(f)
        logger.info("Parent store loaded: %d entries.", len(_parent_store))
    except Exception as exc:
        logger.warning("Failed to load parent store: %s", exc)
        _parent_store = {}
    return _parent_store


# ---------------------------------------------------------------------------
# BM25 index — loaded lazily on first search call
# ---------------------------------------------------------------------------
_bm25_data: dict | None = None
_bm25_load_attempted: bool = False


def _load_bm25() -> dict | None:
    global _bm25_data, _bm25_load_attempted
    if _bm25_load_attempted:
        return _bm25_data
    _bm25_load_attempted = True

    bm25_path = indexer.BM25_PATH
    if not bm25_path.exists():
        logger.warning("BM25 index not found at %s — keyword search unavailable.", bm25_path)
        return None

    logger.info("Loading BM25 index from %s ...", bm25_path)
    try:
        with open(bm25_path, "rb") as f:
            _bm25_data = pickle.load(f)
        logger.info("BM25 index loaded: %d documents.", len(_bm25_data.get("ids", [])))
    except Exception as exc:
        logger.warning("Failed to load BM25 index: %s", exc)
        _bm25_data = None
    return _bm25_data


# ---------------------------------------------------------------------------
# BM25 search
# ---------------------------------------------------------------------------

def _bm25_search(
    query: str,
    category: Optional[str] = None,
    n_results: int = 20,
) -> list[str]:
    """Return top-N chunk IDs by BM25 score, optionally filtered by category."""
    data = _load_bm25()
    if data is None:
        return []

    bm25       = data["bm25"]
    ids        = data["ids"]
    categories = data["categories"]

    tokens = re.findall(r"\w+", query.lower())
    if not tokens:
        return []

    scores = bm25.get_scores(tokens)

    if category:
        for i, cat in enumerate(categories):
            if cat != category:
                scores[i] = 0.0

    scored = [(i, float(s)) for i, s in enumerate(scores) if s > 0.0]
    scored.sort(key=lambda x: -x[1])
    return [ids[i] for i, _ in scored[:n_results]]


# ---------------------------------------------------------------------------
# Vector search (ChromaDB)
# ---------------------------------------------------------------------------

def _vector_search(
    query: str,
    category: Optional[str] = None,
    n_results: int = 20,
) -> list[str]:
    """Return top-N chunk IDs by cosine similarity."""
    collection = indexer.get_collection(create_if_missing=False)
    if collection is None:
        return []

    total = collection.count()
    if total == 0:
        return []

    actual_n = min(n_results, total)
    where    = {"category": {"$eq": category}} if category else None

    kwargs: dict = dict(
        query_texts=[query],
        n_results=actual_n,
        include=["metadatas"],
    )
    if where:
        kwargs["where"] = where

    try:
        results = collection.query(**kwargs)
    except Exception as exc:
        logger.warning("Vector query failed (%s); retrying with n_results=5.", exc)
        kwargs["n_results"] = min(5, total)
        try:
            results = collection.query(**kwargs)
        except Exception:
            return []

    return list(results.get("ids", [[]])[0])


# ---------------------------------------------------------------------------
# RRF fusion
# ---------------------------------------------------------------------------

def _rrf(list_a: list[str], list_b: list[str], k: int = 60) -> list[str]:
    """
    Reciprocal Rank Fusion of two ranked ID lists.
    Higher score = better rank from either list.
    """
    scores: dict[str, float] = {}
    for rank, doc_id in enumerate(list_a):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    for rank, doc_id in enumerate(list_b):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda x: -scores[x])


# ---------------------------------------------------------------------------
# Fetch content from ChromaDB by IDs
# ---------------------------------------------------------------------------

def _fetch_by_ids(ids: list[str]) -> list[dict]:
    """
    Fetch chunk text and metadata from ChromaDB by a list of IDs.
    Results are returned in the same order as the input list (RRF rank order).
    """
    if not ids:
        return []
    collection = indexer.get_collection(create_if_missing=False)
    if collection is None:
        return []

    try:
        result = collection.get(
            ids=ids,
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        logger.warning("ChromaDB get-by-ids failed: %s", exc)
        return []

    docs    = result.get("documents") or []
    metas   = result.get("metadatas") or []
    ret_ids = result.get("ids") or []

    id_map: dict[str, dict] = {
        rid: {"text": doc, "meta": meta}
        for rid, doc, meta in zip(ret_ids, docs, metas)
    }
    return [id_map[doc_id] for doc_id in ids if doc_id in id_map]


# ---------------------------------------------------------------------------
# Parent-child resolution
# ---------------------------------------------------------------------------

def _resolve_parents(results: list[dict]) -> list[dict]:
    """
    Post-process hybrid search results for parent-child retrieval.

    For each result that has a parent_id in the parent store, replace its
    text with the full parent text. Multiple child chunks that map to the
    same parent are merged into a single result. Results with more child
    hits are ranked first (they are the most relevant parent sections).
    Results without a parent_id (standard categories) are passed through
    unchanged and appended after all parent results.

    This function is a no-op when the parent store is empty (i.e., when no
    categories use child_chunk_size).
    """
    parent_store = _load_parent_store()
    if not parent_store:
        return results

    seen: dict[str, dict] = {}
    passthrough: list[dict] = []

    for r in results:
        pid = r.get("parent_id", "")
        if pid and pid in parent_store:
            if pid in seen:
                seen[pid]["_hit_count"] += 1
            else:
                entry = dict(r)
                entry["text"] = parent_store[pid]
                entry["_hit_count"] = 1
                seen[pid] = entry
        else:
            passthrough.append(r)

    parent_results = sorted(seen.values(), key=lambda x: -x["_hit_count"])
    for r in parent_results:
        r.pop("_hit_count", None)
        r.pop("parent_id", None)
    for r in passthrough:
        r.pop("parent_id", None)

    return parent_results + passthrough


# ---------------------------------------------------------------------------
# Public search API
# ---------------------------------------------------------------------------

def hybrid_search(
    query: str,
    category: Optional[str] = None,
    n_results: int = 8,
) -> list[dict]:
    """
    Hybrid BM25 + vector search with RRF fusion.

    For categories with child_chunk_size set (parent-child mode), child chunks
    are used for matching and the parent text is returned for richer context.

    Returns up to n_results dicts with keys:
        text, category, source, source_path, module
    Falls back to whichever retriever is available if one index is missing.
    """
    fetch_n = min(n_results * 3, 30)

    bm25_ids   = _bm25_search(query, category=category, n_results=fetch_n)
    vector_ids = _vector_search(query, category=category, n_results=fetch_n)

    if not bm25_ids and not vector_ids:
        return []

    if not bm25_ids:
        merged_ids = vector_ids[:n_results]
    elif not vector_ids:
        merged_ids = bm25_ids[:n_results]
    else:
        merged_ids = _rrf(bm25_ids, vector_ids)[:n_results]

    chunks = _fetch_by_ids(merged_ids)

    results = [
        {
            "text":        chunk["text"],
            "category":    chunk["meta"].get("category", ""),
            "source":      chunk["meta"].get("source", ""),
            "source_path": chunk["meta"].get("source_path", ""),
            "module":      chunk["meta"].get("module", ""),
            "parent_id":   chunk["meta"].get("parent_id", ""),
        }
        for chunk in chunks
    ]

    return _resolve_parents(results)


def get_category_stats() -> dict[str, int]:
    """Return chunk counts per category from the stats file."""
    return indexer.get_index_stats()
