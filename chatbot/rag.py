"""Lightweight retrieval over the curated Neevalay knowledge base.

Uses fastembed (ONNX embeddings, no PyTorch) and a plain NumPy cosine-similarity
search over a small, prebuilt index (data/knowledge.npz + data/chunks.json).
"""
import json
from functools import lru_cache
from typing import List, Dict, Tuple

import numpy as np

from . import config


@lru_cache(maxsize=1)
def _load_index() -> Tuple[np.ndarray, List[Dict]]:
    """Load the prebuilt embeddings + chunk metadata once, then cache."""
    if not config.EMBEDDINGS_PATH.exists() or not config.CHUNKS_PATH.exists():
        return np.empty((0, 0), dtype=np.float32), []

    with np.load(config.EMBEDDINGS_PATH) as data:
        vectors = data["vectors"].astype(np.float32)
    with open(config.CHUNKS_PATH, "r", encoding="utf-8") as fh:
        chunks = json.load(fh)
    return vectors, chunks


@lru_cache(maxsize=1)
def _embedder():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=config.EMBED_MODEL)


def _embed(text: str) -> np.ndarray:
    vec = np.array(list(_embedder().embed([text]))[0], dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def has_knowledge() -> bool:
    vectors, chunks = _load_index()
    return len(chunks) > 0 and vectors.size > 0


def retrieve(question: str) -> List[Dict]:
    """Return the top-k relevant chunks above the similarity threshold."""
    vectors, chunks = _load_index()
    if not chunks or vectors.size == 0:
        return []

    query = _embed(question)
    # Index vectors are already L2-normalized, so a dot product is cosine sim.
    scores = vectors @ query
    top_idx = np.argsort(scores)[::-1][: config.RAG_TOP_K]

    results = []
    for i in top_idx:
        score = float(scores[i])
        if score < config.RAG_MIN_SCORE:
            continue
        item = dict(chunks[i])
        item["score"] = score
        results.append(item)
    return results


def format_context(results: List[Dict]) -> str:
    """Render retrieved chunks into a compact context block for the LLM."""
    blocks = []
    for r in results:
        blocks.append(
            f"Title: {r.get('title', 'Neevalay')}\n"
            f"URL: {r.get('url', '')}\n"
            f"{r.get('text', '')}"
        )
    return "\n\n".join(blocks)
