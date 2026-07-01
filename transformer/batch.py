from __future__ import annotations

import logging
import time
from pathlib import Path

from transformer.__main__ import run_pipeline

logger = logging.getLogger(__name__)


def run_batch(root: Path, projection_config_path: Path | None) -> tuple[list[dict], dict]:
    """Run the existing single-candidate pipeline once per candidate subfolder."""
    candidate_dirs = sorted(path for path in root.iterdir() if path.is_dir())
    profiles: list[dict] = []
    start = time.perf_counter()
    for directory in candidate_dirs:
        try:
            profiles.extend(run_pipeline(directory, projection_config_path))
        except Exception as exc:
            logger.warning("batch candidate skipped (%s): %s", directory, exc)
    elapsed = time.perf_counter() - start
    stats = {
        "candidates": len(candidate_dirs),
        "profiles": len(profiles),
        "seconds": round(elapsed, 3),
        "per_candidate_ms": round(1000 * elapsed / max(1, len(candidate_dirs)), 2),
    }
    return profiles, stats
