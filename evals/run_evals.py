import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import get_config  # noqa: E402
from core_graph import app as agent_workflow, create_initial_state  # noqa: E402


CASES_PATH = Path(__file__).with_name("cases.jsonl")
RESULTS_PATH = Path(__file__).with_name("eval_results.csv")
DEFAULT_API_URL = "http://127.0.0.1:8000/review"


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _extract_sse_report(text: str) -> str:
    report = ""
    for line in text.splitlines():
        if not line.startswith("data: "):
            continue
        payload = json.loads(line[6:])
        if payload.get("event") == "done":
            data = payload.get("data") or {}
            report = data.get("report", report)
    return report


def run_case_local(code: str, allow_llm: bool = False) -> str:
    if not allow_llm:
        os.environ["OPENAI_API_KEY"] = ""
        get_config.cache_clear()
    state = agent_workflow.invoke(create_initial_state(code))
    return state.get("final_report", "")


def run_case_api(code: str, api_url: str) -> str:
    response = requests.post(api_url, json={"code": code}, timeout=180)
    response.raise_for_status()
    return _extract_sse_report(response.text)


def evaluate(
    use_api: bool = False, api_url: str = DEFAULT_API_URL, allow_llm: bool = False
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in load_cases():
        started_at = time.perf_counter()
        report = (
            run_case_api(case["code"], api_url)
            if use_api
            else run_case_local(case["code"], allow_llm=allow_llm)
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        lower_report = report.lower()
        expected = case["expected_keywords"]
        matched = [keyword for keyword in expected if keyword.lower() in lower_report]
        rows.append(
            {
                "case_id": case["case_id"],
                "expected_keywords": "|".join(expected),
                "matched_keywords": "|".join(matched),
                "passed": str(bool(matched)).lower(),
                "latency_ms": latency_ms,
            }
        )
    return rows


def write_results(rows: list[dict[str, Any]], path: Path = RESULTS_PATH) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "case_id",
                "expected_keywords",
                "matched_keywords",
                "passed",
                "latency_ms",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def pass_rate(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    passed = sum(row["passed"] == "true" for row in rows)
    return passed / len(rows)


def meets_threshold(rows: list[dict[str, Any]], threshold: float) -> bool:
    return pass_rate(rows) >= threshold


def main() -> None:
    parser = argparse.ArgumentParser(description="Run lightweight ReviewBot eval cases.")
    parser.add_argument("--use-api", action="store_true", help="Call a running FastAPI backend.")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--allow-llm", action="store_true", help="Allow local evals to use configured LLM credentials.")
    parser.add_argument("--min-pass-rate", type=float, default=0.8)
    args = parser.parse_args()

    rows = evaluate(use_api=args.use_api, api_url=args.api_url, allow_llm=args.allow_llm)
    write_results(rows)
    passed = sum(row["passed"] == "true" for row in rows)
    rate = pass_rate(rows)
    ok = meets_threshold(rows, args.min_pass_rate)
    result = "PASS" if ok else "FAIL"
    print(
        f"Eval complete. passed={passed}/{len(rows)} "
        f"pass_rate={rate:.2f} threshold={args.min_pass_rate:.2f} "
        f"result={result} output={RESULTS_PATH}"
    )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
