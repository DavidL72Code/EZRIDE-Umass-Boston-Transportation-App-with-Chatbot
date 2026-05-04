from pathlib import Path
from typing import Optional

from src.indexing.bm25_index import BM25Index
from src.indexing.embedder import Embedder, FAISSIndex

CATEGORIES = ["materials", "locations", "programs", "composting", "sustainability", "general"]

# RRF constant — standard value, balances rank importance
_RRF_K = 60


def _rrf(rank: int) -> float:
    return 1.0 / (_RRF_K + rank + 1)


class HybridRetriever:
    """
    Combines BM25 keyword search with all-MiniLM-L6-v2 semantic search
    using Reciprocal Rank Fusion. Supports both global and per-category search.
    """

    def __init__(
        self,
        bm25_dir: Path,
        faiss_dir: Path,
        embedder: Embedder,
        semantic_weight: float = 0.6,
    ) -> None:
        self.embedder = embedder
        self.semantic_weight = semantic_weight  # 0 = pure BM25, 1 = pure semantic
        self.bm25_dir = bm25_dir
        self.faiss_dir = faiss_dir

        # Lazy-loaded index cache
        self._bm25_cache: dict[str, BM25Index] = {}
        self._faiss_cache: dict[str, FAISSIndex] = {}

    def _load_bm25(self, scope: str) -> Optional[BM25Index]:
        if scope not in self._bm25_cache:
            path = self.bm25_dir / f"{scope}.pkl"
            if not path.exists():
                return None
            self._bm25_cache[scope] = BM25Index.load(path)
        return self._bm25_cache[scope]

    def _load_faiss(self, scope: str) -> Optional[FAISSIndex]:
        if scope not in self._faiss_cache:
            idx_path = self.faiss_dir / f"{scope}.index"
            meta_path = self.faiss_dir / f"{scope}_meta.json"
            # numpy fallback path
            npy_path = self.faiss_dir / f"{scope}.npy"
            if not meta_path.exists():
                return None
            if not idx_path.exists() and not npy_path.exists():
                return None
            self._faiss_cache[scope] = FAISSIndex.load(idx_path, meta_path)
        return self._faiss_cache[scope]

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
    ) -> list[dict]:
        scope = category if (category and category != "all") else "global"

        bm25 = self._load_bm25(scope)
        faiss = self._load_faiss(scope)

        if bm25 is None and faiss is None:
            return []

        fetch_k = min(top_k * 3, 30)
        bm25_results = bm25.search(query, top_k=fetch_k) if bm25 else []
        query_vec = self.embedder.embed_query(query)
        faiss_results = faiss.search(query_vec, top_k=fetch_k) if faiss else []

        # Reciprocal Rank Fusion
        scores: dict[str, dict] = {}
        keyword_w = 1.0 - self.semantic_weight
        for r in bm25_results:
            cid = r["chunk"]["chunk_id"]
            scores.setdefault(cid, {"chunk": r["chunk"], "score": 0.0})
            scores[cid]["score"] += keyword_w * _rrf(r["rank"])

        for r in faiss_results:
            cid = r["chunk"]["chunk_id"]
            scores.setdefault(cid, {"chunk": r["chunk"], "score": 0.0})
            scores[cid]["score"] += self.semantic_weight * _rrf(r["rank"])

        ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]

    def is_ready(self) -> bool:
        global_bm25 = self.bm25_dir / "global.pkl"
        global_meta = self.faiss_dir / "global_meta.json"
        return global_bm25.exists() and global_meta.exists()
