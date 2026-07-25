"""
RAG pipeline evaluation: compares RAG answers vs. direct LLM answers
on 10 grounded questions. Scores each on 5 dimensions using Gemini as judge.

Usage:
    python scripts/evaluate.py                  # full eval
    python scripts/evaluate.py --debug-retrieval  # show retrieved chunks per question
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.indexing.embedder import Embedder
from src.retrieval.retriever import HybridRetriever
from src.llm.gemini_llm import GeminiLLM
import google.genai as genai
from google.genai import types

ROOT = Path(__file__).parent.parent

QUESTIONS = [
    {
        "id": 1,
        "question": "How many EV charging ports does UMass Boston have on campus, and where are they located?",
        "expected": "23 total — 15 at West Garage, 4 at Campus Center Garage, 4 at Quad Lot",
        "category": "general",
    },
    {
        "id": 2,
        "question": "What is the fine for parking in an EV charging space without actually charging?",
        "expected": "$75",
        "category": "enforcement",
    },
    {
        "id": 3,
        "question": "How do I cancel my UMass Boston parking permit?",
        "expected": "Log into parking portal → View Permits → click permit number → click Return Permit button",
        "category": "permits",
    },
    {
        "id": 4,
        "question": "What is the carpool subsidy benefit for UMass Boston employees?",
        "expected": "Each rider switching from driving alone to a carpool can earn up to three months of $15 gas cards",
        "category": "general",
    },
    {
        "id": 5,
        "question": "How long is the maximum charging session at a ChargePoint EV station on campus?",
        "expected": "4 hours maximum per session",
        "category": "general",
    },
    {
        "id": 6,
        "question": "What happens if I don't pay or appeal a parking ticket within 21 days?",
        "expected": "License and registration sent to RMV for non-renewal; delinquent notices issued",
        "category": "enforcement",
    },
    {
        "id": 7,
        "question": "How much does an annual Blue Bikes membership cost for UMass Boston affiliates?",
        "expected": "$101.50 with promo code BikeUMB",
        "category": "transit",
    },
    {
        "id": 8,
        "question": "What is the Guaranteed Ride Home benefit and how many rides does it include?",
        "expected": "Up to six free Uber rides home per year under qualifying circumstances",
        "category": "general",
    },
    {
        "id": 9,
        "question": "What is the EV charging cost per kWh at UMass Boston campus stations?",
        "expected": "$0.22 per kWh",
        "category": "general",
    },
    {
        "id": 10,
        "question": "How can a UMass Boston student get access to a bike locker?",
        "expected": "Lockers available at McCormack and Wheatley Peters, managed by Student Activities, first-come first-served",
        "category": "transit",
    },
]

# Key terms to check retrieval hit per question
RETRIEVAL_HINTS = {
    1: ["23", "west garage", "campus center", "quad"],
    2: ["75", "ev", "charging space"],
    3: ["return permit", "cancel"],
    4: ["gas card", "carpool"],
    5: ["4 hour", "four hour", "maximum"],
    6: ["rmv", "non-renewal", "21 days"],
    7: ["101.50", "bikeumb"],
    8: ["six", "uber", "guaranteed ride"],
    9: ["0.22", "kwh"],
    10: ["locker", "student activities"],
}

SCORE_PROMPT = """You are evaluating a chatbot answer against an expected answer for a university transportation assistant.

Question: {question}
Expected answer: {expected}
Chatbot answer: {answer}

Score the chatbot answer on each of these 5 dimensions from 1 (poor) to 5 (excellent):
1. Accuracy - Is the factual information correct?
2. Completeness - Does it cover all key parts of the expected answer?
3. Relevance - Is the answer focused and on-topic?
4. Conciseness - Is it appropriately brief without unnecessary padding?
5. Groundedness - Is it based on specific facts rather than vague generalities?

