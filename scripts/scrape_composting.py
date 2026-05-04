"""
Targeted scrape of UMass Boston composting + sustainability content.
UMass Boston redesigned their site — sustainability is now under /campus-planning/sustainability/.

Output folders:
  data/categories/composting/     pages with composting / food-waste / zero-waste content
  data/categories/sustainability/ other sustainability pages
  data/raw/all_pages.json         global raw (composting + sustainability entries updated)
  data/processed/chunks.json      global chunks (composting + sustainability entries updated)
"""
import sys
import json
import time
import re
from pathlib import Path
from dataclasses import asdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR       = ROOT / "data"
RAW_DIR        = DATA_DIR / "raw"
PROCESSED_DIR  = DATA_DIR / "processed"
CATEGORIES_DIR = DATA_DIR / "categories"

# ── Seed URLs discovered from live site exploration ──────────────────────────
SEEDS = [
    # Core sustainability section (new URL structure)
    "https://www.umb.edu/campus-planning/sustainability/",
    "https://www.umb.edu/campus-planning/sustainability/quad-sustainability/",
    "https://www.umb.edu/campus-planning/sustainability/fossil-fuel-free/",
    "https://www.umb.edu/campus-planning/sustainability/energy-carbon-master-plan/",
    "https://www.umb.edu/campus-planning/",
    "https://www.umb.edu/campus-planning/about-us/",
    "https://www.umb.edu/campus-planning/projects/",
    # Events with food-waste and zero-waste content
    "https://www.umb.edu/uec/special-events/earthmonth/",
    # Sustainable Solutions Lab
    "https://www.umb.edu/ssl/",
    # School for the Environment
    "https://www.umb.edu/environment/",
    "https://www.umb.edu/environment/beacon-lab/",
    "https://www.umb.edu/environment/research/",
    "https://www.umb.edu/environment/institutes-centers--facilities/",
    # News articles about sustainability/composting
    "https://www.umb.edu/news/2024/umass-boston-earns-silver-stars-rating/",
    # Dining / campus life
    "https://www.umb.edu/campus-life/housing-dining/",
    "https://www.umb.edu/campus-life/housing-dining/meal-plans/",
    "https://www.umb.edu/facilities/",
    "https://www.umb.edu/facilities/about/",
    "https://www.umb.edu/facilities/information/",
    "https://www.umb.edu/transportation/",
    "https://www.umb.edu/transportation/commuting/",
    "https://www.umb.edu/administration-finance/departments/",
]

COMPOSTING_KEYWORDS = [
    "compost", "composting", "food scrap", "food waste", "organic waste",
    "food collection", "organics", "worm bin", "vermicompost",
    "green bin", "food diversion", "pre-consumer", "post-consumer",
    "zero waste", "zero-waste",
]

SUSTAINABILITY_KEYWORDS = [
    "sustainab", "recycl", "recycle", "waste reduction", "carbon",
    "climate", "green", "energy", "leed", "solar", "emission",
    "renewable", "environment", "eco", "stormwater", "native plant",
]


def classify_page(url: str, title: str, text: str) -> str:
    combined = f"{url} {title} {text[:4000]}".lower()
    if any(kw in combined for kw in COMPOSTING_KEYWORDS):
        return "composting"
    if any(kw in combined for kw in SUSTAINABILITY_KEYWORDS):
        return "sustainability"
    return None   # not relevant — skip


def is_followable(url: str) -> bool:
    u = url.lower()
    wanted = any(k in u for k in [
        "campus-planning", "sustainability", "environment", "ssl",
        "uec", "earthmonth", "facilities", "campus-life",
        "housing-dining", "transportation", "administration-finance",
        "news/2024", "news/2025", "news/2026",
    ])
    blocked = any(k in u for k in [
        "login", "portal", "apply", "admission", "financial-aid",
        "police", "athletics", "sport", ".pdf", ".jpg", ".png",
        "mailto:", "tel:", "search?", "?q=", "accordion", "d.en.",
        "beacon-gateway", "directory", "registrar", "library",
        "canvas", "wiser", "bursar", "crtix",
    ])
    return wanted and not blocked


