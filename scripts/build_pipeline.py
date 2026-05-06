"""
Full pipeline: scrape → chunk → embed → index (BM25 + FAISS) per category.

Usage:
    python scripts/build_pipeline.py [--max-pages N] [--skip-scrape]
"""
import sys
import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR        = ROOT / "data"
RAW_DIR         = DATA_DIR / "raw"
PROCESSED_DIR   = DATA_DIR / "processed"
CATEGORIES_DIR  = DATA_DIR / "categories"
INDEX_DIR       = ROOT / "index"
BM25_DIR        = INDEX_DIR / "bm25"
FAISS_DIR       = INDEX_DIR / "faiss"


def step_scrape(max_pages: int) -> None:
    print("\n" + "="*60)
    print("STEP 1 — Scraping UMass Boston sustainability pages")
    print("="*60)
    from src.scraper.scraper import SEED_URLS, crawl, save_pages
    pages = crawl(SEED_URLS, max_pages=max_pages, delay=0.8)
    if not pages:
        print("[ERROR] No pages scraped. Check network or seed URLs.")
        sys.exit(1)
    save_pages(pages, RAW_DIR, CATEGORIES_DIR)


def step_chunk() -> list[dict]:
    print("\n" + "="*60)
    print("STEP 2 — Chunking pages (400 words, 80-word overlap)")
    print("="*60)
    import json
    from src.indexing.chunker import load_and_chunk
    raw_path = RAW_DIR / "all_pages.json"
    if not raw_path.exists():
        print(f"[ERROR] {raw_path} not found. Run scrape step first.")
        sys.exit(1)
    chunks = load_and_chunk(raw_path, PROCESSED_DIR, CATEGORIES_DIR, chunk_size=400, overlap=80)
    return [vars(c) if not isinstance(c, dict) else c for c in chunks]


def step_embed(chunks: list[dict]) -> "np.ndarray":
    print("\n" + "="*60)
    print("STEP 3 — Embedding with all-MiniLM-L6-v2")
    print("="*60)
    import json
    # Load from JSON if chunks are dataclass dicts (already serialized by chunker)
    chunks_path = PROCESSED_DIR / "chunks.json"
    import json as _json
    with open(chunks_path) as f:
        chunks = _json.load(f)

    from src.indexing.embedder import Embedder, build_embeddings
    embedder = Embedder()
    emb_path = PROCESSED_DIR / "embeddings.npy"
    embeddings = build_embeddings(chunks, embedder, save_path=emb_path)
    return chunks, embeddings, embedder


def step_build_indexes(chunks: list[dict], embeddings, embedder) -> None:
    print("\n" + "="*60)
    print("STEP 4 — Building BM25 indexes (global + per category)")
    print("="*60)
    from src.indexing.bm25_index import build_category_indexes
    build_category_indexes(chunks, BM25_DIR)

    print("\n" + "="*60)
    print("STEP 5 — Building FAISS indexes (global + per category)")
    print("="*60)
    from src.indexing.embedder import build_faiss_indexes
    build_faiss_indexes(chunks, embeddings, FAISS_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the UMass Boston recycling chatbot pipeline.")
    parser.add_argument("--max-pages", type=int, default=80, help="Max pages to scrape (default: 80)")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip scraping, use existing raw data")
    args = parser.parse_args()

    t0 = time.time()

    if not args.skip_scrape:
        step_scrape(args.max_pages)
    else:
        print("\n[Skipping scrape — using existing raw data]")

    chunks_raw = step_chunk()
    chunks, embeddings, embedder = step_embed(chunks_raw)
    step_build_indexes(chunks, embeddings, embedder)

    elapsed = time.time() - t0
    print("\n" + "="*60)
    print(f"Pipeline complete in {elapsed:.1f}s")
    print(f"  Chunks indexed : {len(chunks)}")
    print(f"  BM25 indexes   : {BM25_DIR}")
    print(f"  FAISS indexes  : {FAISS_DIR}")
    print("\nStart the chatbot with:")
    print("  streamlit run app.py")
    print("="*60)


if __name__ == "__main__":
    main()
