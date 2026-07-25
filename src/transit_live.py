"""Small, server-side live transit lookup used by the chatbot."""

from __future__ import annotations

import re
import os
from difflib import SequenceMatcher
from datetime import datetime, timezone
from typing import Any, Optional


MBTA_PREDICTIONS_URL = "https://api-v3.mbta.com/predictions"
MBTA_STOPS_URL = "https://api-v3.mbta.com/stops"
DEFAULT_STOP = "place-jfk"
PURPLE_ROUTE_IDS = ("CR-NewBedford", "CR-Greenbush", "CR-Kingston")
ROUTE_STOPS_NEAR_CAMPUS = {
    # Both directions at the closest Route 16 stop pair near campus.
    "16": ("111,142", "Mt. Vernon St near South Point Dr"),
}
ROUTE_MAP_STOPS = {
    "16": "mbta-16-mt-vernon-in",
    "Red": "stop-jfk",
}
MBTA_STATION_ALIASES = {
    "jfk/umass": ("place-jfk", "JFK/UMass Station", 42.3204, -71.0518, "stop-jfk"),
    "jfk umass": ("place-jfk", "JFK/UMass Station", 42.3204, -71.0518, "stop-jfk"),
    "ashmont": ("place-asmnl", "Ashmont", 42.2843, -71.0644, "mbta-station-place-asmnl"),
    "shawmut": ("place-smmnl", "Shawmut", 42.2933, -71.0657, "mbta-station-place-smmnl"),
    "fields corner": ("place-fldcr", "Fields Corner", 42.3004, -71.0619, "mbta-station-place-fldcr"),
    "savin hill": ("place-shmnl", "Savin Hill", 42.3107, -71.0534, "mbta-station-place-shmnl"),
}

SHUTTLE_STOPS = {
    "jfk/umass": (104, "JFK/UMass Station"),
    "jfk umass": (104, "JFK/UMass Station"),
    "campus center": (105, "Campus Center"),
    "jfk library": (108, "JFK Library / Commonwealth Museum"),
    "commonwealth museum": (108, "JFK Library / Commonwealth Museum"),
    "bayside inbound": (109, "Bayside (Inbound)"),
    "bayside outbound": (107, "Bayside (Outbound)"),
    "bayside": (109, "Bayside (Inbound)"),
    "mt vernon inbound": (110, "Mt Vernon St (Inbound)"),
    "mt vernon outbound": (111, "Mt Vernon St (Outbound)"),
    "university drive west": (112, "University Drive West (Outbound)"),
}
SHUTTLE_MAP_STOPS = {
    "JFK/UMass Station": "stop-jfk",
    "Campus Center": "stop-campus-center",
    "JFK Library / Commonwealth Museum": "stop-jfk-library",
    "Bayside (Inbound)": "stop-bayside-in",
    "Bayside (Outbound)": "stop-bayside-out",
    "Mt Vernon St (Inbound)": "stop-mt-vernon-in",
    "Mt Vernon St (Outbound)": "stop-mt-vernon-out",
    "University Drive West (Outbound)": "stop-univ-drive-west",
}
SHUTTLE_GEO = {
    "stop-jfk": (104, "JFK/UMass Station", 42.32041, -71.05178),
    "stop-bayside-in": (109, "Bayside (Inbound)", 42.31947, -71.04660),
    "stop-mt-vernon-in": (110, "Mt Vernon St (Inbound)", 42.31722, -71.04032),
    "stop-jfk-library": (108, "JFK Library / Commonwealth Museum", 42.31515, -71.03544),
    "stop-campus-center": (105, "Campus Center", 42.31286, -71.03702),
    "stop-univ-drive-west": (112, "University Drive West (Outbound)", 42.31183, -71.03913),
    "stop-mt-vernon-out": (111, "Mt Vernon St (Outbound)", 42.31722, -71.04032),
    "stop-bayside-out": (107, "Bayside (Outbound)", 42.31947, -71.04660),
}
MBTA_ROUTE_GEO = {
    "16": (
        ("111", "Mt. Vernon St near South Point Dr", 42.317184, -71.040238, "mbta-16-mt-vernon-in"),
        ("142", "Mt. Vernon St near South Point Dr", 42.317207, -71.040611, "mbta-16-mt-vernon-out"),
    ),
}
STATIC_MBTA_ROUTE_GEO = {
    "Red": [
        ("place-jfk", "JFK/UMass Station", 42.3204, -71.0518),
        ("place-shmnl", "Savin Hill", 42.3107, -71.0534),
        ("place-fldcr", "Fields Corner", 42.3004, -71.0619),
        ("place-smmnl", "Shawmut", 42.2933, -71.0657),
        ("place-asmnl", "Ashmont", 42.2843, -71.0644),
        ("place-andrw", "Andrew", 42.3302, -71.0576),
        ("place-brdwy", "Broadway", 42.3426, -71.0572),
        ("place-sstat", "South Station", 42.3524, -71.0552),
        ("place-dwnxg", "Downtown Crossing", 42.3553, -71.0598),
        ("place-pktrm", "Park Street", 42.3563, -71.0628),
        ("place-harsq", "Harvard", 42.3736, -71.1190),
    ],
}

