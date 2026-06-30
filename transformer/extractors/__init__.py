from __future__ import annotations

from pathlib import Path
from typing import Callable

from transformer.config import AppConfig
from transformer.detect import detect_source
from transformer.models import Observation


Extractor = Callable[[Path, AppConfig], list[Observation]]


def _registry() -> dict[str, Extractor]:
    from transformer.extractors.ats_json import extract as ats_extract
    from transformer.extractors.csv_recruiter import extract as csv_extract
    from transformer.extractors.github import extract as github_extract
    from transformer.extractors.notes import extract as notes_extract
    from transformer.extractors.resume import extract as resume_extract

    return {
        "ats_json": ats_extract,
        "recruiter_csv": csv_extract,
        "resume": resume_extract,
        "notes": notes_extract,
        "github": github_extract,
    }


def extract_file(path: str | Path, config: AppConfig) -> list[Observation]:
    source_type = detect_source(path)
    if not source_type:
        return []
    extractor = _registry().get(source_type)
    if not extractor:
        return []
    return extractor(Path(path), config)
