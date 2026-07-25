#!/usr/bin/env python3
"""Run endpoint-level chatbot evals against Flask's /api/chat SSE response."""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"
QUESTIONS_PATH = EVAL_DIR / "questions_25.json"


def parse_sse(body: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in body.split("\n\n"):
        if not block.startswith("data: "):
            continue
        try:
            events.append(json.loads(block[6:]))
        except json.JSONDecodeError as exc:
            events.append({"type": "parse_error", "error": str(exc), "raw": block})
    return events


def text_from_events(events: list[dict[str, Any]]) -> str:
    return "".join(event.get("text", "") for event in events if event.get("type") == "token")


def done_sources(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    done = [event for event in events if event.get("type") == "done"]
    return done[-1].get("sources", []) if done else []


def evaluate_expectations(case: dict[str, Any], answer: str, events: list[dict[str, Any]], sources: list[dict[str, Any]]) -> dict[str, Any]:
    expect = case.get("expect", {})
    answer_lower = answer.lower()
    source_urls = [source.get("url", "") for source in sources]
    media_sources = [source for source in sources if source.get("category") == "transportation_media" or source.get("media_type")]
    pdf_sources = [source for source in sources if source.get("media_type") == "pdf" or source.get("url", "").lower().endswith(".pdf")]
    image_sources = [
        source
        for source in sources
        if source.get("media_type") == "image"
        or source.get("url", "").lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ]
    map_focus_events = [event for event in events if event.get("type") == "map_focus"]

    checks: dict[str, Any] = {}
    if expect.get("must_include_all"):
        checks["must_include_all"] = all(term.lower() in answer_lower for term in expect["must_include_all"])
    if expect.get("must_include_any"):
        checks["must_include_any"] = any(term.lower() in answer_lower for term in expect["must_include_any"])
    if expect.get("must_source_media"):
        checks["must_source_media"] = bool(media_sources)
    if expect.get("must_source_pdf"):
        checks["must_source_pdf"] = bool(pdf_sources)
    if expect.get("must_source_image"):
        checks["must_source_image"] = bool(image_sources)
    if expect.get("must_not_source_media"):
        checks["must_not_source_media"] = not media_sources and not any("/media/transportation/" in url for url in source_urls)
    if expect.get("must_not_map_focus"):
        checks["must_not_map_focus"] = not map_focus_events
    if expect.get("allow_media") is False:
        checks["no_media_unless_explicit"] = not media_sources

    return {
        "passed": all(checks.values()) if checks else True,
        "checks": checks,
        "observed": {
            "source_count": len(sources),
            "media_source_count": len(media_sources),
            "pdf_source_count": len(pdf_sources),
            "image_source_count": len(image_sources),
            "map_focus_count": len(map_focus_events),
        },
    }


def run_eval(question_path: Path, out_prefix: str) -> dict[str, Path]:
    import sys

    sys.path.insert(0, str(ROOT))
    import server  # noqa: PLC0415

    question_path = question_path.resolve()
    cases = json.loads(question_path.read_text(encoding="utf-8"))
    client = server.app.test_client()
    results = []

    for index, case in enumerate(cases, 1):
        payload = {
            "message": case["question"],
            "history": [{"role": "user", "content": case["question"]}],
        }
        if case.get("location"):
            payload["location"] = case["location"]

        attempts = 0
        total_elapsed_ms = 0
        while True:
            attempts += 1
            started = time.monotonic()
            response = client.post(
                "/api/chat",
                json=payload,
                environ_overrides={"REMOTE_ADDR": f"eval-{index}-{attempts}"},
            )
            total_elapsed_ms += round((time.monotonic() - started) * 1000)
            body = response.get_data(as_text=True)
            events = parse_sse(body)
            answer = text_from_events(events)
            if "RESOURCE_EXHAUSTED" not in answer or attempts >= 4:
                break
            match = re.search(r"retry in ([0-9.]+)s", answer, re.IGNORECASE)
            wait_seconds = float(match.group(1)) + 3 if match else 65
            print(f"  quota retry for {case['id']} in {wait_seconds:.1f}s")
            time.sleep(wait_seconds)

        sources = done_sources(events)
        eval_result = evaluate_expectations(case, answer, events, sources)

        result = {
            "id": case["id"],
            "type": case["type"],
            "question": case["question"],
            "status_code": response.status_code,
            "elapsed_ms": total_elapsed_ms,
            "attempts": attempts,
            "answer": answer,
            "sources": sources,
            "events": events,
            "expectation_result": eval_result,
        }
        results.append(result)
        verdict = "PASS" if eval_result["passed"] and response.status_code == 200 else "FAIL"
        retry_note = f", attempts={attempts}" if attempts > 1 else ""
        print(f"[{index:02d}/{len(cases)}] {verdict} {case['id']} ({total_elapsed_ms} ms{retry_note})")

    total = len(results)
    passed = sum(1 for result in results if result["status_code"] == 200 and result["expectation_result"]["passed"])
    by_type: dict[str, dict[str, int]] = {}
    for result in results:
        bucket = by_type.setdefault(result["type"], {"total": 0, "passed": 0})
        bucket["total"] += 1
        if result["status_code"] == 200 and result["expectation_result"]["passed"]:
            bucket["passed"] += 1

    summary = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "question_file": str(question_path.relative_to(ROOT) if question_path.is_relative_to(ROOT) else question_path),
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 3) if total else 0,
        "by_type": by_type,
        "failures": [
            {
                "id": result["id"],
                "type": result["type"],
                "question": result["question"],
                "status_code": result["status_code"],
                "checks": result["expectation_result"]["checks"],
                "observed": result["expectation_result"]["observed"],
                "answer": result["answer"][:500],
                "sources": result["sources"],
            }
            for result in results
            if result["status_code"] != 200 or not result["expectation_result"]["passed"]
        ],
    }

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = EVAL_DIR / f"{out_prefix}_raw.json"
    summary_path = EVAL_DIR / f"{out_prefix}_summary.json"
    report_path = EVAL_DIR / f"{out_prefix}_report.md"
    raw_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(render_report(summary, results), encoding="utf-8")
    return {"raw": raw_path, "summary": summary_path, "report": report_path}


