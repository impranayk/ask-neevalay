"""Build the RAG index from the curated Neevalay knowledge pack.

Reads data/knowledge.md, splits it into sections by level-2 (## ) headings,
chunks long sections, embeds them with fastembed, and writes:
  data/knowledge.npz   -> L2-normalized float32 vectors
  data/chunks.json     -> [{title, url, text}, ...] aligned to the vectors

Run from the repo root:  python ingest/build_index.py
Re-run whenever you edit data/knowledge.md.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

# Allow running as a script without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chatbot import config  # noqa: E402

CHUNK_SIZE = 1100      # characters
CHUNK_OVERLAP = 150
MIN_CHUNK = 40


def strip_comments(text: str) -> str:
    """Remove HTML comments (editor notes / [TO CONFIRM]) so they aren't indexed."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def split_sections(md: str):
    """Split the markdown into (title, body) pairs on level-2 '## ' headings."""
    # Drop a leading level-1 title if present.
    md = re.sub(r"(?m)^#\s+.*$", "", md, count=1)
    parts = re.split(r"(?m)^##\s+(.+?)\s*$", md)
    sections = []
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if body:
            sections.append((title, body))
    return sections


def chunk_text(text: str):
    text = re.sub(r"[ \t]+", " ", text).strip()
    if len(text) <= CHUNK_SIZE:
        return [text] if len(text) >= MIN_CHUNK else []
    chunks, start = [], 0
    while start < len(text):
        piece = text[start:start + CHUNK_SIZE].strip()
        if len(piece) >= MIN_CHUNK:
            chunks.append(piece)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def build():
    src = config.DATA_DIR / "knowledge.md"
    if not src.exists():
        print(f"Missing knowledge pack: {src}")
        return

    md = strip_comments(src.read_text(encoding="utf-8"))
    records = []
    for title, body in split_sections(md):
        for piece in chunk_text(body):
            records.append({"title": title, "url": config.WEBSITE_URL, "text": piece})

    if not records:
        print("No content parsed from knowledge.md — aborting.")
        return

    print(f"Sections/chunks: {len(records)}")
    print(f"Embedding with {config.EMBED_MODEL} (first run downloads the model) …")

    from fastembed import TextEmbedding

    embedder = TextEmbedding(model_name=config.EMBED_MODEL)
    texts = [f"{r['title']}. {r['text']}" for r in records]
    vectors = np.array(list(embedder.embed(texts)), dtype=np.float32)

    # L2-normalize so retrieval can use a plain dot product as cosine similarity.
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vectors = vectors / norms

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(config.EMBEDDINGS_PATH, vectors=vectors)
    with open(config.CHUNKS_PATH, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False)

    print(f"\n[done] Saved {len(records)} chunks")
    print(f"   {config.EMBEDDINGS_PATH}")
    print(f"   {config.CHUNKS_PATH}")


if __name__ == "__main__":
    build()