RETRIEVAL_ONLY_PATTERNS = (
    r"\bsemester\s+passes?\b",
    r"\bpasses?\b",
    r"\bvalid\b",
    r"\bvalidity\b",
    r"\brefund",
    r"\breplace",
    r"\badvertis",
    r"\bads?\b",
    r"\bdelivered?\b",
    r"\bphone\s+number\b",
    r"\bwhat\s+number\b",
    r"\bcontact\b",
    r"\bemail\b",
    r"\boperating\s+hours\b",
    r"\bhours\b",
    r"\bweekday\b.*\b(start|end)\b",
    r"\b(start|end)\b.*\bweekday\b",
    r"\bservice\b.*\b(start|end)\b",
    r"\b(start|end)\b.*\bservice\b",
    r"\bstops\s+does\b",
    r"\bserve\b",
    r"\broute\s+information\b",
    r"\bschedule\s+and\s+route\s+information\b",
    r"\baccepted\b.*\b(pay|payment|tickets?|cards?)",
    r"\b(pay|payment|tickets?|cards?).*\baccepted\b",
)

LIVE_TIME_PATTERNS = (
    r"\bwhen\b",
    r"\bnext\b",
    r"\barriv",
    r"\bdepart",
    r"\bsoon\b",
    r"\blive\b",
    r"\bwhat\s+time\b",
    r"\bhow\s+long\b",
    r"\buntil\b",
    r"\bcoming\b",
    r"\bcome\b",
)

SHUTTLE_STOP_ALIASES = {
    "jfk umass": ("stop-jfk",),
    "jfk station": ("stop-jfk",),
    "campus center": ("stop-campus-center",),
    "jfk library": ("stop-jfk-library",),
    "commonwealth museum": ("stop-jfk-library",),
    "bayside": ("stop-bayside-in", "stop-bayside-out"),
    "mt vernon inbound": ("stop-mt-vernon-in",),
    "mt vernon outbound": ("stop-mt-vernon-out",),
    "mt vernon": ("stop-mt-vernon-in", "stop-mt-vernon-out"),
    "vernon street": ("stop-mt-vernon-in", "stop-mt-vernon-out"),
    "vernon st": ("stop-mt-vernon-in", "stop-mt-vernon-out"),
    "university drive west": ("stop-univ-drive-west",),
}


def requested_route(query: str) -> Optional[str]:
    """Return an explicitly requested route number, if the query has one."""
    if re.search(r"\bcommuter\s+rail\b", query.lower()) or re.search(r"\bpurple\s+line\b", query.lower()):
        return "Purple"
    line = re.search(r"\b(red|orange|green|blue|silver)\s+line\b", query.lower())
    if line:
        return line.group(1).title()
    match = re.search(
        r"(?:route|bus|train|line|number|the|#)\s*[-#]?\s*(\d{1,3})\b|#\s*(\d{1,3})\b",
        query.lower(),
    )
    if not match:
        return None
    return next(group for group in match.groups() if group is not None)


