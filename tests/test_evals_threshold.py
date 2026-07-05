from pathlib import Path

from evals.run_evals import meets_threshold, pass_rate, write_results


def test_pass_rate_equal_threshold_passes():
    rows = [{"passed": "true"}, {"passed": "false"}]
    assert pass_rate(rows) == 0.5
    assert meets_threshold(rows, 0.5)


def test_pass_rate_below_threshold_fails():
    rows = [{"passed": "true"}, {"passed": "false"}]
    assert not meets_threshold(rows, 0.8)


def test_write_results_uses_requested_path(tmp_path):
    path = tmp_path / "eval_results.csv"
    rows = [
        {
            "case_id": "case",
            "expected_keywords": "a|b",
            "matched_keywords": "a",
            "passed": "true",
            "latency_ms": 1,
        }
    ]
    write_results(rows, Path(path))
    assert path.exists()
    assert "case_id,expected_keywords,matched_keywords,passed,latency_ms" in path.read_text(
        encoding="utf-8"
    )
