#!/usr/bin/env python3
"""Collect official MBTA data relevant to UMass Boston transportation.

This uses the public MBTA V3 API rather than scraping mbta.com HTML. The output
is structured JSON that can feed RAG alongside the UMass Boston PDF/image scrape.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "data" / "transportation_media" / "mbta"
JSON_DIR = OUT_ROOT / "json"
MANIFEST = OUT_ROOT / "manifest.json"

API_BASE = "https://api-v3.mbta.com"
UMASS_CENTER = (42.3135, -71.0384)
NEARBY_RADIUS_MILES = 1.6

CORE_ROUTES = ["Red", "8", "16"]
CORE_STOPS = ["place-jfk"]


@dataclass
class Dataset:
    name: str
    url: str
    filename: str
    status: str = "pending"
    records: int = 0
    bytes: int = 0
    error: str = ""


def fetch_json(path: str, params: dict[str, str] | None = None) -> tuple[str, dict[str, Any]]:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{API_BASE}{path}{query}"
    req = Request(url, headers={"User-Agent": "UMassBostonTransportRAG/1.0"})
    with urlopen(req, timeout=25) as res:
        payload = res.read()
    return url, json.loads(payload.decode("utf-8"))


def write_json(filename: str, data: dict[str, Any]) -> int:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    path = JSON_DIR / filename
    content = json.dumps(data, indent=2) + "\n"
    path.write_text(content, encoding="utf-8")
    return len(content.encode("utf-8"))


def record_count(data: dict[str, Any]) -> int:
    value = data.get("data")
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return 1
    return 0


def collect(name: str, filename: str, path: str, params: dict[str, str] | None = None) -> Dataset:
    dataset = Dataset(name=name, url="", filename=filename)
    try:
        url, data = fetch_json(path, params)
        dataset.url = url
        dataset.bytes = write_json(filename, data)
        dataset.records = record_count(data)
        dataset.status = "downloaded"
    except Exception as exc:  # noqa: BLE001 - manifest should capture all fetch failures.
        dataset.status = "failed"
        dataset.error = str(exc)
    return dataset


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return radius_miles * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def collect_nearby_stops() -> Dataset:
    dataset = Dataset(
        name="nearby_stops_umass_boston",
        url=f"{API_BASE}/stops?filter[latitude]={UMASS_CENTER[0]}&filter[longitude]={UMASS_CENTER[1]}",
        filename="nearby_stops_umass_boston.json",
    )
    try:
        _url, data = fetch_json(
            "/stops",
            {
                "filter[latitude]": str(UMASS_CENTER[0]),
                "filter[longitude]": str(UMASS_CENTER[1]),
                "filter[radius]": str(NEARBY_RADIUS_MILES),
                "include": "route",
            },
        )
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            lat, lon = attrs.get("latitude"), attrs.get("longitude")
            if lat is not None and lon is not None:
                attrs["distance_from_umass_miles"] = round(
                    haversine_miles(UMASS_CENTER[0], UMASS_CENTER[1], float(lat), float(lon)),
                    3,
                )
        data["data"] = [
            item for item in data.get("data", [])
            if item.get("attributes", {}).get("distance_from_umass_miles", NEARBY_RADIUS_MILES + 1) <= NEARBY_RADIUS_MILES
        ]
        dataset.url = _url
        dataset.bytes = write_json(dataset.filename, data)
        dataset.records = record_count(data)
        dataset.status = "downloaded"
    except Exception as exc:  # noqa: BLE001
        dataset.status = "failed"
        dataset.error = str(exc)
    return dataset


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    datasets: list[Dataset] = []

    datasets.append(collect_nearby_stops())

    for stop_id in CORE_STOPS:
        datasets.append(collect(f"stop_{stop_id}", f"stop_{stop_id}.json", f"/stops/{stop_id}"))
        datasets.append(collect(f"facilities_{stop_id}", f"facilities_{stop_id}.json", "/facilities", {"filter[stop]": stop_id}))
        datasets.append(collect(f"alerts_{stop_id}", f"alerts_{stop_id}.json", "/alerts", {"filter[stop]": stop_id}))

    for route_id in CORE_ROUTES:
        safe = route_id.lower().replace("-", "_")
        datasets.append(collect(f"route_{route_id}", f"route_{safe}.json", f"/routes/{route_id}"))
        datasets.append(collect(f"route_patterns_{route_id}", f"route_patterns_{safe}.json", "/route_patterns", {"filter[route]": route_id}))
        datasets.append(collect(f"stops_{route_id}", f"stops_{safe}.json", "/stops", {"filter[route]": route_id}))
        datasets.append(collect(f"schedules_{route_id}_jfk", f"schedules_{safe}_jfk.json", "/schedules", {"filter[route]": route_id, "filter[stop]": "place-jfk", "include": "trip"}))
        datasets.append(collect(f"alerts_{route_id}", f"alerts_{safe}.json", "/alerts", {"filter[route]": route_id}))

    manifest = {
        "description": "Official MBTA V3 API data relevant to UMass Boston transportation.",
        "api_base": API_BASE,
        "focus": {
            "campus_center": {"lat": UMASS_CENTER[0], "lon": UMASS_CENTER[1]},
            "routes": CORE_ROUTES,
            "stops": CORE_STOPS,
            "nearby_radius_miles": NEARBY_RADIUS_MILES,
        },
        "output_root": str(OUT_ROOT.relative_to(ROOT)),
        "datasets": [asdict(dataset) for dataset in datasets],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    downloaded = [dataset for dataset in datasets if dataset.status == "downloaded"]
    print(f"downloaded {len(downloaded)} of {len(datasets)} MBTA datasets")
    print(f"manifest: {MANIFEST}")
    return 0 if downloaded else 1


if __name__ == "__main__":
    raise SystemExit(main())
