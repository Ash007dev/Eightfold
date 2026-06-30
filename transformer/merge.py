from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from transformer.cache import stable_hash
from transformer.config import AppConfig, DEFAULT_SOURCE_TRUST
from transformer.confidence import build_field_meta, confidence_for_skill, overall_confidence
from transformer.models import CanonicalRecord, Education, Experience, FieldMeta, Links, Location, Observation, ProvenanceEntry
from transformer.normalize import (
    clean_text,
    normalize_country,
    normalize_date,
    normalize_email,
    normalize_link,
    normalize_phone,
    normalize_skill,
    normalize_year,
)


SOURCE_ORDER = {"recruiter_csv": 0, "ats_json": 1, "resume": 2, "github": 3, "notes": 4}


@dataclass
class Bucket:
    id: int
    observations: list[Observation] = field(default_factory=list)
    emails: set[str] = field(default_factory=set)
    phones: set[str] = field(default_factory=set)
    names: set[str] = field(default_factory=set)
    links: set[str] = field(default_factory=set)
    companies: set[str] = field(default_factory=set)


class DSU:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        lroot = self.find(left)
        rroot = self.find(right)
        if lroot != rroot:
            self.parent[max(lroot, rroot)] = min(lroot, rroot)


def _trust(config: AppConfig, field: str, source: str, method: str = "") -> int:
    table = config.source_trust or DEFAULT_SOURCE_TRUST
    if field == "skills" and source == "github" and method == "github_authored":
        return 8
    if field == "skills" and source == "github" and method == "github_filesignal":
        return 6
    return table.get(field, table["default"]).get(source, 0)


def _field_root(field_name: str) -> str:
    return field_name.split(".", 1)[0]


def _normalize_observation(obs: Observation, config: AppConfig) -> tuple[str, Any] | None:
    field_name = obs.field
    root = _field_root(field_name)
    value = obs.value
    if root == "emails":
        normalized = normalize_email(value)
    elif root == "phones":
        normalized = normalize_phone(value, config.default_region)
    elif root == "skills":
        normalized = normalize_skill(value)
    elif field_name == "location.country":
        normalized = normalize_country(value)
    elif field_name.startswith("links."):
        normalized = normalize_link(value)
    elif field_name in {"experience.start", "experience.end"}:
        normalized = normalize_date(value)
    elif field_name == "education.end_year":
        normalized = normalize_year(value)
    else:
        normalized = clean_text(value)
    if normalized is None:
        return None
    return field_name, normalized


def _bucketize(observations: list[Observation], config: AppConfig) -> list[Bucket]:
    grouped: dict[str, list[Observation]] = defaultdict(list)
    for index, obs in enumerate(observations):
        grouped[obs.candidate_hint or f"obs:{index}"].append(obs)

    buckets: list[Bucket] = []
    for index, rows in enumerate(grouped.values()):
        bucket = Bucket(id=index, observations=rows)
        for obs in rows:
            normalized = _normalize_observation(obs, config)
            if not normalized:
                continue
            field_name, value = normalized
            if field_name == "emails":
                bucket.emails.add(value)
            elif field_name == "phones":
                bucket.phones.add(value)
            elif field_name == "full_name":
                bucket.names.add(str(value).casefold())
            elif field_name.startswith("links."):
                bucket.links.add(value)
            elif field_name == "experience.company":
                bucket.companies.add(str(value).casefold())
        buckets.append(bucket)
    return buckets


def _identity_groups(buckets: list[Bucket]) -> list[list[Bucket]]:
    dsu = DSU(len(buckets))
    for left in range(len(buckets)):
        for right in range(left + 1, len(buckets)):
            a = buckets[left]
            b = buckets[right]
            if a.emails & b.emails:
                dsu.union(left, right)
            elif a.phones & b.phones:
                dsu.union(left, right)
            elif a.names & b.names and ((a.links & b.links) or (a.companies & b.companies)):
                dsu.union(left, right)
    strong_roots = {
        dsu.find(index)
        for index, bucket in enumerate(buckets)
        if bucket.emails or bucket.phones or bucket.links or bucket.companies
    }
    if len(strong_roots) == 1:
        strong_root = next(iter(strong_roots))
        for index, bucket in enumerate(buckets):
            if not bucket.emails and not bucket.phones and not bucket.names and not bucket.links and not bucket.companies:
                dsu.union(strong_root, index)
    groups: dict[int, list[Bucket]] = defaultdict(list)
    for index, bucket in enumerate(buckets):
        groups[dsu.find(index)].append(bucket)
    return [groups[key] for key in sorted(groups)]


