"""Deterministic parking intent handling for the chatbot."""

from __future__ import annotations

import re
from math import asin, cos, radians, sin, sqrt
from typing import Any, Optional


PARKING_SOURCE = "https://www.umb.edu/transportation/parking-rates/"
PARKING_OPTIONS = (
    "West Garage",
    "Campus Center Garage",
    "Lot D",
    "Quad Lot",
    "Bayside Lot",
)
PARKING_LOTS = (
    {
        "name": "West Garage",
        "kind": "garage",
        "coords": (42.31518, -71.04151),
        "rate": "$7.00 minimum, $15.00 daily max, $10.00 evening/weekend",
    },
    {
        "name": "Lot D",
        "kind": "lot",
        "coords": (42.31691, -71.03875),
        "rate": "$15.00 daily, $10.00 evening/weekend",
    },
    {
        "name": "Campus Center Garage",
        "kind": "garage",
        "coords": (42.31286, -71.03702),
        "rate": "$15.00 daily, $10.00 evening/weekend",
    },
    {
        "name": "Quad Lot",
        "kind": "lot",
        "coords": (42.31450, -71.03824),
        "rate": "$15.00 daily, $10.00 evening/weekend",
    },
    {
        "name": "Bayside Lot",
        "kind": "lot",
        "coords": (42.32068, -71.04627),
        "rate": "$9.00 daily",
    },
)


def _normalized(query: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", query.lower())


def asks_parking_price(query: str) -> bool:
    q = _normalized(query)
    policy_or_permit_terms = (
        "fine",
        "ticket",
        "citation",
        "permit",
        "pass",
        "resident",
        "reserved",
        "student",
        "faculty",
        "employee",
        "commuter",
        "semester",
        "academic",
        "fall",
        "spring",
        "summer",
    )
    if any(term in q for term in policy_or_permit_terms):
        return False
    time_rate_terms = ("evening", "weekend", "after 4", "4 pm", "4pm", "daily maximum", "daily max")
    if any(term in q for term in time_rate_terms):
        return False
    return "parking" in q and any(term in q for term in ("how much", "cost", "price", "rate", "fee"))


def mentions_specific_lot(query: str) -> bool:
    q = _normalized(query)
    lot_terms = (
        "west garage",
        "campus center",
        "campus center garage",
        "lot d",
        "quad lot",
        "bayside",
        "emk",
        "kennedy",
        "archives",
        "jfk library",
    )
    return any(term in q for term in lot_terms)


def ambiguous_parking_price_question(query: str) -> bool:
    return asks_parking_price(query) and not mentions_specific_lot(query)


def parking_price_followup() -> str:
    options = "\n".join(f"- {name}" for name in PARKING_OPTIONS)
    return f"Which parking location do you mean?\n\n{options}"


def asks_nearby_parking(query: str) -> bool:
    q = _normalized(query)
    return "parking" in q and any(
        term in q
        for term in (
            "near me",
            "nearest",
            "closest",
            "nearby",
            "near my location",
            "where can i park near",
        )
    )


def location_tuple(location: Optional[dict[str, Any]]) -> Optional[tuple[float, float]]:
    try:
        latitude = float(location["latitude"])
        longitude = float(location["longitude"])
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return latitude, longitude
    except (TypeError, KeyError, ValueError):
        pass
    return None


def distance_miles(latitude: float, longitude: float, dest_latitude: float, dest_longitude: float) -> float:
    earth_miles = 3958.8
    d_lat = radians(dest_latitude - latitude)
    d_lng = radians(dest_longitude - longitude)
    a = sin(d_lat / 2) ** 2 + cos(radians(latitude)) * cos(radians(dest_latitude)) * sin(d_lng / 2) ** 2
    return round(earth_miles * 2 * asin(sqrt(a)), 2)


def nearest_parking_answer(location: Optional[dict[str, Any]]) -> str:
    coords = location_tuple(location)
    if not coords:
        return (
            "I need your location to find the closest parking. Please allow location access, "
            "or tell me where you are starting from."
        )

    lat, lng = coords
    ranked = sorted(
        (
            {
                **lot,
                "distance": distance_miles(lat, lng, lot["coords"][0], lot["coords"][1]),
            }
            for lot in PARKING_LOTS
        ),
        key=lambda item: item["distance"],
    )
    lines = [
        f"The closest parking options from your location are:",
        "",
    ]
    for lot in ranked[:3]:
        lines.append(f"- **{lot['name']}**: {lot['distance']} miles away; {lot['rate']}.")
    return "\n".join(lines)