def main() -> None:
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlparse
    from src.scraper.scraper import scrape_page, clean_text
    from src.indexing.chunker import chunk_pages

    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (compatible; UMBSustainabilityBot/1.0; +https://www.umb.edu)"
    )

    visited: set[str] = set()
    queue = list(SEEDS)
    composting_pages: list[dict] = []
    sustainability_pages: list[dict] = []

    print("=" * 60)
    print("Scraping UMass Boston sustainability & composting content")
    print("=" * 60)

    while queue:
        url = queue.pop(0)
        norm = urlparse(url)._replace(fragment="", query="").geturl().rstrip("/")
        if norm in visited:
            continue
        visited.add(norm)

        print(f"  Fetching: {url}")
        page = scrape_page(url, session)
        if page is None:
            continue

        category = classify_page(page.url, page.title, page.text)
        if category is None:
            print(f"    – skipped (not sustainability relevant)")
            continue

        page.category = category
        page_dict = asdict(page)

        if category == "composting":
            composting_pages.append(page_dict)
            print(f"    ✓ COMPOSTING: {page.title!r}")
        else:
            sustainability_pages.append(page_dict)
            print(f"    ✓ sustainability: {page.title!r}")

        # Follow links within umb.edu that are relevant
        for link in page.links:
            ln = urlparse(link)._replace(fragment="", query="").geturl().rstrip("/")
            if "umb.edu" in link and ln not in visited and is_followable(link):
                queue.append(link)

        time.sleep(0.7)

    print(f"\nComposting pages: {len(composting_pages)}")
    print(f"Sustainability pages: {len(sustainability_pages)}")

    if not composting_pages and not sustainability_pages:
        print("[WARN] Nothing scraped. Check network connection.")
        return

    # ── Save per-category files ───────────────────────────────────────────────
    def save_category(cat: str, pages: list[dict]) -> list[dict]:
        if not pages:
            return []
        cat_dir = CATEGORIES_DIR / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        with open(cat_dir / "pages.json", "w") as f:
            json.dump(pages, f, indent=2)
        print(f"  → {cat_dir / 'pages.json'}  ({len(pages)} pages)")

        chunks = chunk_pages(pages, chunk_size=400, overlap=80)
        chunk_dicts = [asdict(c) for c in chunks]
        with open(cat_dir / "chunks.json", "w") as f:
            json.dump(chunk_dicts, f, indent=2)
        print(f"  → {cat_dir / 'chunks.json'}  ({len(chunk_dicts)} chunks)")
        return chunk_dicts

    print("\nSaving files…")
    composting_chunks = save_category("composting", composting_pages)
    sustainability_chunks = save_category("sustainability", sustainability_pages)

    all_new_pages = composting_pages + sustainability_pages
    all_new_chunks = composting_chunks + sustainability_chunks
    new_cats = {"composting", "sustainability"}

    # ── Merge into global raw file ────────────────────────────────────────────
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    global_raw = RAW_DIR / "all_pages.json"
    existing_pages: list[dict] = []
    if global_raw.exists():
        with open(global_raw) as f:
            existing_pages = [p for p in json.load(f) if p.get("category") not in new_cats]
    all_pages = existing_pages + all_new_pages
    with open(global_raw, "w") as f:
        json.dump(all_pages, f, indent=2)
    print(f"  → {global_raw}  ({len(all_pages)} total pages)")

    # ── Merge into global chunks file ─────────────────────────────────────────
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    global_chunks = PROCESSED_DIR / "chunks.json"
    existing_chunks: list[dict] = []
    if global_chunks.exists():
        with open(global_chunks) as f:
            existing_chunks = [c for c in json.load(f) if c.get("category") not in new_cats]
    all_chunks_merged = existing_chunks + all_new_chunks
    with open(global_chunks, "w") as f:
        json.dump(all_chunks_merged, f, indent=2)
    print(f"  → {global_chunks}  ({len(all_chunks_merged)} total chunks)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Scrape complete.")
    print(f"  Composting  : {len(composting_pages)} pages, {len(composting_chunks)} chunks")
    print(f"  Sustainability: {len(sustainability_pages)} pages, {len(sustainability_chunks)} chunks")
    print()
    print("Folder layout:")
    print(f"  {CATEGORIES_DIR / 'composting'}/")
    print(f"    pages.json    — raw page data")
    print(f"    chunks.json   — chunked for search")
    print(f"  {CATEGORIES_DIR / 'sustainability'}/")
    print(f"    pages.json")
    print(f"    chunks.json")
    print()
    print("Next step — rebuild search indexes:")
    print("  python scripts/build_pipeline.py --skip-scrape")
    print("=" * 60)


if __name__ == "__main__":
    main()
