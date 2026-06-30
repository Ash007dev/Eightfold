from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from transformer.models import CanonicalRecord
from transformer.normalize import normalize_email, normalize_phone, normalize_skill
from transformer.validate import MISSING, validate_value


TOKEN_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(\[(\d*|)\])?")


def _to_data(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_to_data(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_data(item) for key, item in value.items()}
    return value


def resolve_path(data: Any, path: str) -> Any:
    current = _to_data(data)
    tokens = path.split(".") if path else []
    for index, token in enumerate(tokens):
        match = TOKEN_RE.fullmatch(token)
        if not match:
            return MISSING
        key, bracket, array_index = match.group(1), match.group(2), match.group(3)
        if not isinstance(current, dict) or key not in current:
            return MISSING
        current = current[key]
        if bracket is None:
            continue
        if not isinstance(current, list):
            return MISSING
        if array_index == "":
            rest = ".".join(tokens[index + 1 :])
            if not rest:
                return current
            projected = [resolve_path(item, rest) for item in current]
            return [item for item in projected if item is not MISSING]
        try:
            selected = int(array_index)
        except ValueError:
            return MISSING
        if selected >= len(current):
            return MISSING
        current = current[selected]
    return current


def _assign_path(output: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = output
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _normalize_projection(value: Any, normalizer: str | None) -> Any:
    if value is MISSING or normalizer is None:
        return value
    if normalizer == "E164":
        return normalize_phone(value) if isinstance(value, str) else value
    if normalizer == "email":
        return normalize_email(value) if isinstance(value, str) else value
    if normalizer == "canonical":
        if isinstance(value, list):
            normalized = [normalize_skill(item) for item in value]
            seen: set[str] = set()
            ordered: list[str] = []
            for item in normalized:
                if item and item not in seen:
                    seen.add(item)
                    ordered.append(item)
            return ordered
        if isinstance(value, str):
            return normalize_skill(value)
    return value


def _field_confidence(record: CanonicalRecord, from_path: str) -> float:
    root = from_path.split(".", 1)[0].split("[", 1)[0]
    meta = record.field_meta.get(root)
    return meta.confidence if meta else 0.0


def project_record(record: CanonicalRecord, config: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    on_missing = config.get("on_missing", "null")
    confidence: dict[str, float] = {}
    for field_config in config.get("fields", []):
        out_path = field_config["path"]
        from_path = field_config.get("from", out_path)
        value = resolve_path(record, from_path)
        value = _normalize_projection(value, field_config.get("normalize"))
        required = bool(field_config.get("required", False))
        if value is MISSING:
            if required and on_missing == "error":
                validate_value(value, field_config["type"], required, out_path)
            if on_missing == "omit":
                continue
            value = None
        validate_value(value, field_config["type"], required, out_path)
        _assign_path(output, out_path, value)
        confidence[out_path] = _field_confidence(record, from_path)

    if config.get("include_confidence"):
        output["_confidence"] = {key: confidence[key] for key in sorted(confidence)}
    if config.get("include_provenance"):
        output["_provenance"] = [
            row.model_dump(exclude_none=True)
            for row in sorted(record.provenance, key=lambda item: (item.field, item.source, item.method, str(item.value)))
        ]
    return output


def project_records(records: list[CanonicalRecord], config: dict[str, Any]) -> list[dict[str, Any]]:
    return [project_record(record, config) for record in sorted(records, key=lambda item: item.candidate_id)]
