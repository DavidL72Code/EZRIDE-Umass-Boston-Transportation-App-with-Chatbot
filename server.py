import json
import os
import sys
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory
from flask import stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

app = Flask(__name__, static_folder="static", static_url_path="")

CORS(app)

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
        semantic_weight=0.6,
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
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"error": "empty message"}), 400

    results = _retriever.search(message, top_k=5)

    def generate():
        if not results:
            text = (
                "I couldn't find specific information about that. "
                "Try rephrasing your question, or visit "
                "umb.edu/transportation/ directly."
            )
            yield _event("token", text=text)
            yield _event("done", sources=[])
            return

        if _llm is None:
            parts = []
            for i, item in enumerate(results[:3], 1):
                c = item["chunk"]
                snippet = c["text"][:300].rsplit(" ", 1)[0] + "…"
                parts.append(f"**[{i}] {c.get('title', 'Source')}**\n{snippet}")
            yield _event("token", text="\n\n".join(parts))
        else:
            try:
                for token in _llm.answer_stream(message, results, history=history[-6:]):
                    yield _event("token", text=token)
            except Exception as exc:
                yield _event("token", text=f"_(Error: {exc})_")

        seen: set = set()
        sources = []
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


@app.route("/api/transit/arrivals")
def transit_arrivals():
    stop_id = request.args.get("stop_id", "")
    if not stop_id:
        return jsonify([])
    try:
        import requests as http
        r = http.get(
            "https://umb.transloc.com/Services/JSONPRelay.svc/GetStopArrivalTimes",
            params={"apiKey": "8882812681", "routeStopIDs": stop_id},
            headers={"Referer": "https://umb.transloc.com/", "User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    _init()
    app.run(host="0.0.0.0", port=8080, threaded=True, use_reloader=False)
