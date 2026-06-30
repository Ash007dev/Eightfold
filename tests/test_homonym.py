from pathlib import Path

from transformer.__main__ import run_pipeline


ROOT = Path(__file__).resolve().parents[1]


def test_same_name_without_shared_identity_does_not_merge() -> None:
    output = run_pipeline(ROOT / "samples" / "edge_homonym", ROOT / "configs" / "default.json")
    assert len(output) == 2
    assert [record["full_name"] for record in output] == ["Sam Patel", "Sam Patel"]
    assert sorted(record["emails"][0] for record in output) == ["sam.backend@example.com", "sam.data@example.com"]
