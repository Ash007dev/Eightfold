from pathlib import Path

from transformer.__main__ import run_pipeline


ROOT = Path(__file__).resolve().parents[1]


def test_corrupt_ats_does_not_crash_pipeline() -> None:
    output = run_pipeline(ROOT / "samples" / "edge_garbage", ROOT / "configs" / "default.json")
    assert len(output) == 1
    assert output[0]["full_name"] == "Ananya Rao"
    assert output[0]["emails"] == ["ananya.rao@example.com"]