def is_retrieval_transit_question(query: str) -> bool:
    q = query.lower()
    return any(re.search(pattern, q) for pattern in RETRIEVAL_ONLY_PATTERNS)


def is_live_transit_question(query: str) -> bool:
    q = query.lower()
    if is_retrieval_transit_question(query):
        return False
    has_live_time_intent = any(re.search(pattern, q) for pattern in LIVE_TIME_PATTERNS)
    nearest_live = bool(re.search(r"\b(nearest|closest)\b", q)) and bool(re.search(r"\b(bus|train|shuttle|mbta|transit)\b", q))
    return (
        (
            any(word in q for word in ("bus", "train", "subway", "mbta", "line", "route", "umass"))
            or bool(re.search(r"\bthe\s+\d{1,3}\b", q))
        )
        and (has_live_time_intent or nearest_live)
    )


def is_shuttle_question(query: str) -> bool:
    q = query.lower()
    if is_retrieval_transit_question(query):
        return False
    return (
        requested_route(query) is None
        and
        any(word in q for word in ("shuttle", "campus bus", "umass bus", "university bus"))
        and any(re.search(pattern, q) for pattern in LIVE_TIME_PATTERNS)
    )


def _normalize_stop_text(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).replace("street", "st").strip()


def resolve_shuttle_stops(query: str) -> list[dict[str, Any]]:
    """Resolve stop wording, including aliases and small typos."""
    q = _normalize_stop_text(query)
    matched_aliases: set[str] = set()
    exact_aliases: set[str] = set()
    for alias, stop_ids in SHUTTLE_STOP_ALIASES.items():
        alias_normalized = _normalize_stop_text(alias)
        if alias_normalized in q:
            matched_aliases.add(alias)
            exact_aliases.add(alias)

    # Fuzzy-match short stop phrases, e.g. "campuz cnter" or "vernon streeet".
    if not exact_aliases:
        words = q.split()
        for alias in SHUTTLE_STOP_ALIASES:
            alias_words = _normalize_stop_text(alias).split()
            width = len(alias_words)
            for start in range(max(1, len(words) - width + 1)):
                phrase = " ".join(words[start:start + width])
                if SequenceMatcher(None, phrase, _normalize_stop_text(alias)).ratio() >= 0.80:
                    matched_aliases.add(alias)

    # A directional phrase wins over a shorter parent phrase such as "mt vernon".
    if matched_aliases:
        longest = max(len(_normalize_stop_text(alias)) for alias in matched_aliases)
        matched_aliases = {
            alias for alias in matched_aliases
            if len(_normalize_stop_text(alias)) == longest
        }
    matched: set[str] = set()
    for alias in matched_aliases:
        matched.update(SHUTTLE_STOP_ALIASES[alias])

    return [
        {
            "map_stop_id": map_id,
            "stop_id": SHUTTLE_GEO[map_id][0],
            "stop_name": SHUTTLE_GEO[map_id][1],
        }
        for map_id in matched
    ]


def _shuttle_stop(query: str) -> Optional[tuple[int, str]]:
    stops = resolve_shuttle_stops(query)
    if len(stops) != 1:
        return None
    stop = stops[0]
    return stop["stop_id"], stop["stop_name"]


def has_shuttle_stop(query: str) -> bool:
    return bool(resolve_shuttle_stops(query))


def shuttle_followup_needed(query: str) -> bool:
    return is_shuttle_question(query) and _shuttle_stop(query) is None


def _nearest(items: list[tuple], latitude: float, longitude: float) -> tuple:
    return min(items, key=lambda item: (item[2] - latitude) ** 2 + (item[3] - longitude) ** 2)


