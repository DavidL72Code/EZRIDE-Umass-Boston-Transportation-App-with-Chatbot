import os
from typing import Optional, Iterator

try:
    import google.genai as genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

SYSTEM_PROMPT = """You are a helpful parking and transportation assistant for UMass Boston \
(University of Massachusetts Boston). Your job is to help students, faculty, staff, and visitors \
with questions about parking permits, parking rates, fines, MBTA passes, shuttle buses, \
visitor parking, and commuting options on campus.

Guidelines:
- Give clear, actionable answers about parking permits, costs, locations, and procedures.
- Reference specific UMass Boston lots, garages, rates, or programs whenever the context supports it.
- If the provided context does not contain enough information, say so honestly rather than guessing.
- Keep answers concise — 2–4 sentences unless the question is complex.
- Do not repeat source URLs in your answer text; they are shown separately to the user.
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
            thinking_config=types.ThinkingConfig(thinking_budget=512),
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
