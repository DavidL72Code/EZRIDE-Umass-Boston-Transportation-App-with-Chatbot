import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import re
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


SEED_URLS = [
    "https://www.umb.edu/sustainability/",
    "https://www.umb.edu/sustainability/recycling/",
    "https://www.umb.edu/sustainability/waste-reduction/",
    "https://www.umb.edu/sustainability/composting/",
    "https://www.umb.edu/sustainability/programs/",
    "https://www.umb.edu/sustainability/energy/",
    "https://www.umb.edu/sustainability/transportation/",
    "https://www.umb.edu/sustainability/about/",
    "https://www.umb.edu/sustainability/get-involved/",
    "https://www.umb.edu/campus-life/sustainability/",
    "https://www.umb.edu/facilities/sustainability/",
    "https://www.umb.edu/sustainability/zero-waste/",
    "https://www.umb.edu/sustainability/climate-action/",
    "https://www.umb.edu/sustainability/green-labs/",
]

# Ordered so higher-priority categories win on ties
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("composting", ["compost", "food waste", "organic waste", "food scrap", "vermicompost"]),
    ("materials", [
        "recycle", "recyclable", "paper", "plastic", "glass", "metal",
        "cardboard", "what to recycle", "accepted items", "not accepted",
        "prohibited", "bottle", "can", "bin", "container",
    ]),
    ("locations", [
        "location", "where to recycle", "drop-off", "drop off", "bin location",
        "station", "building", "floor", "campus map", "collection point",
        "recycling center", "dumpster",
    ]),
    ("programs", [
        "program", "initiative", "campaign", "event", "volunteer", "green team",
        "student", "club", "organization", "zero waste", "ecochallenge",
        "recyclemania", "contest", "grant",
    ]),
    ("sustainability", [
        "sustainability", "environment", "green", "carbon", "climate",
        "energy", "water", "eco", "leed", "emission", "footprint",
        "renewable", "solar",
    ]),
]


@dataclass
class ScrapedPage:
    url: str
    title: str
    text: str
    category: str
    source: str = "umb.edu"
    headings: list = field(default_factory=list)
    links: list = field(default_factory=list)


def detect_category(url: str, title: str, text: str) -> str:
    combined = f"{url} {title} {text[:2000]}".lower()
    best_cat, best_score = "general", 0
    for cat, keywords in CATEGORY_RULES:
        score = sum(combined.count(kw) for kw in keywords)
        if score > best_score:
            best_cat, best_score = cat, score
    return best_cat


def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove common boilerplate phrases
    boilerplate = [
        r'Skip to (main )?content',
        r'Toggle navigation',
        r'Search this site',
        r'You are here:',
        r'Breadcrumb',
        r'Share this page',
    ]
    for pattern in boilerplate:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return text.strip()


def scrape_page(url: str, session: requests.Session) -> Optional[ScrapedPage]:
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [skip] {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)
        title = re.sub(r'\s*[|\-–]\s*UMass Boston.*$', '', title).strip()

    headings = []
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        text = h.get_text(strip=True)
        if text and len(text) > 3:
            headings.append(text)

    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=re.compile(r"(content|main)", re.I))
        or soup.find(class_=re.compile(r"(content|main|page-body)", re.I))
        or soup.body
    )
    if main is None:
        return None

    text = clean_text(main.get_text(separator=" "))
    if len(text.split()) < 50:
        return None

    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        parsed = urlparse(href)
        # Normalize: strip fragments and query strings for dedup
        clean_href = parsed._replace(fragment="", query="").geturl()
        if "umb.edu" in href and href.startswith("http") and clean_href not in seen:
            seen.add(clean_href)
            links.append(href)

    category = detect_category(url, title, text)
    return ScrapedPage(url=url, title=title, text=text, category=category, headings=headings[:8], links=links)


def is_relevant_url(url: str) -> bool:
    url_lower = url.lower()
    relevant = any(kw in url_lower for kw in [
        "sustainab", "recycl", "compost", "waste", "green", "environment",
        "eco", "program", "facilities", "campus-life", "zero-waste",
        "climate", "energy", "leed",
    ])
    excluded = any(kw in url_lower for kw in [
        "login", "portal", "apply", "admission", "financial", "parking",
        "police", "athletics", "sport", "event-calendar", "news/", "media",
        ".pdf", ".jpg", ".png", ".gif", ".doc", "mailto:", "tel:",
        "search?", "?q=", "feed/", "rss",
    ])
    return relevant and not excluded


def crawl(seed_urls: list, max_pages: int = 80, delay: float = 0.8) -> list[ScrapedPage]:
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (compatible; UMBRecyclingBot/1.0; +https://www.umb.edu)"

    visited: set[str] = set()
    queue = list(seed_urls)
    pages: list[ScrapedPage] = []

    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        # Normalize URL for visited check
        norm = urlparse(url)._replace(fragment="", query="").geturl().rstrip("/")
        if norm in visited:
            continue
        visited.add(norm)

        print(f"Scraping [{len(pages)+1}/{max_pages}]: {url}")
        page = scrape_page(url, session)
        if page:
            pages.append(page)
            for link in page.links:
                link_norm = urlparse(link)._replace(fragment="", query="").geturl().rstrip("/")
                if link_norm not in visited and is_relevant_url(link):
                    queue.append(link)
        time.sleep(delay)

    return pages


def save_pages(pages: list[ScrapedPage], raw_dir: Path, categories_dir: Path) -> dict[str, list]:
    raw_dir.mkdir(parents=True, exist_ok=True)

    all_data = [asdict(p) for p in pages]
    with open(raw_dir / "all_pages.json", "w") as f:
        json.dump(all_data, f, indent=2)
    print(f"Saved {len(all_data)} pages to {raw_dir / 'all_pages.json'}")

    by_category: dict[str, list] = {}
    for page in pages:
        by_category.setdefault(page.category, []).append(asdict(page))

    for cat, docs in by_category.items():
        cat_dir = categories_dir / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        with open(cat_dir / "pages.json", "w") as f:
            json.dump(docs, f, indent=2)
        print(f"  [{cat}] {len(docs)} pages → {cat_dir}")

    print(f"\nTotal: {len(pages)} pages across {len(by_category)} categories")
    return by_category