def _distance_miles(latitude: float, longitude: float, stop_latitude: float, stop_longitude: float) -> float:
    """Approximate walking-start distance for explaining the selected stop."""
    from math import asin, cos, radians, sin, sqrt
    earth_miles = 3958.8
    d_lat = radians(stop_latitude - latitude)
    d_lng = radians(stop_longitude - longitude)
    a = sin(d_lat / 2) ** 2 + cos(radians(latitude)) * cos(radians(stop_latitude)) * sin(d_lng / 2) ** 2
    return round(earth_miles * 2 * asin(sqrt(a)), 2)


def _location_tuple(location: Optional[dict[str, Any]]) -> Optional[tuple[float, float]]:
    try:
        latitude = float(location["latitude"])
        longitude = float(location["longitude"])
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return latitude, longitude
    except (TypeError, KeyError, ValueError):
        pass
    return None


def transit_stop_followup_needed(query: str, location: Optional[dict[str, Any]]) -> bool:
    """Ask for a stop when live arrivals need a location but GPS was unavailable."""
    if not is_live_transit_question(query) or _location_tuple(location):
        return False
    if any(term in query.lower() for term in ("jfk", "station")) or any(alias in query.lower() for alias in MBTA_STATION_ALIASES) or resolve_shuttle_stops(query):
        return False
    return True


