"""The full sample pipeline must emit byte-identical JSON on repeated runs."""

import json
from pathlib import Path

from transformer.__main__ import run_pipeline


ROOT = Path(__file__).resolve().parents[1]


def test_candidate_01_output_is_byte_identical_twice() -> None:
    first = json.dumps(run_pipeline(ROOT / "samples" / "candidate_01", ROOT / "configs" / "default.json"), indent=2, sort_keys=True)
    second = json.dumps(run_pipeline(ROOT / "samples" / "candidate_01", ROOT / "configs" / "default.json"), indent=2, sort_keys=True)
    assert first == second
