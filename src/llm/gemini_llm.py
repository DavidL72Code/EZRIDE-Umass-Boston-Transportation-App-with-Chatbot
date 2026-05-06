import os
from typing import Optional, Iterator

try:
    import google.genai as genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

SYSTEM_PROMPT = """You are a parking and transportation assistant for UMass Boston. \
Answer questions about parking permits, fines, rates, MBTA passes, shuttles, biking, and visitor parking.

Data you have access to:
- enforcement: Parking fines in three groups:
    Group A ($150): violations 101-104 — handicapped/HP space violations
    Group B ($75): violations 105-106, 113 — tow zones, fire lanes, controlled areas
    Group B ($35): violations 107-117 — sidewalk, hydrant, intersection, bus stop, snow removal, etc.
    Group C ($35): violation 124 — access lane
    Group C ($25): violations 118-123, 125-128 — double parking, driveway, curb, no-parking zones, etc.
    Group C ($0): violation 129 — no fine
    Also covers: appealing a ticket (online within 21 days), paying fines online or by mail, towing, RMV holds.
- permits: Permit types, parking rates by lot/garage, carpool registration, accessible parking.
- transit: MBTA semester passes, subway/commuter rail coverage, shuttle bus schedules and stops.
- visitor: Visitor parking options, directions, campus map, visitor rates.
- general: Overview of all transportation services, e-bike/e-scooter charging at West Garage (13 Saris Power Posts).

Guidelines:
- When answering about a fine, always include the violation code, description, and dollar amount.
- When answering about prices or rates, always include the exact dollar figure from the context.
- If the context doesn't cover the question, say so — do not guess.
- Keep answers concise — 2-4 sentences unless listing multiple items.
- Do not repeat source URLs; they are shown separately.
"""

MODEL = "gemini-3.1-flash-lite-preview"

_client: Optional["genai.Client"] = None


class GeminiLLM:
    def __init__(self, api_key: Optional[str] = None, model: str = MODEL) -> None:
        global _client
        if not HAS_GENAI:
            raise ImportError("google-genai not installed. Run: pip install google-genai")
        if _client is None:
            key = api_key or os.getenv("GOOGLE_API_KEY", "")
            if not key:
                raise ValueError("GOOGLE_API_KEY not set. Add it to your .env file.")
            _client = genai.Client(api_key=key)
        self._client = _client
        self._model = model
        self._config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=512,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

    def _build_context(self, chunks: list) -> str:
        parts = []
        for i, item in enumerate(chunks, 1):
            c = item["chunk"]
            parts.append(
                f"[{i}] {c.get('title', '')} — {c.get('headings', [''])[0]}\n"
                f"{c['text']}"
            )
        return "\n\n---\n\n".join(parts)

    def _build_prompt(self, query: str, chunks: list) -> str:
        context = self._build_context(chunks)
        return f"Context:\n{context}\n\nQuestion: {query}"

    def _build_contents(self, query: str, chunks: list, history: list) -> list:
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
        contents.append(types.Content(role="user", parts=[types.Part(text=self._build_prompt(query, chunks))]))
        return contents

    def answer(self, query: str, chunks: list, history: Optional[list] = None) -> str:
        contents = self._build_contents(query, chunks, history or [])
        response = self._client.models.generate_content(
            model=self._model, contents=contents, config=self._config
        )
        return response.text

    def answer_stream(
        self, query: str, chunks: list, history: Optional[list] = None
    ) -> Iterator[str]:
        contents = self._build_contents(query, chunks, history or [])
        for chunk in self._client.models.generate_content_stream(
            model=self._model, contents=contents, config=self._config
        ):
            if chunk.text:
                yield chunk.text
