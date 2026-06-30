from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from transformer.models import FieldMeta, ProvenanceEntry, Skill


WEAK_FREE_TEXT = {"notes"}
WEAK_METHODS = {"github_topic"}
SKILL_FILE_SIGNAL_TIERS = {"infra", "cicd", "db_api", "framework"}


def _is_tooling_only_signal(row: ProvenanceEntry) -> bool:
    return row.method == "github_filesignal" and row.confidence_signals.get("tier") == "tooling"


def _has_signal(entries: list[ProvenanceEntry], key: str, truthy: bool = True) -> bool:
    if truthy:
        return any(bool(row.confidence_signals.get(key)) for row in entries)
    return any(key in row.confidence_signals for row in entries)


def score_from_provenance(entries: Iterable[ProvenanceEntry], coerced: bool = False) -> tuple[float, dict[str, Any]]:
    rows = list(entries)
    if not rows:
        return 0.0, {"base": 0}
    rows_for_score = [row for row in rows if not _is_tooling_only_signal(row)]
    if not rows_for_score:
        return 0.0, {"tooling_only": 0}

    sources = {row.source for row in rows_for_score}
    methods = {row.method for row in rows_for_score}
    score: float = 3
    breakdown: dict[str, Any] = {"base": 3}
    if len(sources) >= 2:
        score += 2
        breakdown["multi_source"] = 2
    if "github_authored" in methods:
        score += 3
        breakdown["github_authored"] = 3
    leetcode_cross_confirmed = "leetcode_solved" in methods and any(row.source != "leetcode" for row in rows_for_score)
    if leetcode_cross_confirmed:
        score += 2
        breakdown["leetcode_cross_confirm"] = 2
    if any(
        row.method == "github_filesignal" and row.confidence_signals.get("tier") in SKILL_FILE_SIGNAL_TIERS
        for row in rows_for_score
    ):
        score += 1
        breakdown["github_filesignal"] = 1
    if _has_signal(rows_for_score, "identity_confirmed"):
        score += 1
        breakdown["identity_confirmed"] = 1
    if _has_signal(rows_for_score, "recent"):
        score += 0.5
        breakdown["recent"] = 0.5
    if any((row.confidence_signals.get("stars") or 0) > 0 for row in rows_for_score):
        score += 0.25
        breakdown["stars"] = 0.25
    weak_only = all(row.source in WEAK_FREE_TEXT or row.method in WEAK_METHODS or row.source == "leetcode" for row in rows_for_score)
    if weak_only and len(sources) == 1:
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
        weight = 2.0 if ("github" in skill.sources or "leetcode" in skill.sources) else 1.0
        weighted.append((skill.confidence, weight))
    if not weighted:
        return 0.0
    numerator = sum(score * weight for score, weight in weighted)
    denominator = sum(weight for _, weight in weighted)
    return round(numerator / denominator, 3)