def lookup_live_shuttle(query: str, location: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    """Look up UMass shuttle arrivals when the user names a campus stop."""
    stop = _shuttle_stop(query)
    stop_options = resolve_shuttle_stops(query)
    coords = _location_tuple(location)
    if not is_shuttle_question(query) or (stop is None and not stop_options and coords is None):
        return None

    distance_miles = None
    if stop is None and stop_options and coords:
        lat, lng = coords
        nearest_option = min(
            stop_options,
            key=lambda option: (SHUTTLE_GEO[option["map_stop_id"]][2] - lat) ** 2
            + (SHUTTLE_GEO[option["map_stop_id"]][3] - lng) ** 2,
        )
        stop = nearest_option["stop_id"], nearest_option["stop_name"]

    if stop is None and stop_options:
        return None

    if stop is None:
        lat, lng = coords
        map_stop_id, (stop_id, stop_name, _, _) = min(
            SHUTTLE_GEO.items(),
            key=lambda item: (item[1][2] - lat) ** 2 + (item[1][3] - lng) ** 2,
        )
    else:
        stop_id, stop_name = stop
        map_stop_id = SHUTTLE_MAP_STOPS[stop_name]

    transloc_key = os.getenv("TRANSLOC_API_KEY", "")
    if not transloc_key:
        return None

    if coords:
        geo = SHUTTLE_GEO[map_stop_id]
        distance_miles = _distance_miles(coords[0], coords[1], geo[2], geo[3])

    import requests as http

    try:
        response = http.get(
            "https://umb.transloc.com/Services/JSONPRelay.svc/GetStopArrivalTimes",
            params={"apiKey": transloc_key, "routeStopIDs": stop_id},
            headers={"Referer": "https://umb.transloc.com/", "User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None

    arrivals = []
    for item in payload if isinstance(payload, list) else []:
        for arrival in item.get("Times", []) or []:
            seconds = arrival.get("Seconds")
            if seconds is None:
                continue
            arrivals.append({"minutes": max(0, round(seconds / 60))})
    arrivals.sort(key=lambda item: item["minutes"])
    return {
        "stop": stop_name,
        "map_stop_id": map_stop_id,
        "arrivals": arrivals[:5],
        "checked_at": datetime.now(timezone.utc).strftime("%I:%M %p UTC").lstrip("0"),
        "distance_miles": distance_miles,
        "source": "https://umb.transloc.com/",
    }


def format_shuttle_context(live: dict[str, Any]) -> str:
    distance = f" ({live['distance_miles']} miles away)" if live.get("distance_miles") is not None else ""
    if not live["arrivals"]:
        return (
            f"LIVE UMass SHUTTLE LOOKUP at {live['stop']}{distance}: No upcoming shuttle "
            "prediction was returned. Do not invent an arrival time."
        )
    lines = []
    for arrival in live["arrivals"]:
        lines.append("- arriving now" if arrival["minutes"] <= 1 else f"- arriving in {arrival['minutes']} min")
    return (
        f"LIVE UMass SHUTTLE LOOKUP at {live['stop']}{distance}:\n" + "\n".join(lines) +
        "\nUse these live results in the answer, and say they can change."
    )


def _route_name(item: dict[str, Any], routes: dict[str, dict[str, Any]]) -> str:
    route_id = item.get("relationships", {}).get("route", {}).get("data", {}).get("id", "")
    return routes.get(route_id, {}).get("attributes", {}).get("long_name") or route_id


def _nearest_mbta_stop(route: str, latitude: float, longitude: float) -> Optional[tuple[str, str, float, float]]:
    import requests as http

    try:
        response = http.get(
            MBTA_STOPS_URL,
            params={"filter[route]": route, "filter[route_type]": 1 if route in {"Red", "Orange", "Green-B", "Green-C", "Green-D", "Green-E", "Blue", "Silver"} else 3},
            timeout=8,
        )
        response.raise_for_status()
        stops = []
        for item in response.json().get("data", []):
            attrs = item.get("attributes", {})
            if attrs.get("latitude") is not None and attrs.get("longitude") is not None:
                stops.append((
                    item["id"], attrs.get("name", "MBTA stop"),
                    float(attrs["latitude"]), float(attrs["longitude"]),
                ))
        return _nearest(stops, latitude, longitude) if stops else None
    except Exception:
        return None


def lookup_live_arrivals(
    query: str,
    stop: str = DEFAULT_STOP,
    location: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Look up the next MBTA arrivals for a route explicitly named by the user.

    Returns None when the question is not a supported live lookup or when the
    upstream service is unavailable. Failures are intentionally non-fatal so
    the normal knowledge-base answer still works.
    """
    if not is_live_transit_question(query):
        return None
    route = requested_route(query)
    if not route:
        return None

    import requests as http

    station_match = next(
        (details for alias, details in MBTA_STATION_ALIASES.items() if alias in query.lower()),
        None,
    )
    asks_for_jfk = any(term in query.lower() for term in ("jfk", "station"))
    route_filter = ",".join(PURPLE_ROUTE_IDS) if route == "Purple" else route
    coords = _location_tuple(location)
    dynamic_map_stop = None
    distance_miles = None
    explicit_route_16_stop = route == "16" and any(
        phrase in query.lower() for phrase in ("mt vernon", "vernon street", "vernon st")
    )
    if station_match and route == "Red":
        route_stop_filter, stop_name, stop_lat, stop_lng, map_stop_id = station_match
        dynamic_map_stop = {
            "id": map_stop_id,
            "name": stop_name,
            "coords": [stop_lat, stop_lng],
            "type": "mbta",
            "mbtaStopId": route_stop_filter,
            "route": route,
            "routes": ["Red Line"],
            "notes": f"MBTA Red Line station selected: {stop_name}.",
        }
        if coords:
            distance_miles = _distance_miles(coords[0], coords[1], stop_lat, stop_lng)
    elif explicit_route_16_stop:
        route_stop_filter, stop_name = ROUTE_STOPS_NEAR_CAMPUS["16"]
        map_stop_id = ROUTE_MAP_STOPS["16"]
    elif asks_for_jfk:
        route_stop_filter, stop_name, map_stop_id = stop, "JFK/UMass Station", "stop-jfk"
    elif coords and route in MBTA_ROUTE_GEO:
        lat, lng = coords
        route_stop_filter, stop_name, stop_lat, stop_lng, map_stop_id = _nearest(MBTA_ROUTE_GEO[route], lat, lng)
        distance_miles = _distance_miles(lat, lng, stop_lat, stop_lng)
    elif coords:
        lat, lng = coords
        nearest = _nearest_mbta_stop(route, *coords)
        if not nearest and route in STATIC_MBTA_ROUTE_GEO:
            nearest = _nearest(STATIC_MBTA_ROUTE_GEO[route], *coords)
        if not nearest:
            return None
        route_stop_filter, stop_name, stop_lat, stop_lng = nearest
        map_stop_id = f"mbta-stop-{route_stop_filter}"
        dynamic_map_stop = {
            "id": map_stop_id,
            "name": stop_name,
            "coords": [stop_lat, stop_lng],
            "type": "mbta" if route in {"Red", "Orange", "Green", "Blue", "Silver"} else "mbta-bus",
            "mbtaStopId": route_stop_filter,
            "route": route,
            "routes": [f"{route} Line" if route in {"Red", "Orange", "Green", "Blue", "Silver"} else f"Bus {route}"],
            "notes": f"MBTA Route {route} stop selected near your location.",
        }
        distance_miles = _distance_miles(lat, lng, stop_lat, stop_lng)
    else:
        # Never silently turn an unlocated request into JFK/UMass. The caller
        # normally asks for location first, but this guard keeps a future call
        # path from returning a misleading campus default.
        return None
    params = {
        "filter[stop]": route_stop_filter,
        "filter[route]": route_filter,
        "sort": "departure_time",
        "include": "trip,route",
    }
    try:
        response = http.get(MBTA_PREDICTIONS_URL, params=params, timeout=8)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None

    trips = {
        item["id"]: item.get("attributes", {})
        for item in payload.get("included", [])
        if item.get("type") == "trip"
    }
    routes = {
        item["id"]: item
        for item in payload.get("included", [])
        if item.get("type") == "route"
    }
    now = datetime.now(timezone.utc)
    arrivals = []
    for item in payload.get("data", []):
        attrs = item.get("attributes", {})
        timestamp = attrs.get("departure_time") or attrs.get("arrival_time")
        if not timestamp:
            continue
        try:
            arrival_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            minutes = max(0, round((arrival_at - now).total_seconds() / 60))
        except (TypeError, ValueError):
            continue
        trip_id = item.get("relationships", {}).get("trip", {}).get("data", {}).get("id")
        arrivals.append({
            "minutes": minutes,
            "time": arrival_at.strftime("%I:%M %p").lstrip("0"),
            "destination": trips.get(trip_id, {}).get("headsign", ""),
            "route_name": _route_name(item, routes),
        })

    arrivals.sort(key=lambda item: (item["minutes"], item["time"]))
    return {
        "route": route,
        "stop": stop_name,
        "map_stop_id": map_stop_id,
        "map_stop": dynamic_map_stop,
        "arrivals": arrivals[:5],
        "checked_at": now.strftime("%I:%M %p UTC").lstrip("0"),
        "distance_miles": distance_miles,
        "source": "https://www.mbta.com/",
    }


def format_live_context(live: dict[str, Any]) -> str:
    distance = f" ({live['distance_miles']} miles away)" if live.get("distance_miles") is not None else ""
    if not live["arrivals"]:
        return (
            f"LIVE TRANSIT LOOKUP (checked {live['checked_at']}): No upcoming MBTA "
            f"predictions were returned for route {live['route']} at {live['stop']}{distance}. "
            "Do not invent an arrival time; mention that no prediction is currently available."
        )
    lines = []
    for arrival in live["arrivals"]:
        destination = f" toward {arrival['destination']}" if arrival["destination"] else ""
        when = "now" if arrival["minutes"] <= 1 else f"in {arrival['minutes']} min"
        lines.append(f"- {when} ({arrival['time']}){destination}")
    return (
        f"LIVE TRANSIT LOOKUP (checked {live['checked_at']}) for MBTA route {live['route']} "
        f"at {live['stop']}{distance}:\n" + "\n".join(lines) +
        "\nUse these live results in the answer, and say they can change."
    )
