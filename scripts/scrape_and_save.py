"""
Scrapes UMass Boston parking / transportation URLs.
Each URL is saved as its own .json file inside the appropriate category folder.
Also rebuilds the global all_pages.json and per-category chunks.json.
"""
import sys
import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR      = ROOT / "data"
RAW_DIR       = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CAT_DIR       = DATA_DIR / "categories"

# ── URLs → category ───────────────────────────────────────────────────────────
URLS = [
    # General transportation hub
    ("https://www.umb.edu/transportation/",                                        "general"),
    ("https://www.umb.edu/transportation/commuting/",                              "general"),

    # Parking permits & rates
    ("https://www.umb.edu/transportation/parking-rates/",                          "permits"),
    ("https://www.umb.edu/transportation/parking-rates/parking-rates/",            "permits"),
    ("https://www.umb.edu/transportation/parking-rates/carpool-registration-form/","permits"),
    ("https://www.umb.edu/transportation/parking-rates/prepaid-pass-order-form/",  "permits"),

    # Fines & enforcement
    ("https://www.umb.edu/transportation/parking-rates/fines/",                    "enforcement"),

    # MBTA passes & transit
    ("https://www.umb.edu/transportation/mbta/",                                   "transit"),
    ("https://www.umb.edu/transportation/parking-rates/mbta-pass-replacement-form/","transit"),
    ("https://hr.umb.edu/benefits/parking-mbta-passes",                            "transit"),

    # Shuttle bus
    ("https://www.umb.edu/transportation/shuttle-bus-information/",                "transit"),

    # Visitor parking
    ("https://www.umb.edu/transportation/visitor-resources/",                      "visitor"),

    # Biking / alternatives
    ("https://www.umb.edu/transportation/biking/",                                 "transit"),
]


def extract_clean_text(soup: BeautifulSoup) -> str:
    sidebar_wrap = soup.find(class_="l-page-sidebar")
    if sidebar_wrap:
        divs = [c for c in sidebar_wrap.children if getattr(c, "name", "") == "div"]
        content_div = divs[1] if len(divs) >= 2 else (divs[0] if divs else sidebar_wrap)
    else:
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()
        content_div = (
            soup.find("main")
            or soup.find("article")
            or soup.find(id=re.compile(r"content|main", re.I))
            or soup.body
        )

    if not content_div:
        return ""

    for tag in content_div(["form", "button", "script", "style", "noscript"]):
        tag.decompose()
    for tag in content_div.find_all(class_=re.compile(r"breadcrumb|skip|social", re.I)):
        tag.decompose()

    lines = []
    for el in content_div.find_all(
        ["h1", "h2", "h3", "h4", "h5", "p", "li", "td", "th", "blockquote", "dt", "dd"]
    ):
        text = el.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        if not text or len(text) < 3:
            continue
        if el.name in ("h1", "h2", "h3", "h4", "h5"):
            lines.append("")
            lines.append(f"## {text}")
        elif el.name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)

    raw = "\n".join(lines)
    raw = re.sub(r"\n{3,}", "\n\n", raw).strip()
    return raw


_HEADING_NOISE = {"menu", "umass", "umass boston", "home", "in this section", ""}

def extract_headings(soup: BeautifulSoup) -> list:
    seen = set()
    result = []
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        text = h.get_text(strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        low = text.lower()
        if text and len(text) > 3 and low not in _HEADING_NOISE and low not in seen:
            seen.add(low)
            result.append(text)
    return result


def url_to_filename(url: str) -> str:
    path = urlparse(url).path.strip("/")
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "index"
    slug = "_".join(parts[-2:]) if len(parts) >= 2 else parts[-1]
    slug = re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")
    return slug or "page"


def scrape_url(url: str, session: requests.Session) -> Optional[dict]:
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"    [skip] {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)
        title = re.sub(r"\s*[|\-–]\s*UMass Boston.*$", "", title).strip()

    headings = extract_headings(soup)
    text = extract_clean_text(soup)

    if len(text.split()) < 40:
        print(f"    [skip] too little content ({len(text.split())} words)")
        return None

    return {
        "url": url,
        "title": title,
        "source": urlparse(url).netloc,
        "scraped_date": str(date.today()),
        "headings": headings[:8],
        "word_count": len(text.split()),
        "text": text,
    }


def main() -> None:
    from src.indexing.chunker import chunk_pages
    from dataclasses import asdict

    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (compatible; UMBParkingBot/1.0; +https://www.umb.edu)"
    )

    print("=" * 60)
    print("Scraping UMass Boston parking & transportation")
    print("=" * 60)

    all_pages: list[dict] = []
    cat_pages: dict[str, list[dict]] = {}

    for url, category in URLS:
        print(f"\n[{category}] {url}")
        page_data = scrape_url(url, session)
        if not page_data:
            continue

        page_data["category"] = category
        filename = url_to_filename(url)

        cat_folder = CAT_DIR / category
        cat_folder.mkdir(parents=True, exist_ok=True)

        out_path = cat_folder / f"{filename}.json"
        counter = 1
        while out_path.exists():
            counter += 1
            out_path = cat_folder / f"{filename}_{counter}.json"

        with open(out_path, "w") as f:
            json.dump(page_data, f, indent=2, ensure_ascii=False)

        print(f"    ✓ {out_path.name}  ({page_data['word_count']} words)")

        all_pages.append(page_data)
        cat_pages.setdefault(category, []).append(page_data)

        time.sleep(0.7)

    # ── Per-category chunks.json ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Building chunks per category…")

    for cat, pages in cat_pages.items():
        chunks = chunk_pages(pages, chunk_size=150, overlap=30)
        chunk_dicts = [asdict(c) for c in chunks]
        chunks_path = CAT_DIR / cat / "chunks.json"
        with open(chunks_path, "w") as f:
            json.dump(chunk_dicts, f, indent=2, ensure_ascii=False)
        print(f"  [{cat}] {len(pages)} pages → {len(chunk_dicts)} chunks")

    # ── Global files ──────────────────────────────────────────────────────────
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(RAW_DIR / "all_pages.json", "w") as f:
        json.dump(all_pages, f, indent=2, ensure_ascii=False)
    print(f"\nGlobal: {len(all_pages)} pages → data/raw/all_pages.json")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    all_chunks = []
    for pages in cat_pages.values():
        chunks = chunk_pages(pages, chunk_size=150, overlap=30)
        all_chunks.extend([asdict(c) for c in chunks])
    with open(PROCESSED_DIR / "chunks.json", "w") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    print(f"Global: {len(all_chunks)} chunks → data/processed/chunks.json")

    print("\n" + "=" * 60)
    print("Done.")
    for cat, pages in cat_pages.items():
        print(f"  data/categories/{cat}/  ({len(pages)} files)")
    print("=" * 60)
    print("\nNext: python scripts/build_pipeline.py --skip-scrape")


if __name__ == "__main__":
    main()
