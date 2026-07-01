"""The human report should expose skill provenance and existing breakdown keys."""

from pathlib import Path

from transformer.__main__ import build_records
from transformer.report import render_report


ROOT = Path(__file__).resolve().parents[1]


def test_report_contains_skill_names_and_breakdown_keys() -> None:
    records = build_records(ROOT / "samples" / "candidate_01")
    report = render_report(records)
    assert "Python" in report
    assert "breakdown=" in report
    assert "github_authored" in report
    assert "leetcode_cross_confirm" in report
