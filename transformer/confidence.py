from __future__ import annotations

from collections.abc import Iterable

from transformer.models import FieldMeta, ProvenanceEntry, Skill


WEAK_FREE_TEXT = {"notes"}


def score_from_provenance(entries: Iterable[ProvenanceEntry], coerced: bool = False) -> tuple[float, dict[str, int]]:
    rows = list(entries)
    if not rows:
        return 0.0, {"base": 0}
    sources = {row.source for row in rows}
    methods = {row.method for row in rows}
    score = 3
    breakdown = {"base": 3}
    if len(sources) >= 2:
        score += 2
        breakdown["multi_source"] = 2
    if "github_authored" in methods:
        score += 3
        breakdown["github_authored"] = 3
    if "github_filesignal" in methods:
        score += 1
        breakdown["github_filesignal"] = 1
    if sources.issubset(WEAK_FREE_TEXT) and len(sources) == 1:
        score -= 1
        breakdown["weak_free_text"] = -1
    if coerced:
        score -= 1
        breakdown["coerced"] = -1
    score = max(0, min(10, score))
    return round(score / 10, 3), breakdown


def confidence_for_skill(skill: str, provenance: list[ProvenanceEntry]) -> Skill:
    entries = [row for row in provenance if row.field == "skills" and row.value == skill]
    confidence, _ = score_from_provenance(entries)
    sources = sorted({row.source for row in entries})
    return Skill(name=skill, confidence=confidence, sources=sources)


def build_field_meta(field: str, provenance: list[ProvenanceEntry]) -> FieldMeta:
    entries = [row for row in provenance if row.field == field or row.field.startswith(f"{field}.")]
    confidence, breakdown = score_from_provenance(entries)
    return FieldMeta(confidence=confidence, provenance=entries, score_breakdown=breakdown)


def overall_confidence(field_meta: dict[str, FieldMeta], skills: list[Skill]) -> float:
    weighted: list[tuple[float, float]] = []
    weights = {
        "emails": 2.0,
        "phones": 2.0,
        "full_name": 1.5,
        "location": 0.5,
        "experience": 1.5,
        "education": 1.0,
        "headline": 0.5,
    }
    for field, weight in weights.items():
        meta = field_meta.get(field)
        if meta and meta.confidence > 0:
            weighted.append((meta.confidence, weight))
    for skill in skills:
        weight = 2.0 if "github" in skill.sources else 1.0
        weighted.append((skill.confidence, weight))
    if not weighted:
        return 0.0
    numerator = sum(score * weight for score, weight in weighted)
    denominator = sum(weight for _, weight in weighted)
    return round(numerator / denominator, 3)
