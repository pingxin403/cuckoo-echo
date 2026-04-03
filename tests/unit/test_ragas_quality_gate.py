"""Unit tests for Ragas quality gate script.

Covers:
- Report generation with passing scores
- Report generation with failing scores
- Test case loading
- Mock evaluation fallback
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

# Import from the script
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from ragas_quality_gate import generate_report, load_test_cases, _mock_evaluation, THRESHOLDS


class TestGenerateReport:
    def test_all_passing(self):
        """All metrics above threshold → overall_passed = True."""
        scores = {
            "faithfulness": 0.90,
            "context_precision": 0.85,
            "context_recall": 0.80,
            "answer_relevancy": 0.90,
        }
        report = generate_report(scores, THRESHOLDS, "test.json")

        assert report["overall_passed"] is True
        for metric in scores:
            assert report["metrics"][metric]["passed"] is True

    def test_one_failing(self):
        """One metric below threshold → overall_passed = False."""
        scores = {
            "faithfulness": 0.50,  # Below 0.85
            "context_precision": 0.85,
            "context_recall": 0.80,
            "answer_relevancy": 0.90,
        }
        report = generate_report(scores, THRESHOLDS, "test.json")

        assert report["overall_passed"] is False
        assert report["metrics"]["faithfulness"]["passed"] is False
        assert report["metrics"]["context_precision"]["passed"] is True

    def test_all_failing(self):
        """All metrics below threshold → overall_passed = False."""
        scores = {
            "faithfulness": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "answer_relevancy": 0.0,
        }
        report = generate_report(scores, THRESHOLDS, "test.json")

        assert report["overall_passed"] is False

    def test_report_has_timestamp(self):
        scores = {"faithfulness": 0.9, "context_precision": 0.9,
                  "context_recall": 0.9, "answer_relevancy": 0.9}
        report = generate_report(scores, THRESHOLDS, "test.json")
        assert "timestamp" in report
        assert "T" in report["timestamp"]  # ISO format


class TestLoadTestCases:
    def test_load_valid_json(self):
        """Loads test cases from a valid JSON file."""
        cases = [{"question": "test?", "answer": "yes", "contexts": ["ctx"], "ground_truth": "yes"}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(cases, f)
            f.flush()
            loaded = load_test_cases(f.name)

        assert len(loaded) == 1
        assert loaded[0]["question"] == "test?"
        os.unlink(f.name)


class TestMockEvaluation:
    def test_returns_zero_scores(self):
        """Mock evaluation returns all zeros."""
        scores = _mock_evaluation([{"question": "test"}])
        assert all(v == 0.0 for v in scores.values())
        assert "faithfulness" in scores
