from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from transformer.config import AppConfig
from transformer.llm import LLMClient
from transformer.models import Observation
from transformer.normalize import clean_text, normalize_skill

logger = logging.getLogger(__name__)


def _prompt(text: str) -> str:
    return (
        "Extract explicitly stated recruiter-note signals as JSON with keys skills "
        "and seniority_hint. Return only JSON. Do not infer missing values.\n\n"
        f"NOTES:\n{text}"
    )


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else ([] if value in (None, "") else [value])


def extract(path: Path, config: AppConfig) -> list[Observation]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            return []
        text = text[: max(1, config.max_files_to_read) * 2000]
        data = json.loads(LLMClient(config).complete(_prompt(text)))
        hint = str(path)
        observations: list[Observation] = []
        for skill in _as_list(data.get("skills")):
            value = normalize_skill(skill)
            if value:
                observations.append(
                    Observation(field="skills", value=value, source="notes", method="llm_extraction", candidate_hint=hint)
                )
        seniority = clean_text(data.get("seniority_hint"))
        if seniority:
            observations.append(
                Observation(field="headline", value=seniority, source="notes", method="llm_extraction", candidate_hint=hint)
            )
        return observations
    except Exception as exc:
        logger.warning("failed to parse notes %s: %s", path, exc)
        return []
