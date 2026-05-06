import os
from typing import Optional, Iterator

try:
    import google.generativeai as genai
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

# Module-level singleton — created once when GeminiLLM is first instantiated.
_genai_model = None


class GeminiLLM:
    def __init__(self, api_key: Optional[str] = None, model: str = MODEL) -> None:
        global _genai_model
        if not HAS_GENAI:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")
        if _genai_model is None:
            key = api_key or os.getenv("GOOGLE_API_KEY", "")
            if not key:
                raise ValueError("GOOGLE_API_KEY not set. Add it to your .env file.")
            genai.configure(api_key=key)
            _genai_model = genai.GenerativeModel(
                model_name=model,
                system_instruction=SYSTEM_PROMPT,
                generation_config=genai.GenerationConfig(max_output_tokens=512),
            )
        self._model = _genai_model

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

    def count_prompt_tokens(self, query: str, chunks: list) -> int:
        try:
            prompt = self._build_prompt(query, chunks)
            result = self._model.count_tokens(prompt)
            return result.total_tokens
        except Exception:
            return -1

    def _history_to_genai(self, history: list) -> list:
        result = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            result.append({"role": role, "parts": [msg["content"]]})
        return result

    def answer(self, query: str, chunks: list, history: Optional[list] = None) -> str:
        chat = self._model.start_chat(history=self._history_to_genai(history or []))
        response = chat.send_message(self._build_prompt(query, chunks))
        return response.text

    def answer_stream(
        self, query: str, chunks: list, history: Optional[list] = None
    ) -> Iterator[str]:
        chat = self._model.start_chat(history=self._history_to_genai(history or []))
        response = chat.send_message(self._build_prompt(query, chunks), stream=True)
        for chunk in response:
            yield chunk.text
        try:
            usage = response.usage_metadata
            print(f"[tokens] input={usage.prompt_token_count} output={usage.candidates_token_count}")
        except Exception:
            pass
