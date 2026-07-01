"""Batch output must be byte-identical across repeated runs."""

import json
from pathlib import Path

from transformer.batch import run_batch


ROOT = Path(__file__).resolve().parents[1]


def test_batch10_is_byte_identical_twice() -> None:
    first, _ = run_batch(ROOT / "samples" / "batch10", ROOT / "configs" / "default.json")
    second, _ = run_batch(ROOT / "samples" / "batch10", ROOT / "configs" / "default.json")
    assert json.dumps(first, indent=2, sort_keys=True) == json.dumps(second, indent=2, sort_keys=True)
