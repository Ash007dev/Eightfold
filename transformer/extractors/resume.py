from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from transformer.config import AppConfig
from transformer.llm import LLMClient
from transformer.models import Observation
from transformer.normalize import (
    clean_text,
    normalize_date,
    normalize_email,
    normalize_phone,
    normalize_skill,
    normalize_year,
)

logger = logging.getLogger(__name__)


def _ocr_pdf_page(page: Any) -> str:
    try:
        import pytesseract

        image = page.to_image(resolution=200).original
        return pytesseract.image_to_string(image) or ""
    except Exception as exc:
        logger.warning("pdf OCR failed on page: %s", exc)
        return ""


def _read_pdf_text(path: Path) -> str:
    import pdfplumber

    chunks: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(text)
                continue
            ocr_text = _ocr_pdf_page(page)
            if ocr_text.strip():
                chunks.append(ocr_text)
    return "\n".join(chunks)


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".pdf":
        return _read_pdf_text(path)
    if path.suffix.lower() == ".docx":
        from docx import Document

        document = Document(path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    return ""


def _prompt(text: str) -> str:
    return (
        "Extract candidate data from this resume into JSON with keys: "
        "full_name, emails, phones, skills, experience, education, headline. "
        "experience items use company,title,start,end,summary. education items use "
        "institution,degree,field,end_year. Return only values explicitly present.\n\n"
        f"RESUME:\n{text}"
    )


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else ([] if value in (None, "") else [value])


def _emit(field: str, value: Any, hint: str) -> Observation:
    return Observation(field=field, value=value, source="resume", method="llm_extraction", candidate_hint=hint)


def extract(path: Path, config: AppConfig) -> list[Observation]:
    try:
        text = _read_text(path)
        if not text.strip():
            return []
        text = text[: max(1, config.max_files_to_read) * 4000]
        data = json.loads(LLMClient(config).complete(_prompt(text), tier="strong"))
        hint = str(path)
        observations: list[Observation] = []
        name = clean_text(data.get("full_name"))
        if name:
            observations.append(_emit("full_name", name, hint))
        headline = clean_text(data.get("headline"))
        if headline:
            observations.append(_emit("headline", headline, hint))
        for email in _as_list(data.get("emails")):
            value = normalize_email(email)
            if value:
                observations.append(_emit("emails", value, hint))
        for phone in _as_list(data.get("phones")):
            value = normalize_phone(phone, config.default_region)
            if value:
                observations.append(_emit("phones", value, hint))
        for skill in _as_list(data.get("skills")):
            value = normalize_skill(skill)
            if value:
                observations.append(_emit("skills", value, hint))
        for item in _as_list(data.get("experience")):
            if not isinstance(item, dict):
                continue
            for key in ("company", "title", "summary"):
                value = clean_text(item.get(key))
                if value:
                    observations.append(_emit(f"experience.{key}", value, hint))
            for key in ("start", "end"):
                value = normalize_date(item.get(key))
                if value:
                    observations.append(_emit(f"experience.{key}", value, hint))
        for item in _as_list(data.get("education")):
            if not isinstance(item, dict):
                continue
            for key in ("institution", "degree", "field"):
                value = clean_text(item.get(key))
                if value:
                    observations.append(_emit(f"education.{key}", value, hint))
            end_year = normalize_year(item.get("end_year"))
            if end_year:
                observations.append(_emit("education.end_year", end_year, hint))
        return observations
    except Exception as exc:
        logger.warning("failed to parse resume %s: %s", path, exc)
        return []
