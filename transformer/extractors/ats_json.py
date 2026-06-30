from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from transformer.config import AppConfig
from transformer.models import Observation
from transformer.normalize import clean_text

logger = logging.getLogger(__name__)


FIELD_MAP = {
    "candidateName": "full_name",
    "emailAddress": "emails",
    "mobile": "phones",
    "currentEmployer": "experience.company",
    "jobTitle": "experience.title",
    "skillTags": "skills",
    "city": "location.city",
    "region": "location.region",
    "country": "location.country",
    "linkedinUrl": "links.linkedin",
    "githubUrl": "links.github",
    "portfolioUrl": "links.portfolio",
}


def _iter_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("candidates"), list):
            return [item for item in data["candidates"] if isinstance(item, dict)]
        return [data]
    return []


def _emit_value(field: str, value: Any, hint: str) -> list[Observation]:
    if isinstance(value, list):
        values = value
    else:
        values = [value]
    observations = []
    for item in values:
        cleaned = clean_text(item)
        if cleaned is None:
            continue
        observations.append(
            Observation(
                field=field,
                value=cleaned,
                source="ats_json",
                method="exact",
                candidate_hint=hint,
            )
        )
    return observations


def extract(path: Path, config: AppConfig) -> list[Observation]:
    del config
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        observations: list[Observation] = []
        for index, record in enumerate(_iter_records(data)):
            hint = f"{path}:{index}"
            for key, target in FIELD_MAP.items():
                if key in record:
                    observations.extend(_emit_value(target, record[key], hint))
        return observations
    except Exception as exc:
        logger.warning("failed to parse ats json %s: %s", path, exc)
        return []