Respond ONLY with valid JSON in this exact format:
{{"accuracy": X, "completeness": X, "relevance": X, "conciseness": X, "groundedness": X, "comment": "one sentence"}}"""


def check_retrieval_hit(chunks: list, hints: list) -> bool:
    combined = " ".join(item["chunk"]["text"].lower() for item in chunks)
    return all(h.lower() in combined for h in hints)


def get_rag_answer(retriever, llm, question, debug=False):
    chunks = retriever.search(question, top_k=5)

    if debug:
        print(f"  --- Retrieved chunks ---")
        for i, item in enumerate(chunks, 1):
            c = item["chunk"]
            snippet = c["text"][:120].replace("\n", " ")
            print(f"  [{i}] score={item['score']:.4f} | {c.get('source_url','').split('/')[-2] or 'home'} | {snippet}…")

    if not chunks:
        return "No relevant information found.", chunks

    tokens = []
    for token in llm.answer_stream(question, chunks):
        tokens.append(token)
    return "".join(tokens), chunks


def get_direct_answer(llm, question):
    tokens = []
    for token in llm.answer_stream(question, []):
        tokens.append(token)
    return "".join(tokens)


def score_answer(judge, question, expected, answer):
    prompt = SCORE_PROMPT.format(question=question, expected=expected, answer=answer)
    response = judge.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        ),
    )
    try:
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        return {"accuracy": 0, "completeness": 0, "relevance": 0, "conciseness": 0, "groundedness": 0, "comment": f"parse error: {e}"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug-retrieval", action="store_true", help="Print retrieved chunks for each question")
    args = parser.parse_args()

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set"); sys.exit(1)

    print("Loading retriever…")
    embedder = Embedder()
    retriever = HybridRetriever(
        ROOT / "index" / "bm25",
        ROOT / "index" / "faiss",
        embedder,
        semantic_weight=0.75,
    )
    llm = GeminiLLM(api_key=api_key)
    judge = genai.Client(api_key=api_key)

    results = []
    retrieval_hits = []

    for q in QUESTIONS:
        print(f"\n[{q['id']}/10] {q['question'][:60]}…")

        rag_answer, chunks = get_rag_answer(retriever, llm, q["question"], debug=args.debug_retrieval)

        hints = RETRIEVAL_HINTS.get(q["id"], [])
        hit = check_retrieval_hit(chunks, hints)
        retrieval_hits.append(hit)
        if args.debug_retrieval:
            print(f"  Retrieval hit: {'YES' if hit else 'NO'} (looking for: {hints})")

        time.sleep(4)
        direct_answer = get_direct_answer(llm, q["question"])
        time.sleep(4)
        rag_scores = score_answer(judge, q["question"], q["expected"], rag_answer)
        time.sleep(4)
        direct_scores = score_answer(judge, q["question"], q["expected"], direct_answer)
        time.sleep(4)

        result = {
            "id": q["id"],
            "question": q["question"],
            "expected": q["expected"],
            "category": q["category"],
            "rag_answer": rag_answer,
            "direct_answer": direct_answer,
            "rag_scores": rag_scores,
            "direct_scores": direct_scores,
            "retrieval_hit": hit,
        }
        results.append(result)
        print(f"  RAG scores: {rag_scores}")
        print(f"  Direct scores: {direct_scores}")

    out_path = ROOT / "scripts" / "eval_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved → {out_path}")

    dims = ["accuracy", "completeness", "relevance", "conciseness", "groundedness"]
    print("\n=== SUMMARY ===")
    print(f"{'Dimension':<15} {'RAG avg':>8} {'Direct avg':>10}")
    for d in dims:
        rag_avg = sum(r["rag_scores"].get(d, 0) for r in results) / len(results)
        dir_avg = sum(r["direct_scores"].get(d, 0) for r in results) / len(results)
        print(f"{d:<15} {rag_avg:>8.2f} {dir_avg:>10.2f}")

    hits = sum(retrieval_hits)
    print(f"\nRetrieval hits: {hits}/{len(QUESTIONS)} questions had all key terms in top-5 chunks")


if __name__ == "__main__":
    main()
