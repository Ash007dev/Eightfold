from __future__ import annotations

import csv
import logging
from pathlib import Path

from transformer.config import AppConfig
from transformer.models import Observation
from transformer.normalize import clean_text

logger = logging.getLogger(__name__)


FIELD_MAP = {
    "name": "full_name",
    "email": "emails",
    "phone": "phones",
    "current_company": "experience.company",
    "title": "experience.title",
}


def extract(path: Path, config: AppConfig) -> list[Observation]:
    del config
    observations: list[Observation] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for index, row in enumerate(reader):
                hint = f"{path}:{index}"
                for source_field, target_field in FIELD_MAP.items():
                    value = clean_text(row.get(source_field))
                    if value is None:
                        continue
                    observations.append(
                        Observation(
                            field=target_field,
                            value=value,
                            source="recruiter_csv",
                            method="exact",
                            candidate_hint=hint,
                        )
                    )
    except Exception as exc:  # pragma: no cover - warning path covered via pipeline tests
        logger.warning("failed to parse recruiter csv %s: %s", path, exc)
        return []
    return observations
