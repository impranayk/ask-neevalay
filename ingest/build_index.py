"""Build the RAG knowledge index by crawling the Neevalay website.

Fetches every content page on neevalay.com (a static HTML site), strips the
repeated navigation/footer boilerplate, splits the real page text into
overlapping chunks, embeds them with fastembed, and saves:
  data/knowledge.npz   -> L2-normalized float32 vectors
  data/chunks.json     -> [{title, url, text}, ...] aligned to the vectors

The curated supplement in data/knowledge.md is merged in too (graceful phrasing
for contact / booking). Run from the repo root:  python ingest/build_index.py
"""
import html as _html
import json
import re
import sys
import time
import urllib.parse as up
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chatbot import config  # noqa: E402

SITE = config.WEBSITE_URL.rstrip("/")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NeevalayBot/1.0; +https://neevalay.com)"}
# Pages with no useful answer content for parents.
DENY = {"privacy-policy.html", "terms-of-use.html", "cookie-policy.html"}
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
MIN_CHUNK = 80
REQUEST_PAUSE = 0.3


class _Extractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip = 0
        self._in_title = False
        self.title = ""
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self._skip += 1
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            t = data.strip()
            if t:
                self.parts.append(_html.unescape(re.sub(r"\s+", " ", t)))


def canonical(u: str) -> str:
    p = up.urlparse(u.split("#")[0])
    path = p.path or "/"
    if path.endswith("/index.html"):
        path = path[: -len("index.html")]
    if path == "":
        path = "/"
    return f"{p.scheme}://{p.netloc}{path}"


def fetch(u: str):
    try:
        r = requests.get(u, headers=HEADERS, timeout=25)
        ctype = r.headers.get("content-type", "")
        if r.status_code == 200 and "html" in ctype:
            # requests defaults to ISO-8859-1 when the charset is unstated, which
            # mangles UTF-8 punctuation (curly quotes, em-dashes). Detect instead.
            if not r.encoding or r.encoding.lower() == "iso-8859-1":
                r.encoding = r.apparent_encoding or "utf-8"
            return r.text
    except Exception as exc:
        print(f"   ! {u}: {exc}")
    return None


def crawl():
    """BFS over same-domain .html pages starting from the homepage."""
    start = canonical(SITE + "/")
    seen, queue, pages = set(), [start], {}
    while queue:
        u = queue.pop(0)
        key = canonical(u)
        if key in seen:
            continue
        seen.add(key)
        html_text = fetch(u)
        if not html_text:
            continue
        ex = _Extractor()
        ex.feed(html_text)
        pages[key] = (ex.title.strip() or key, ex.parts)
        print(f"  fetched {key}  ({len(ex.parts)} fragments)")
        for h in re.findall(r'href=["\']([^"\']+)["\']', html_text, re.I):
            full = canonical(up.urljoin(u, h))
            if not full.startswith(SITE):
                continue
            base = full.rstrip("/").rsplit("/", 1)[-1]
            if base in DENY:
                continue
            if re.search(r"\.html?$|/$", full) and full not in seen:
                queue.append(full)
        time.sleep(REQUEST_PAUSE)
    return pages


def strip_boilerplate(pages: dict):
    """Drop text fragments that repeat across most pages (nav / footer)."""
    freq = Counter()
    for _title, parts in pages.values():
        for frag in set(parts):
            freq[frag] += 1
    cutoff = max(2, int(0.5 * len(pages)))  # on >=50% of pages => boilerplate
    cleaned = {}
    for url, (title, parts) in pages.items():
        body = " ".join(f for f in parts if freq[f] < cutoff or len(f) > 120)
        cleaned[url] = (title, re.sub(r"\s+", " ", body).strip())
    return cleaned


def chunk_text(text: str):
    chunks, start = [], 0
    while start < len(text):
        piece = text[start:start + CHUNK_SIZE].strip()
        if len(piece) >= MIN_CHUNK:
            chunks.append(piece)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def build():
    print(f"Crawling {SITE} …")
    pages = crawl()
    if not pages:
        print("No pages fetched — aborting.")
        return
    pages = strip_boilerplate(pages)

    records = []
    for url, (title, body) in pages.items():
        for piece in chunk_text(body):
            records.append({"title": title, "url": url, "text": piece})

    print(f"\nPages: {len(pages)} | chunks: {len(records)}")
    print(f"Embedding with {config.EMBED_MODEL} (first run downloads the model) …")

    from fastembed import TextEmbedding

    embedder = TextEmbedding(model_name=config.EMBED_MODEL)
    texts = [f"{r['title']}. {r['text']}" for r in records]
    vectors = np.array(list(embedder.embed(texts)), dtype=np.float32)
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
