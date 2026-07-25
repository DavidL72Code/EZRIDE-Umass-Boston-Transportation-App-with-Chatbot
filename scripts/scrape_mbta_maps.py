#!/usr/bin/env python3
"""Download official MBTA map PDFs and map-oriented route geometry data."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from urllib.error import HTTPError
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "data" / "transportation_media" / "mbta"
PDF_DIR = OUT_ROOT / "pdf"
JSON_DIR = OUT_ROOT / "json"
MANIFEST = OUT_ROOT / "maps_manifest.json"
API_BASE = "https://api-v3.mbta.com"

MAP_PDFS = [
    ("full_system_map", "https://www.mbta.com/system-map"),
    ("downtown_map", "https://www.mbta.com/downtown-map"),
    ("subway_map", "https://www.mbta.com/subway-map"),
    ("frequent_bus_route_map", "https://www.mbta.com/frequent-bus-map"),
    ("ferry_map", "https://cdn.mbta.com/sites/default/files/2024-05-ferry-map.pdf"),
    ("commuter_rail_map", "https://www.mbta.com/cr-map"),
    ("commuter_rail_zones_map", "https://www.mbta.com/cr-map-zones"),
]

RAPID_ROUTES = ["Red", "Mattapan", "Orange", "Blue", "Green-B", "Green-C", "Green-D", "Green-E"]
COMMUTER_RAIL_ROUTES = [
    "CR-Fairmount",
    "CR-Fitchburg",
    "CR-Worcester",
    "CR-Franklin",
    "CR-Greenbush",
    "CR-Haverhill",
    "CR-Kingston",
    "CR-Lowell",
    "CR-Middleborough",
    "CR-Needham",
    "CR-Newburyport",
    "CR-Providence",
]


@dataclass
class Asset:
    kind: str
    name: str
    url: str
    filename: str
    status: str = "pending"
    bytes: int = 0
    records: int = 0
    error: str = ""


def fetch_bytes(url: str, retries: int = 6) -> tuple[str, bytes, str]:
    req = Request(url, headers={"User-Agent": "UMassBostonTransportRAG/1.0"})
    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=45) as res:
                final_url = res.geturl()
                content_type = res.headers.get("content-type", "")
                payload = res.read()
            return final_url, payload, content_type
        except HTTPError as exc:
            if exc.code != 429 or attempt == retries:
                raise
            retry_after = exc.headers.get("retry-after")
            wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 5 * (attempt + 1)
            time.sleep(wait_seconds)
    raise RuntimeError(f"failed to fetch {url}")


def fetch_api(path: str, params: dict[str, str]) -> tuple[str, dict]:
    url = f"{API_BASE}{path}?{urlencode(params)}"
    final_url, payload, _content_type = fetch_bytes(url)
    return final_url, json.loads(payload.decode("utf-8"))


def write_json_data(name: str, filename: str, url: str, data: dict) -> Asset:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2) + "\n"
    (JSON_DIR / filename).write_text(content, encoding="utf-8")
    value = data.get("data")
    return Asset(
        kind="json",
        name=name,
        url=url,
        filename=filename,
        status="downloaded",
        bytes=len(content.encode("utf-8")),
        records=len(value) if isinstance(value, list) else int(bool(value)),
    )


def slug_from_pdf_url(name: str, url: str) -> str:
    path_name = Path(urlparse(url).path).name
    if path_name.lower().endswith(".pdf"):
        return re.sub(r"[^A-Za-z0-9._-]+", "-", path_name)
    return f"{name}.pdf"


def write_pdf(name: str, url: str) -> Asset:
    asset = Asset(kind="pdf", name=name, url=url, filename="")
    try:
        final_url, payload, content_type = fetch_bytes(url)
        if "pdf" not in content_type.lower() and not final_url.lower().endswith(".pdf"):
            raise RuntimeError(f"not a PDF: {content_type or final_url}")
        asset.url = final_url
        asset.filename = slug_from_pdf_url(name, final_url)
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        (PDF_DIR / asset.filename).write_bytes(payload)
        asset.bytes = len(payload)
        asset.records = 1
        asset.status = "downloaded"
    except Exception as exc:  # noqa: BLE001
        asset.status = "failed"
        asset.error = str(exc)
        asset.filename = f"{name}.pdf"
    return asset


def write_json(name: str, filename: str, path: str, params: dict[str, str]) -> Asset:
    asset = Asset(kind="json", name=name, url="", filename=filename)
    try:
        final_url, data = fetch_api(path, params)
        return write_json_data(name, filename, final_url, data)
    except Exception as exc:  # noqa: BLE001
        asset.status = "failed"
        asset.error = str(exc)
    return asset


def write_merged_route_json(name: str, filename: str, path: str, route_ids: list[str]) -> Asset:
    asset = Asset(kind="json", name=name, url="", filename=filename)
    try:
        by_id: dict[str, dict] = {}
        urls: list[str] = []
        for route_id in route_ids:
            final_url, data = fetch_api(path, {"filter[route]": route_id})
            urls.append(final_url)
            for item in data.get("data", []):
                by_id[item["id"]] = item
            time.sleep(0.75)
        merged = {
            "data": sorted(by_id.values(), key=lambda item: item["id"]),
            "meta": {
                "source": "MBTA V3 API",
                "route_count": len(route_ids),
                "routes": route_ids,
                "request_count": len(urls),
            },
        }
        return write_json_data(name, filename, ";".join(urls), merged)
    except Exception as exc:  # noqa: BLE001
        asset.status = "failed"
        asset.error = str(exc)
    return asset


def main() -> int:
    assets: list[Asset] = []

    for name, url in MAP_PDFS:
        assets.append(write_pdf(name, url))

    rapid_filter = ",".join(RAPID_ROUTES)
    commuter_filter = ",".join(COMMUTER_RAIL_ROUTES)
    assets.extend([
        write_json("rapid_transit_routes", "map_rapid_transit_routes.json", "/routes", {"filter[id]": rapid_filter}),
        write_merged_route_json("rapid_transit_stops", "map_rapid_transit_stops.json", "/stops", RAPID_ROUTES),
        write_merged_route_json("rapid_transit_route_patterns", "map_rapid_transit_route_patterns.json", "/route_patterns", RAPID_ROUTES),
        write_merged_route_json("rapid_transit_shapes", "map_rapid_transit_shapes.json", "/shapes", RAPID_ROUTES),
        write_json("commuter_rail_routes", "map_commuter_rail_routes.json", "/routes", {"filter[id]": commuter_filter}),
        write_merged_route_json("commuter_rail_stops", "map_commuter_rail_stops.json", "/stops", COMMUTER_RAIL_ROUTES),
        write_merged_route_json("commuter_rail_route_patterns", "map_commuter_rail_route_patterns.json", "/route_patterns", COMMUTER_RAIL_ROUTES),
        write_merged_route_json("commuter_rail_shapes", "map_commuter_rail_shapes.json", "/shapes", COMMUTER_RAIL_ROUTES),
    ])

    manifest = {
        "description": "Official MBTA map PDFs plus MBTA V3 map geometry for subway and commuter rail.",
        "routes": {
            "rapid_transit": RAPID_ROUTES,
            "commuter_rail": COMMUTER_RAIL_ROUTES,
        },
        "assets": [asdict(asset) for asset in assets],
    }
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    downloaded = [asset for asset in assets if asset.status == "downloaded"]
    print(f"downloaded {len(downloaded)} of {len(assets)} MBTA map assets")
    print(f"manifest: {MANIFEST}")
    return 0 if downloaded else 1


if __name__ == "__main__":
    raise SystemExit(main())
