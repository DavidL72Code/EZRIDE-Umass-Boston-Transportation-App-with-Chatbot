import json
import os
import re
import sys
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory
from flask import stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024

ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080,https://davidl72code-ezride-umass.hf.space,https://ezride-umass-boston-transportation.vercel.app",
    ).split(",")
    if origin.strip()
}
CORS(app, resources={r"/api/*": {"origins": sorted(ALLOWED_ORIGINS)}})

_RATE_LIMITS = {
    "/api/chat": (20, 60),
    "/api/walk-route": (30, 60),
    "/api/mbta/predictions": (60, 60),
    "/api/transit/arrivals": (60, 60),
}
_rate_events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_rate_lock = threading.Lock()


@app.before_request
def enforce_api_limits():
    if not request.path.startswith("/api/"):
        return None
    limit, window = _RATE_LIMITS.get(request.path, (60, 60))
    now = time.monotonic()
    key = (request.remote_addr or "unknown", request.path)
    with _rate_lock:
        events = _rate_events[key]
        while events and events[0] <= now - window:
            events.popleft()
        if len(events) >= limit:
            retry_after = max(1, int(window - (now - events[0])))
            response = jsonify({"error": "rate limit exceeded", "retry_after_seconds": retry_after})
            response.status_code = 429
            response.headers["Retry-After"] = str(retry_after)
            return response
        events.append(now)
    return None


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(self), camera=(), microphone=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com; img-src 'self' data: blob: https:; "
        "connect-src 'self' https:; font-src 'self' https:; object-src 'none'",
    )
    return response


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "request body too large"}), 413


@app.errorhandler(500)
def internal_error(_error):
    return jsonify({"error": "internal server error"}), 500

_retriever = None
_llm = None
_init_lock = threading.Lock()


def _init():
    """Load the embedding model, search indexes, and LLM once at startup."""
    global _retriever, _llm

    from src.indexing.embedder import Embedder
    from src.retrieval.retriever import HybridRetriever

    print("[startup] Loading sentence-transformers model and search indexes…")
    _retriever = HybridRetriever(
        ROOT / "index" / "bm25",
        ROOT / "index" / "faiss",
        Embedder(),
        semantic_weight=0.75,
    )
    print("[startup] Search indexes ready.")

    key = os.getenv("GOOGLE_API_KEY", "")
    if key:
        try:
            from src.llm.gemini_llm import GeminiLLM
            _llm = GeminiLLM(api_key=key)
            print("[startup] Gemini LLM ready.")
        except Exception as e:
            print(f"[startup] Gemini LLM failed to load: {e}")
    else:
        print("[startup] No GOOGLE_API_KEY — running without LLM.")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/chat")
def chat_page():
    return send_from_directory("static", "chat.html")


@app.route("/parking-rates")
def parking_rates():
    return send_from_directory("static", "parking-rates.html")


@app.route("/blue-bikes")
def blue_bikes():
    return send_from_directory("static", "blue-bikes.html")


