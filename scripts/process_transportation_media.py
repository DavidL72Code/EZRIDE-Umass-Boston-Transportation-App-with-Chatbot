#!/usr/bin/env python3
"""Turn scraped transportation PDFs/images/JSON into RAG chunks and indexes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MEDIA_ROOT = ROOT / "data" / "transportation_media"
PROCESSED_DIR = ROOT / "data" / "processed"
INDEX_DIR = ROOT / "index"
BM25_DIR = INDEX_DIR / "bm25"
FAISS_DIR = INDEX_DIR / "faiss"
CHUNKS_PATH = PROCESSED_DIR / "transportation_media_chunks.json"
ELEMENTS_PATH = PROCESSED_DIR / "transportation_media_elements.jsonl"
EMBEDDINGS_PATH = PROCESSED_DIR / "transportation_media_embeddings.npy"
ERRORS_PATH = PROCESSED_DIR / "transportation_media_errors.json"

os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_matplotlib")


def stable_id(*parts: str) -> str:
    raw = "::".join(parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", "_".join(parts[:2])).strip("_").lower()
    return f"{slug}_{digest}"


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def require_unstructured():
    try:
        from unstructured.partition.image import partition_image
        from unstructured.partition.pdf import partition_pdf
    except ImportError as exc:
        raise SystemExit(
            "unstructured dependencies are missing. Run: python3 -m pip install -r requirements.txt"
        ) from exc
    return partition_pdf, partition_image


def element_to_record(element: Any, source_path: Path, source_kind: str) -> dict[str, Any] | None:
    text = clean_text(str(element))
    if not text:
        return None

    metadata = getattr(element, "metadata", None)
    metadata_dict = metadata.to_dict() if metadata and hasattr(metadata, "to_dict") else {}
    category = getattr(element, "category", None) or element.__class__.__name__
    page_number = metadata_dict.get("page_number")

    return {
        "id": stable_id(source_kind, str(source_path.relative_to(ROOT)), str(page_number), text[:80]),
        "source_kind": source_kind,
        "source_file": str(source_path.relative_to(ROOT)),
        "source_url": metadata_dict.get("url") or str(source_path.relative_to(ROOT)),
        "title": source_path.stem,
        "category": "transportation_media",
        "element_type": category,
        "page_number": page_number,
        "text": text,
        "metadata": metadata_dict,
    }


def extract_media_elements(strategy: str, include_images: bool, strict: bool) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    partition_pdf, partition_image = require_unstructured()
    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for pdf_path in sorted(MEDIA_ROOT.rglob("*.pdf")):
        try:
            elements = partition_pdf(filename=str(pdf_path), strategy=strategy)
        except Exception as exc:  # noqa: BLE001
            if strict:
                raise
            errors.append({
                "source_file": str(pdf_path.relative_to(ROOT)),
                "source_kind": "pdf",
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue
        for element in elements:
            record = element_to_record(element, pdf_path, "pdf")
            if record:
                records.append(record)

    if not include_images:
        return records, errors

    for image_path in sorted(MEDIA_ROOT.rglob("*")):
        if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        try:
            elements = partition_image(filename=str(image_path))
        except Exception as exc:  # noqa: BLE001
            if strict:
                raise
            errors.append({
                "source_file": str(image_path.relative_to(ROOT)),
                "source_kind": "image",
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue
        for element in elements:
            record = element_to_record(element, image_path, "image")
            if record:
                records.append(record)

    return records, errors


def summarize_stop(item: dict[str, Any]) -> str:
    attrs = item.get("attributes", {})
    name = attrs.get("name") or item.get("id")
    lat = attrs.get("latitude")
    lon = attrs.get("longitude")
    municipality = attrs.get("municipality")
    vehicle_type = attrs.get("vehicle_type")
    parts = [f"Stop {name} has MBTA id {item.get('id')}."]
    if municipality:
        parts.append(f"It is in {municipality}.")
    if vehicle_type is not None:
        parts.append(f"Vehicle type code: {vehicle_type}.")
    if lat is not None and lon is not None:
        parts.append(f"Coordinates: {lat}, {lon}.")
    return " ".join(parts)


def summarize_route(item: dict[str, Any]) -> str:
    attrs = item.get("attributes", {})
    long_name = attrs.get("long_name") or item.get("id")
    short_name = attrs.get("short_name")
    desc = attrs.get("description")
    color = attrs.get("color")
    text_color = attrs.get("text_color")
    parts = [f"Route {long_name} has MBTA id {item.get('id')}."]
    if short_name:
        parts.append(f"Short name: {short_name}.")
    if desc:
        parts.append(f"Description: {desc}.")
    if color:
        parts.append(f"Map color #{color} with text #{text_color}.")
    return " ".join(parts)


def summarize_route_pattern(item: dict[str, Any]) -> str:
    attrs = item.get("attributes", {})
    name = attrs.get("name") or item.get("id")
    direction = attrs.get("direction_id")
    typicality = attrs.get("typicality")
    route = item.get("relationships", {}).get("route", {}).get("data", {}).get("id")
    representative_trip = item.get("relationships", {}).get("representative_trip", {}).get("data", {}).get("id")
    parts = [f"Route pattern {name} has MBTA id {item.get('id')}."]
    if route:
        parts.append(f"It belongs to route {route}.")
    if direction is not None:
        parts.append(f"Direction id: {direction}.")
    if typicality is not None:
        parts.append(f"Typicality code: {typicality}.")
    if representative_trip:
        parts.append(f"Representative trip id: {representative_trip}.")
    return " ".join(parts)


def summarize_shape(item: dict[str, Any]) -> str:
    attrs = item.get("attributes", {})
    polyline = attrs.get("polyline", "")
    route = item.get("relationships", {}).get("route", {}).get("data", {}).get("id")
    text = f"Shape {item.get('id')} describes MBTA route geometry."
    if route:
        text += f" It belongs to route {route}."
    if polyline:
        text += f" Encoded polyline length: {len(polyline)} characters."
    return text


def summarize_alert(item: dict[str, Any]) -> str:
    attrs = item.get("attributes", {})
    header = attrs.get("header") or item.get("id")
    effect = attrs.get("effect")
    severity = attrs.get("severity")
    lifecycle = attrs.get("lifecycle")
    text = f"MBTA alert: {header}."
    details = []
    if effect:
        details.append(f"effect {effect}")
    if severity is not None:
        details.append(f"severity {severity}")
    if lifecycle:
        details.append(f"lifecycle {lifecycle}")
    if details:
        text += " " + ", ".join(details) + "."
    description = clean_text(attrs.get("description") or "")
    if description:
        text += f" {description}"
    return text


def json_summary(filename: str, item: dict[str, Any]) -> str:
    name = filename.lower()
    if "alert" in name:
        return summarize_alert(item)
    if "route_patterns" in name:
        return summarize_route_pattern(item)
    if "routes" in name or name.startswith("route_"):
        return summarize_route(item)
    if "stops" in name or "stop_" in name or "nearby_stops" in name:
        return summarize_stop(item)
    if "shapes" in name:
        return summarize_shape(item)
    return clean_text(json.dumps(item, sort_keys=True))[:1800]


def extract_json_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for json_path in sorted(MEDIA_ROOT.rglob("*.json")):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        items = data.get("data") if isinstance(data, dict) else data
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            text = json_summary(json_path.name, item)
            if not text:
                continue
            records.append({
                "id": stable_id("json", str(json_path.relative_to(ROOT)), item.get("id", ""), text[:80]),
                "source_kind": "json",
                "source_file": str(json_path.relative_to(ROOT)),
                "source_url": str(json_path.relative_to(ROOT)),
                "title": json_path.stem,
                "category": "transportation_media",
                "element_type": item.get("type", "json_record"),
                "page_number": None,
                "text": text,
                "metadata": {
                    "record_id": item.get("id"),
                    "record_type": item.get("type"),
                    "relationships": item.get("relationships", {}),
                },
            })
    return records


def records_to_chunks(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        text = record["text"]
        chunks.append({
            "chunk_id": record["id"],
            "text": text,
            "source_url": record["source_url"],
            "title": record["title"],
            "category": "transportation_media",
            "headings": [record["source_kind"], record["element_type"]],
            "chunk_index": index,
            "total_chunks": len(records),
            "price_mentions": sorted(set(re.findall(r"\$\d+(?:\.\d{2})?", text))),
            "violation_codes": [],
            "active_section": record["element_type"],
            "source_file": record["source_file"],
            "source_kind": record["source_kind"],
            "page_number": record["page_number"],
            "metadata": record["metadata"],
        })
    return chunks


def save_outputs(records: list[dict[str, Any]], chunks: list[dict[str, Any]], errors: list[dict[str, str]]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with ELEMENTS_PATH.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    CHUNKS_PATH.write_text(json.dumps(chunks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ERRORS_PATH.write_text(json.dumps(errors, indent=2) + "\n", encoding="utf-8")


def build_indexes(chunks: list[dict[str, Any]]) -> None:
    from src.indexing.bm25_index import BM25Index
    from src.indexing.embedder import Embedder, FAISSIndex, build_embeddings

    bm25 = BM25Index()
    bm25.build(chunks)
    bm25.save(BM25_DIR / "transportation_media.pkl")

    embedder = Embedder()
    embeddings = build_embeddings(chunks, embedder, save_path=EMBEDDINGS_PATH)
    faiss_index = FAISSIndex()
    faiss_index.build(chunks, embeddings)
    faiss_index.save(FAISS_DIR / "transportation_media.index", FAISS_DIR / "transportation_media_meta.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Process transportation media into structured chunks.")
    parser.add_argument("--strategy", default="fast", choices=["fast", "hi_res", "ocr_only"], help="Unstructured PDF strategy.")
    parser.add_argument("--json-only", action="store_true", help="Only process scraped JSON records.")
    parser.add_argument("--skip-images", action="store_true", help="Skip OCR extraction for image files.")
    parser.add_argument("--strict-media", action="store_true", help="Fail instead of logging per-file extraction errors.")
    parser.add_argument("--no-embed", action="store_true", help="Skip embedding and index creation.")
    args = parser.parse_args()

    if args.json_only:
        media_records, errors = [], []
    else:
        media_records, errors = extract_media_elements(
            args.strategy,
            include_images=not args.skip_images,
            strict=args.strict_media,
        )
    json_records = extract_json_records()
    records = media_records + json_records
    chunks = records_to_chunks(records)
    save_outputs(records, chunks, errors)

    print(f"media elements: {len(media_records)}")
    print(f"json records: {len(json_records)}")
    print(f"chunks: {len(chunks)}")
    print(f"errors: {len(errors)}")
    print(f"elements: {ELEMENTS_PATH}")
    print(f"chunks: {CHUNKS_PATH}")
    print(f"errors: {ERRORS_PATH}")

    if not args.no_embed:
        build_indexes(chunks)
        print(f"bm25: {BM25_DIR / 'transportation_media.pkl'}")
        print(f"faiss: {FAISS_DIR / 'transportation_media.index'}")
        print(f"embeddings: {EMBEDDINGS_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