def _match_key(group: list[Bucket]) -> str:
    emails = sorted(set().union(*(bucket.emails for bucket in group)))
    if emails:
        return f"email:{emails[0]}"
    phones = sorted(set().union(*(bucket.phones for bucket in group)))
    if phones:
        return f"phone:{phones[0]}"
    names = sorted(set().union(*(bucket.names for bucket in group)))
    links = sorted(set().union(*(bucket.links for bucket in group)))
    companies = sorted(set().union(*(bucket.companies for bucket in group)))
    if names and (links or companies):
        return f"name+corroboration:{names[0]}:{(links or companies)[0]}"
    return f"isolated:{stable_hash('|'.join(str(bucket.id) for bucket in group))[:12]}"


def _add_provenance(provenance: list[ProvenanceEntry], field_name: str, obs: Observation, value: Any, selected: bool = True) -> None:
    provenance.append(
        ProvenanceEntry(
            field=_field_root(field_name),
            source=obs.source,
            method=obs.method,
            value=value,
            selected=selected,
            confidence_signals=obs.confidence_signals,
        )
    )


def _best_scalar(items: list[tuple[str, Any, Observation]], config: AppConfig) -> tuple[Any | None, list[ProvenanceEntry]]:
    if not items:
        return None, []
    ranked = sorted(
        items,
        key=lambda item: (
            -_trust(config, _field_root(item[0]), item[2].source, item[2].method),
            SOURCE_ORDER.get(item[2].source, 99),
            str(item[1]).casefold(),
        ),
    )
    winner = ranked[0]
    rows: list[ProvenanceEntry] = []
    for field_name, value, obs in ranked:
        rows.append(
            ProvenanceEntry(
                field=_field_root(field_name),
                source=obs.source,
                method=obs.method,
                value=value,
                selected=value == winner[1],
                confidence_signals=obs.confidence_signals,
            )
        )
    return winner[1], rows


def _rank_array(field_name: str, items: list[tuple[Any, Observation]], config: AppConfig) -> list[Any]:
    best: dict[Any, tuple[int, int, str]] = {}
    for value, obs in items:
        rank = (
            _trust(config, field_name, obs.source, obs.method),
            -SOURCE_ORDER.get(obs.source, 99),
            str(value).casefold(),
        )
        if value not in best or rank > best[value]:
            best[value] = rank
    return sorted(best, key=lambda value: (-best[value][0], -best[value][1], best[value][2]))


def _experience_from_values(values: dict[str, list[tuple[str, Any, Observation]]], config: AppConfig, provenance: list[ProvenanceEntry]) -> list[Experience]:
    company, company_prov = _best_scalar(values.get("experience.company", []), config)
    title, title_prov = _best_scalar(values.get("experience.title", []), config)
    start, start_prov = _best_scalar(values.get("experience.start", []), config)
    end, end_prov = _best_scalar(values.get("experience.end", []), config)
    summary, summary_prov = _best_scalar(values.get("experience.summary", []), config)
    provenance.extend(company_prov + title_prov + start_prov + end_prov + summary_prov)
    if any([company, title, start, end, summary]):
        return [Experience(company=company, title=title, start=start, end=end, summary=summary)]
    return []


def _education_from_values(values: dict[str, list[tuple[str, Any, Observation]]], config: AppConfig, provenance: list[ProvenanceEntry]) -> list[Education]:
    institution, p1 = _best_scalar(values.get("education.institution", []), config)
    degree, p2 = _best_scalar(values.get("education.degree", []), config)
    field_value, p3 = _best_scalar(values.get("education.field", []), config)
    end_year, p4 = _best_scalar(values.get("education.end_year", []), config)
    provenance.extend(p1 + p2 + p3 + p4)
    if any([institution, degree, field_value, end_year]):
        return [Education(institution=institution, degree=degree, field=field_value, end_year=end_year)]
    return []


