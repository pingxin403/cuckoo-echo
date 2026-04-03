"""Ragas Quality Gate — automated RAG quality evaluation.

Reads test cases from JSON, runs Ragas evaluation, outputs a report
with pass/fail judgment based on configurable thresholds.

Usage:
    uv run python scripts/ragas_quality_gate.py \
        --test-cases tests/quality/test_cases.json \
        --output reports/ragas_report.json

Thresholds (configurable via env vars):
    RAGAS_FAITHFULNESS_MIN=0.85
    RAGAS_CONTEXT_PRECISION_MIN=0.80
    RAGAS_CONTEXT_RECALL_MIN=0.75
    RAGAS_ANSWER_RELEVANCY_MIN=0.85
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone


# Thresholds
THRESHOLDS = {
    "faithfulness": float(os.environ.get("RAGAS_FAITHFULNESS_MIN", "0.85")),
    "context_precision": float(os.environ.get("RAGAS_CONTEXT_PRECISION_MIN", "0.80")),
    "context_recall": float(os.environ.get("RAGAS_CONTEXT_RECALL_MIN", "0.75")),
    "answer_relevancy": float(os.environ.get("RAGAS_ANSWER_RELEVANCY_MIN", "0.85")),
}


def load_test_cases(path: str) -> list[dict]:
    """Load test cases from JSON file."""
    with open(path) as f:
        return json.load(f)


def run_evaluation(test_cases: list[dict]) -> dict:
    """Run Ragas evaluation on test cases.

    Returns a dict with per-metric scores and overall pass/fail.
    """
    try:
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
        from datasets import Dataset

        # Convert test cases to Ragas dataset format
        data = {
            "question": [tc["question"] for tc in test_cases],
            "answer": [tc.get("answer", "") for tc in test_cases],
            "contexts": [tc.get("contexts", []) for tc in test_cases],
            "ground_truth": [tc.get("ground_truth", "") for tc in test_cases],
        }
        dataset = Dataset.from_dict(data)

        result = evaluate(
            dataset,
            metrics=[faithfulness, context_precision, context_recall, answer_relevancy],
        )

        scores = {
            "faithfulness": float(result["faithfulness"]),
            "context_precision": float(result["context_precision"]),
            "context_recall": float(result["context_recall"]),
            "answer_relevancy": float(result["answer_relevancy"]),
        }
        return scores

    except ImportError:
        print("WARNING: ragas not installed. Running in mock mode.")
        return _mock_evaluation(test_cases)
    except Exception as e:
        print(f"WARNING: Ragas evaluation failed: {e}. Running in mock mode.")
        return _mock_evaluation(test_cases)


def _mock_evaluation(test_cases: list[dict]) -> dict:
    """Mock evaluation for testing without LLM API key."""
    return {
        "faithfulness": 0.0,
        "context_precision": 0.0,
        "context_recall": 0.0,
        "answer_relevancy": 0.0,
    }


def generate_report(scores: dict, thresholds: dict, test_cases_path: str) -> dict:
    """Generate a quality gate report with pass/fail judgment."""
    results = {}
    all_passed = True

    for metric, score in scores.items():
        threshold = thresholds.get(metric, 0.0)
        passed = score >= threshold
        if not passed:
            all_passed = False
        results[metric] = {
            "score": round(score, 4),
            "threshold": threshold,
            "passed": passed,
        }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_cases_path": test_cases_path,
        "overall_passed": all_passed,
        "metrics": results,
        "thresholds": thresholds,
    }


def main():
    parser = argparse.ArgumentParser(description="Ragas Quality Gate")
    parser.add_argument("--test-cases", required=True, help="Path to test cases JSON")
    parser.add_argument("--output", default="reports/ragas_report.json", help="Output report path")
    args = parser.parse_args()

    print(f"Loading test cases from {args.test_cases}...")
    test_cases = load_test_cases(args.test_cases)
    print(f"Loaded {len(test_cases)} test cases.")

    print("Running Ragas evaluation...")
    scores = run_evaluation(test_cases)

    report = generate_report(scores, THRESHOLDS, args.test_cases)

    # Write report
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report written to {args.output}")

    # Print summary
    print("\n=== Ragas Quality Gate Report ===")
    for metric, result in report["metrics"].items():
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  {metric}: {result['score']:.4f} (threshold: {result['threshold']}) {status}")

    if report["overall_passed"]:
        print("\n✅ Quality gate PASSED")
        sys.exit(0)
    else:
        print("\n❌ Quality gate FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