@app.route("/transit")
def transit():
    return send_from_directory("static", "transit.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"error": "empty message"}), 400
    if len(message) > 4000:
        return jsonify({"error": "message too long"}), 413
    if not isinstance(history, list) or len(history) > 24:
        return jsonify({"error": "history too long"}), 413

    def generate():
        from src.transit_live import (
            format_live_context,
            format_shuttle_context,
            lookup_live_arrivals,
            lookup_live_shuttle,
            has_shuttle_stop,
            is_live_transit_question,
            is_shuttle_question,
            requested_route,
            resolve_shuttle_stops,
            transit_stop_followup_needed,
            shuttle_followup_needed,
        )

        location = data.get("location")
        pending_original = history[-3].get("content", "") if len(history) >= 3 else ""
        shuttle_options = resolve_shuttle_stops(message)
        pending_shuttle = (
            len(history) >= 3
            and is_shuttle_question(pending_original)
            and (
                "i need a stop to check live arrivals" in history[-2].get("content", "").lower()
                or "which umass shuttle stop" in history[-2].get("content", "").lower()
                or "inbound or outbound" in history[-2].get("content", "").lower()
            )
        )
        pending_transit = (
            len(history) >= 3
            and is_live_transit_question(pending_original)
            and any(
                phrase in history[-2].get("content", "").lower()
                for phrase in (
                    "i need your location or a stop",
                    "tell me the stop name",
                )
            )
        )
        if (is_shuttle_question(message) or pending_shuttle) and len(shuttle_options) > 1 and not location:
            yield _event("status", text="")
            yield _event("token", text="Do you mean the Mt. Vernon shuttle inbound or outbound stop?")
            yield _event("done", sources=[])
            return
        if transit_stop_followup_needed(message, location):
            yield _event("status", text="")
            route = requested_route(message)
            if route:
                route_label = "Commuter Rail (Purple)" if route == "Purple" else f"{route} Line" if route in {"Red", "Orange", "Green", "Blue", "Silver"} else f"Route {route}"
                prompt = (
                    f"I need your location or a stop for {route_label} to check live arrivals. "
                    "Please allow location access, or tell me the stop name."
                )
            elif is_shuttle_question(message):
                prompt = (
                    "I need your location or a UMass shuttle stop to check live arrivals. "
                    "Please allow location access, or tell me the stop name—for example "
                    "JFK/UMass Station, Campus Center, Bayside, JFK Library, or Mt. Vernon Street."
                )
            else:
                prompt = (
                    "I need your location or a transit stop to check live arrivals. "
                    "Please allow location access, or tell me the stop name."
                )
            yield _event("token", text=prompt)
            route = requested_route(message)
            yield _event("done", sources=[{
                "url": "https://www.mbta.com/" if route else "https://www.umb.edu/transportation/shuttle-bus-information/",
                "title": "MBTA live arrivals" if route else "UMass shuttle stops",
                "category": "transit",
            }])
            return

        yield _event("status", text="🔍 Searching knowledge base…")
        prior_user_message = ""
        # The browser includes the current user turn in history. Find the
        # preceding user topic so short follow-ups such as "How much?" or
        # "What about weekends?" retrieve the right documents.
        for previous in reversed(history[:-1] if history and history[-1].get("content") == message else history):
            if previous.get("role") == "user" and previous.get("content"):
                prior_user_message = previous["content"]
                break
        followup_like = len(message.split()) <= 8 or bool(
            re.match(r"^(how much|what about|and |what if|where|when|can i|is it|are they)\b", message.lower())
        )
        retrieval_query = (
            f"{prior_user_message}\nFollow-up question: {message}"
            if prior_user_message and followup_like and not is_live_transit_question(message)
            else message
        )
        results = _retriever.search(retrieval_query, top_k=5)
        transit_query = message
        if pending_transit and not location:
            # The follow-up may only be a stop name (e.g. "Ashmont"). Carry
            # forward the original route so it remains a live lookup.
            transit_query = f"{pending_original} at {message}"
        live_mbta = lookup_live_arrivals(transit_query, location=location)
        shuttle_query = message
        if (
            len(history) >= 2
            and bool(shuttle_options)
            and (
                "which umass shuttle stop" in history[-2].get("content", "").lower()
                or "i need a stop to check live arrivals" in history[-2].get("content", "").lower()
                or "inbound or outbound" in history[-2].get("content", "").lower()
            )
        ):
            shuttle_query = f"when is the next UMass shuttle at {message}"
        live_shuttle = lookup_live_shuttle(shuttle_query, location=location)
        live_context = "\n\n".join(filter(None, [
            format_live_context(live_mbta) if live_mbta else "",
            format_shuttle_context(live_shuttle) if live_shuttle else "",
        ]))

        if not results and not live_context:
            yield _event("status", text="")
            yield _event("token", text=(
                "I couldn't find specific information about that. "
                "Try rephrasing your question, or visit "
                "umb.edu/transportation/ directly."
            ))
            yield _event("done", sources=[])
            return

        categories = list({item["chunk"].get("category", "general") for item in results})
        if live_context:
            yield _event("status", text="🚌 Checking live transit arrivals…")
        yield _event("status", text=f"📄 Found {len(results)} chunks ({', '.join(categories)})")

        if _llm is None:
            yield _event("status", text="")
            parts = []
            for i, item in enumerate(results[:3], 1):
                c = item["chunk"]
                snippet = c["text"][:300].rsplit(" ", 1)[0] + "…"
                parts.append(f"**[{i}] {c.get('title', 'Source')}**\n{snippet}")
            if live_context:
                yield _event("token", text=live_context)
            if parts:
                yield _event("token", text=("\n\n" if live_context else "") + "\n\n".join(parts))
        else:
            yield _event("status", text="⚡ Generating response…")
            try:
                for event_type, text in _llm.answer_stream(
                    message, results, history=history[-6:], extra_context=live_context
                ):
                    yield _event("status", text="")
                    yield _event(event_type, text=text)
            except Exception as exc:
                yield _event("status", text="")
                yield _event("token", text=f"_(Error: {exc})_")

        seen: set = set()
        sources = []
        # A live arrival answer should not be followed by unrelated parking or
        # visitor-document links. Those chips make a real-time result look
        # fabricated, even when the live lookup succeeded.
        if not live_context:
            for item in results:
                c = item["chunk"]
                url = c.get("source_url", "")
                if url and url not in seen:
                    seen.add(url)
                    sources.append({
                        "url": url,
                        "title": (c.get("title") or url)[:60],
                        "category": c.get("category", "general"),
                    })
        if live_context:
            live_result = live_mbta or live_shuttle
            yield _event(
                "map_focus",
                stop_id=live_result["map_stop_id"],
                stop=live_result.get("map_stop"),
                transit={
                    "route": live_result.get("route", "UMass shuttle"),
                    "stop": live_result.get("stop", "Selected stop"),
                    "checked_at": live_result.get("checked_at"),
                    "distance_miles": live_result.get("distance_miles"),
                },
            )
            sources.append({
                "url": (live_mbta or live_shuttle)["source"],
                "title": "Live transit arrivals",
                "category": "transit",
            })
        yield _event("done", sources=sources)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _event(type: str, **kwargs) -> str:
    return f"data: {json.dumps({'type': type, **kwargs})}\n\n"


@app.route("/api/mbta/predictions")
def mbta_predictions():
    stop = request.args.get("stop", "")
    route = request.args.get("route", "")
    direction = request.args.get("direction", "")
    if not stop:
        return jsonify({"data": [], "included": []})
    if not re.fullmatch(r"[A-Za-z0-9_-]+(?:,[A-Za-z0-9_-]+)*", stop):
        return jsonify({"error": "invalid stop id"}), 400
    if route and not re.fullmatch(r"[A-Za-z0-9_-]+(?:,[A-Za-z0-9_-]+)*", route):
        return jsonify({"error": "invalid route id"}), 400
    if direction and direction not in {"0", "1"}:
        return jsonify({"error": "invalid direction"}), 400
    try:
        import requests as http
        route_type = request.args.get("route_type", "")
        params = {
            "filter[stop]": stop,
            "sort": "departure_time",
            "include": "trip",
        }
        if route:
            params["filter[route]"] = route
        if route_type:
            params["filter[route_type]"] = route_type
        if direction != "":
            params["filter[direction_id]"] = direction
        r = http.get(
            "https://api-v3.mbta.com/predictions",
            params=params,
            timeout=8,
        )
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/walk-route", methods=["POST"])
def walk_route():
    api_key = os.getenv("STADIA_API_KEY", "")
    if not api_key:
        return jsonify({"error": "STADIA_API_KEY not configured"}), 503
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON object required"}), 400
    try:
        import requests as http
        r = http.post(
            f"https://api.stadiamaps.com/route/v1?api_key={api_key}",
            json=payload,
            timeout=15,
        )
        return Response(r.content, status=r.status_code, mimetype="application/json")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/transit/arrivals")
def transit_arrivals():
    stop_id = request.args.get("stop_id", "")
    if not stop_id:
        return jsonify([])
    if not stop_id.isdigit():
        return jsonify({"error": "invalid shuttle stop id"}), 400
    api_key = os.getenv("TRANSLOC_API_KEY", "")
    if not api_key:
        return jsonify({"error": "TRANSLOC_API_KEY not configured"}), 503
    try:
        import requests as http
        r = http.get(
            "https://umb.transloc.com/Services/JSONPRelay.svc/GetStopArrivalTimes",
            params={"apiKey": api_key, "routeStopIDs": stop_id},
            headers={"Referer": "https://umb.transloc.com/", "User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


_init()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True, use_reloader=False)
