from __future__ import annotations

from pathlib import Path

from transformer.config import AppConfig
from transformer.evidence.leetcode import extract_file
from transformer.models import Observation


def extract(path: Path, config: AppConfig) -> list[Observation]:
    return extract_file(path, config)
