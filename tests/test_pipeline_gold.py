import json
from pathlib import Path

from transformer.__main__ import run_pipeline


ROOT = Path(__file__).resolve().parents[1]


def test_candidate_01_matches_gold() -> None:
    actual = run_pipeline(ROOT / "samples" / "candidate_01", ROOT / "configs" / "default.json")
    expected = json.loads((ROOT / "samples" / "candidate_01.gold.json").read_text(encoding="utf-8"))
    assert actual == expected