def render_report(summary: dict[str, Any], results: list[dict[str, Any]]) -> str:
    lines = [
        "# Chatbot Eval Report",
        "",
        f"- Run: {summary['run_at']}",
        f"- Total: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Pass rate: {summary['pass_rate']:.1%}",
        "",
        "## Results",
        "",
        "| ID | Type | Status | Checks | Sources | Map focus |",
        "|---|---|---:|---|---:|---:|",
    ]
    for result in results:
        expectation = result["expectation_result"]
        status = "PASS" if result["status_code"] == 200 and expectation["passed"] else "FAIL"
        checks = ", ".join(
            f"{name}={'yes' if value else 'no'}"
            for name, value in expectation["checks"].items()
        )
        observed = expectation["observed"]
        lines.append(
            f"| {result['id']} | {result['type']} | {status} | {checks or 'n/a'} | "
            f"{observed['source_count']} | {observed['map_focus_count']} |"
        )

    if summary["failures"]:
        lines.extend(["", "## Failures", ""])
        for failure in summary["failures"]:
            lines.extend([
                f"### {failure['id']}",
                "",
                f"Question: {failure['question']}",
                "",
                f"Checks: `{json.dumps(failure['checks'])}`",
                "",
                f"Observed: `{json.dumps(failure['observed'])}`",
                "",
                f"Answer excerpt: {failure['answer']}",
                "",
            ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=QUESTIONS_PATH)
    parser.add_argument("--out-prefix", default=f"chatbot_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    args = parser.parse_args()
    paths = run_eval(args.questions, args.out_prefix)
    print("\nSaved:")
    for key, path in paths.items():
        print(f"  {key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
