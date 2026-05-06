import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Chunk:
    chunk_id: str
    text: str
    source_url: str
    title: str
    category: str
    headings: list
    chunk_index: int
    total_chunks: int


def _tokenize_len(text: str) -> int:
    return len(text.split())


def split_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    # Split on sentence boundaries, preserving the delimiter
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sent in sentences:
        sent_len = _tokenize_len(sent)
        if current_len + sent_len > chunk_size and current:
            chunks.append(" ".join(current))
            # Keep overlap sentences from the tail
            overlap_sents: list[str] = []
            overlap_len = 0
            for s in reversed(current):
                slen = _tokenize_len(s)
                if overlap_len + slen <= overlap:
                    overlap_sents.insert(0, s)
                    overlap_len += slen
                else:
                    break
            current = overlap_sents
            current_len = overlap_len
        current.append(sent)
        current_len += sent_len

    if current:
        chunks.append(" ".join(current))

    return [c for c in chunks if _tokenize_len(c) >= 20]


def _make_context_header(title: str, headings: list[str]) -> Optional[str]:
    parts = []
    if title:
        parts.append(title)
    # Top 3 most relevant headings
    for h in headings[:3]:
        if h and h.lower() != title.lower():
            parts.append(h)
    return " | ".join(parts) if parts else None


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 400,
    overlap: int = 80,
) -> list[dict]:
    chunks: list[dict] = []
    for page in pages:
        raw_text = page.get("text", "")
        if not raw_text:
            continue

        title = page.get("title", "")
        headings = page.get("headings", [])
        header = _make_context_header(title, headings)
        enriched = f"{header} | {raw_text}" if header else raw_text
        url_slug = (
            page["url"]
            .replace("https://", "")
            .replace("http://", "")
            .replace("/", "_")
            .rstrip("_")
        )

        splits = split_text(enriched, chunk_size, overlap)
        for i, text in enumerate(splits):
            chunks.append(asdict(Chunk(
                chunk_id=f"{url_slug}__chunk{i}",
                text=text,
                source_url=page["url"],
                title=title,
                category=page.get("category", "general"),
                headings=headings[:6],
                chunk_index=i,
                total_chunks=len(splits),
            )))

    return chunks


def load_and_chunk(
    raw_path: Path,
    processed_dir: Path,
    categories_dir: Path,
    chunk_size: int = 400,
    overlap: int = 80,
) -> list[dict]:
    with open(raw_path) as f:
        pages = json.load(f)

    chunks = chunk_pages(pages, chunk_size=chunk_size, overlap=overlap)
    processed_dir.mkdir(parents=True, exist_ok=True)

    with open(processed_dir / "chunks.json", "w") as f:
        json.dump(chunks, f, indent=2)

    print(f"Created {len(chunks)} chunks from {len(pages)} pages")

    # Per-category chunks
    by_cat: dict[str, list[dict]] = {}
    for c in chunks:
        by_cat.setdefault(c["category"], []).append(c)

    for cat, cat_chunks in by_cat.items():
        cat_dir = categories_dir / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        with open(cat_dir / "chunks.json", "w") as f:
            json.dump(cat_chunks, f, indent=2)
        print(f"  [{cat}] {len(cat_chunks)} chunks → {cat_dir / 'chunks.json'}")

    return chunks