def merge_observations(observations: list[Observation], config: AppConfig) -> list[CanonicalRecord]:
    buckets = _bucketize(observations, config)
    records: list[CanonicalRecord] = []
    for group in _identity_groups(buckets):
        values: dict[str, list[tuple[str, Any, Observation]]] = defaultdict(list)
        array_values: dict[str, list[tuple[Any, Observation]]] = defaultdict(list)
        provenance: list[ProvenanceEntry] = []
        for bucket in group:
            for obs in bucket.observations:
                normalized = _normalize_observation(obs, config)
                if not normalized:
                    continue
                field_name, value = normalized
                root = _field_root(field_name)
                if root in {"emails", "phones", "skills"}:
                    array_values[root].append((value, obs))
                    _add_provenance(provenance, field_name, obs, value)
                else:
                    values[field_name].append((field_name, value, obs))

        full_name, name_prov = _best_scalar(values.get("full_name", []), config)
        provenance.extend(name_prov)
        location = Location(
            city=_best_scalar(values.get("location.city", []), config)[0],
            region=_best_scalar(values.get("location.region", []), config)[0],
            country=_best_scalar(values.get("location.country", []), config)[0],
        )
        for key in ("location.city", "location.region", "location.country"):
            provenance.extend(_best_scalar(values.get(key, []), config)[1])
        links = Links(
            linkedin=_best_scalar(values.get("links.linkedin", []), config)[0],
            github=_best_scalar(values.get("links.github", []), config)[0],
            leetcode=_best_scalar(values.get("links.leetcode", []), config)[0],
            orcid=_best_scalar(values.get("links.orcid", []), config)[0],
            portfolio=_best_scalar(values.get("links.portfolio", []), config)[0],
            other=_rank_array("links", [(item[1], item[2]) for item in values.get("links.other", [])], config),
        )
        for key in ("links.linkedin", "links.github", "links.leetcode", "links.orcid", "links.portfolio", "links.other"):
            provenance.extend(_best_scalar(values.get(key, []), config)[1])
        headline, headline_prov = _best_scalar(values.get("headline", []), config)
        years_experience, years_prov = _best_scalar(values.get("years_experience", []), config)
        provenance.extend(headline_prov + years_prov)
        experience = _experience_from_values(values, config, provenance)
        education = _education_from_values(values, config, provenance)

        emails = _rank_array("emails", array_values["emails"], config)
        phones = _rank_array("phones", array_values["phones"], config)
        skill_names = _rank_array("skills", array_values["skills"], config)
        skills = [confidence_for_skill(skill, provenance) for skill in skill_names]
        skills.sort(key=lambda item: (-item.confidence, item.name.casefold()))

        field_meta: dict[str, FieldMeta] = {
            field_name: build_field_meta(field_name, provenance)
            for field_name in [
                "full_name",
                "emails",
                "phones",
                "location",
                "links",
                "headline",
                "years_experience",
                "skills",
                "experience",
                "education",
            ]
        }
        key = _match_key(group)
        candidate_id = f"cand_{stable_hash(key)[:12]}"
        record = CanonicalRecord(
            candidate_id=candidate_id,
            match_key=key,
            full_name=full_name,
            emails=emails,
            phones=phones,
            location=location,
            links=links,
            headline=headline,
            years_experience=float(years_experience) if isinstance(years_experience, (int, float)) else None,
            skills=skills,
            experience=experience,
            education=education,
            provenance=sorted(
                provenance,
                key=lambda row: (row.field, row.source, row.method, str(row.value), not row.selected),
            ),
            field_meta=field_meta,
        )
        record.overall_confidence = overall_confidence(field_meta, skills)
        records.append(record)
    return sorted(records, key=lambda record: record.candidate_id)
