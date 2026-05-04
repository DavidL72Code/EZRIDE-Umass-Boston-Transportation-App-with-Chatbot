import re
import json
import pickle
from pathlib import Path

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False


_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "was", "were", "be", "been", "have", "has",
    "do", "does", "did", "will", "would", "can", "could", "should", "may",
    "might", "this", "that", "these", "those", "it", "its", "by", "from",
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


class BM25Index:
    def __init__(self) -> None:
        self._index: "BM25Okapi | None" = None
        self.chunks: list[dict] = []

    def build(self, chunks: list[dict]) -> None:
        if not HAS_BM25:
            raise ImportError("rank-bm25 not installed. Run: pip install rank-bm25")
        self.chunks = chunks
        corpus = [tokenize(c["text"]) for c in chunks]
        self._index = BM25Okapi(corpus)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        if self._index is None:
            return []
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self._index.get_scores(tokens)
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            {"chunk": self.chunks[i], "score": float(scores[i]), "rank": r}
            for r, i in enumerate(top_idx)
            if scores[i] > 0
        ]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"index": self._index, "chunks": self.chunks}, f)

    @classmethod
    def load(cls, path: Path) -> "BM25Index":
        with open(path, "rb") as f:
            data = pickle.load(f)
        obj = cls()
        obj._index = data["index"]
        obj.chunks = data["chunks"]
        return obj


def build_category_indexes(
    chunks: list[dict],
    index_dir: Path,
) -> dict[str, BM25Index]:
    """Build one BM25 index per category plus a global index."""
    index_dir.mkdir(parents=True, exist_ok=True)

    # Global
    global_idx = BM25Index()
    global_idx.build(chunks)
    global_idx.save(index_dir / "global.pkl")
    print(f"  BM25 global: {len(chunks)} chunks")

    # Per category
    by_cat: dict[str, list[dict]] = {}
    for c in chunks:
        by_cat.setdefault(c["category"], []).append(c)

    indexes: dict[str, BM25Index] = {"global": global_idx}
    for cat, cat_chunks in by_cat.items():
        idx = BM25Index()
        idx.build(cat_chunks)
        idx.save(index_dir / f"{cat}.pkl")
        indexes[cat] = idx
        print(f"  BM25 [{cat}]: {len(cat_chunks)} chunks")

    return indexes
