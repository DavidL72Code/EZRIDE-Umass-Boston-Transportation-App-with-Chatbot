#!/usr/bin/env python3
"""Download UMass Boston transportation-related PDF and image assets.

The scraper intentionally stays narrow: it only visits official UMass Boston
pages that are already transportation/map related, then saves linked PDFs and
images with a manifest for later multimodal RAG ingestion.
"""

from __future__ import annotations

import html
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "data" / "transportation_media"
PDF_DIR = OUT_ROOT / "pdf"
IMAGE_DIR = OUT_ROOT / "image"
MANIFEST = OUT_ROOT / "manifest.json"

SOURCE_PAGES = [
    "https://www.umb.edu/transportation/",
    "https://www.umb.edu/transportation/shuttle-bus-information/",
    "https://www.umb.edu/transportation/visitor-resources/",
    "https://www.umb.edu/transportation/parking-rates/",
    "https://www.umb.edu/transportation/parking-rates/parking-rates/",
    "https://www.umb.edu/transportation/biking/",
    "https://www.umb.edu/admissions/visit/maps/",
    "https://www.umb.edu/map-archive/",
]

ASSET_RE = re.compile(
    r"""(?:href|src)=["']([^"']+\.(?:pdf|png|jpe?g|webp|gif)(?:\?[^"']*)?)["']""",
    re.I,
)
ALT_RE = re.compile(r"""alt=["']([^"']+)["']""", re.I)
TAG_RE = re.compile(r"""<(a|img)\b[^>]*(?:href|src)=["']([^"']+)["'][^>]*>(.*?)</a>|<img\b[^>]*src=["']([^"']+)["'][^>]*>""", re.I | re.S)

TRANSPORT_TERMS = (
    "transport", "shuttle", "parking", "garage", "lot", "bayside", "jfk",
    "umass", "campus", "map", "bike", "biking", "scooter", "mbta", "bus",
    "route", "visitor", "morrissey", "harborwalk", "bluebike",
)


@dataclass
class Asset:
    kind: str
    url: str
    filename: str
    source_page: str
    label: str
    status: str = "pending"
    bytes: int = 0
    error: str = ""


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 UMassBostonTransportRAG/1.0"})
    with urlopen(req, timeout=20) as res:
        return res.read().decode("utf-8", errors="replace")


def fetch_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 UMassBostonTransportRAG/1.0"})
    with urlopen(req, timeout=30) as res:
        return res.read()


def clean_label(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:180]


def slug(value: str) -> str:
    value = re.sub(r"[?#].*$", "", value)
    stem = Path(urlparse(value).path).stem or "asset"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._")
    return stem[:90] or "asset"


def ext_for(url: str, kind: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return suffix
    return ".pdf" if kind == "pdf" else ".bin"


def is_relevant(url: str, label: str) -> bool:
    lowered_url = url.lower()
    if "favicon" in lowered_url or "/site-assets/images/favicons/" in lowered_url:
        return False
    haystack = f"{url} {label}".lower()
    return "umb.edu" in urlparse(url).netloc and any(term in haystack for term in TRANSPORT_TERMS)


def iter_assets(page_url: str, page_html: str) -> Iterable[tuple[str, str]]:
    seen: set[str] = set()
    for match in TAG_RE.finditer(page_html):
        href = match.group(2) or match.group(4)
        label = clean_label(match.group(3) or "")
        tag = match.group(0)
        alt_match = ALT_RE.search(tag)
        if alt_match and not label:
            label = clean_label(alt_match.group(1))
        if not href:
            continue
        url = urljoin(page_url, html.unescape(href))
        if not re.search(r"\.(pdf|png|jpe?g|webp|gif)(?:\?|$)", url, re.I):
            continue
        if url in seen:
            continue
        seen.add(url)
        yield url, label

    for href in ASSET_RE.findall(page_html):
        url = urljoin(page_url, html.unescape(href))
        if url in seen:
            continue
        seen.add(url)
        yield url, ""


def unique_filename(asset: Asset, used: set[str]) -> str:
    base = slug(asset.url)
    ext = ext_for(asset.url, asset.kind)
    name = f"{base}{ext}"
    i = 2
    while name in used:
        name = f"{base}-{i}{ext}"
        i += 1
    used.add(name)
    return name


def main() -> int:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    assets_by_url: dict[str, Asset] = {}
    for page_url in SOURCE_PAGES:
        try:
            page_html = fetch_text(page_url)
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"warn: failed page {page_url}: {exc}", file=sys.stderr)
            continue
        for url, label in iter_assets(page_url, page_html):
            if not is_relevant(url, label):
                continue
            kind = "pdf" if re.search(r"\.pdf(?:\?|$)", url, re.I) else "image"
            assets_by_url.setdefault(
                url,
                Asset(kind=kind, url=url, filename="", source_page=page_url, label=label),
            )

    used_pdf: set[str] = set()
    used_image: set[str] = set()
    assets = list(assets_by_url.values())
    for asset in assets:
        asset.filename = unique_filename(asset, used_pdf if asset.kind == "pdf" else used_image)
        dest = (PDF_DIR if asset.kind == "pdf" else IMAGE_DIR) / asset.filename
        try:
            payload = fetch_bytes(asset.url)
            dest.write_bytes(payload)
            asset.status = "downloaded"
            asset.bytes = len(payload)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            asset.status = "failed"
            asset.error = str(exc)
            print(f"warn: failed asset {asset.url}: {exc}", file=sys.stderr)

    manifest = {
        "source_pages": SOURCE_PAGES,
        "output_root": str(OUT_ROOT.relative_to(ROOT)),
        "assets": [asdict(asset) for asset in sorted(assets, key=lambda a: (a.kind, a.filename))],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    downloaded = [asset for asset in assets if asset.status == "downloaded"]
    print(f"downloaded {len(downloaded)} of {len(assets)} assets")
    print(f"manifest: {MANIFEST}")
    return 0 if downloaded else 1


if __name__ == "__main__":
    raise SystemExit(main())
