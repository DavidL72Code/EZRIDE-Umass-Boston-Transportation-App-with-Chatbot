import json
import numpy as np
from pathlib import Path
from typing import Optional

try:
    from sentence_transformers import SentenceTransformer
    HAS_ST = True
except ImportError:
    HAS_ST = False

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


class Embedder:
    def __init__(self, model_name: str = MODEL_NAME):
        if not HAS_ST:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def embed(self, texts: list[str], batch_size: int = 64, show_progress: bool = True) -> np.ndarray:
        return self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

    def embed_query(self, query: str) -> np.ndarray:
        vec = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)
        return vec[0]


class FAISSIndex:
    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self.dim = dim
        self._index = None
        self._embeddings: Optional[np.ndarray] = None
        self.chunks: list[dict] = []

    def build(self, chunks: list[dict], embeddings: np.ndarray) -> None:
        self.chunks = chunks
        vecs = embeddings.astype(np.float32)
        if HAS_FAISS:
            self._index = faiss.IndexFlatIP(self.dim)
            self._index.add(vecs)
        else:
            # Fallback: keep matrix for numpy dot-product search
            self._embeddings = vecs

    def search(self, query_vec: np.ndarray, top_k: int = 10) -> list[dict]:
        q = query_vec.astype(np.float32)
        if HAS_FAISS and self._index is not None:
            scores, indices = self._index.search(q.reshape(1, -1), top_k)
            return [
                {"chunk": self.chunks[idx], "score": float(scores[0][r]), "rank": r}
                for r, idx in enumerate(indices[0])
                if idx >= 0
            ]
        # numpy fallback
        if self._embeddings is not None:
            scores_arr = self._embeddings @ q
            top_idx = np.argsort(scores_arr)[::-1][:top_k]
            return [
                {"chunk": self.chunks[i], "score": float(scores_arr[i]), "rank": r}
                for r, i in enumerate(top_idx)
            ]
        return []

    def save(self, index_path: Path, meta_path: Path) -> None:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        if HAS_FAISS and self._index is not None:
            faiss.write_index(self._index, str(index_path))
        elif self._embeddings is not None:
            np.save(str(index_path.with_suffix(".npy")), self._embeddings)
        with open(meta_path, "w") as f:
            json.dump(self.chunks, f, indent=2)

    @classmethod
    def load(cls, index_path: Path, meta_path: Path) -> "FAISSIndex":
        with open(meta_path) as f:
            chunks = json.load(f)
        obj = cls()
        obj.chunks = chunks
        if HAS_FAISS:
            if index_path.exists():
                obj._index = faiss.read_index(str(index_path))
        else:
            npy_path = index_path.with_suffix(".npy")
            if npy_path.exists():
                obj._embeddings = np.load(str(npy_path))
        return obj


def build_embeddings(chunks: list[dict], embedder: Embedder, save_path: Optional[Path] = None) -> np.ndarray:
    texts = [c["text"] for c in chunks]
    print(f"Embedding {len(texts)} chunks with {embedder.model_name}...")
    embeddings = embedder.embed(texts)
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(save_path), embeddings)
        print(f"Saved embeddings → {save_path}")
    return embeddings


def build_faiss_indexes(
    chunks: list[dict],
    embeddings: np.ndarray,
    index_dir: Path,
) -> dict[str, "FAISSIndex"]:
    """Build one FAISS index per category plus a global index."""
    index_dir.mkdir(parents=True, exist_ok=True)

    # Global
    global_idx = FAISSIndex()
    global_idx.build(chunks, embeddings)
    global_idx.save(index_dir / "global.index", index_dir / "global_meta.json")
    print(f"  FAISS global: {len(chunks)} vectors")

    # Per category
    by_cat: dict[str, list[int]] = {}
    for i, c in enumerate(chunks):
        by_cat.setdefault(c["category"], []).append(i)

    indexes: dict[str, FAISSIndex] = {"global": global_idx}
    for cat, indices in by_cat.items():
        cat_chunks = [chunks[i] for i in indices]
        cat_emb = embeddings[indices]
        idx = FAISSIndex()
        idx.build(cat_chunks, cat_emb)
        idx.save(index_dir / f"{cat}.index", index_dir / f"{cat}_meta.json")
        indexes[cat] = idx
        print(f"  FAISS [{cat}]: {len(cat_chunks)} vectors")

    return indexes
