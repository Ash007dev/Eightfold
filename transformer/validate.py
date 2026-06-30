from __future__ import annotations

from typing import Any


MISSING = object()


class ProjectionValidationError(ValueError):
    pass


def validate_value(value: Any, expected_type: str, required: bool, path: str) -> None:
    if value is MISSING:
        if required:
            raise ProjectionValidationError(f"required field {path} is missing")
        return
    if value is None:
        return
    if expected_type == "string":
        valid = isinstance(value, str)
    elif expected_type == "string[]":
        valid = isinstance(value, list) and all(isinstance(item, str) for item in value)
    elif expected_type == "number":
        valid = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif expected_type == "object":
        valid = isinstance(value, (dict, list))
    else:
        raise ProjectionValidationError(f"unknown type {expected_type} for {path}")
    if not valid:
        raise ProjectionValidationError(f"field {path} expected {expected_type}, got {type(value).__name__}")
