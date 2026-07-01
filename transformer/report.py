from __future__ import annotations

from transformer.confidence import score_from_provenance
from transformer.models import CanonicalRecord


def _source_method(entries: list) -> str:
    pairs = sorted({f"{entry.source} ({entry.method})" for entry in entries})
    return ", ".join(pairs) if pairs else "no provenance"


def render_report(records: list[CanonicalRecord]) -> str:
    lines: list[str] = []
    for record in records:
        name = record.full_name or record.candidate_id
        lines.append(f"{name}   (overall_confidence {record.overall_confidence})")

        phone_entries = [entry for entry in record.provenance if entry.field == "phones"]
        if record.phones:
            phones = []
            for phone in record.phones:
                entries = [entry for entry in phone_entries if entry.value == phone]
                phones.append(f"{phone} <- {_source_method(entries)}")
            lines.append(f"  phones: {', '.join(phones)}")

        if record.skills:
            lines.append("  skills:")
            for skill in record.skills:
                entries = [entry for entry in record.provenance if entry.field == "skills" and entry.value == skill.name]
                methods = sorted({entry.method for entry in entries})
                sources = sorted({entry.source for entry in entries})
                _, breakdown = score_from_provenance(entries)
                lines.append(
                    f"    {skill.name}  {skill.confidence:.2f}  sources={sources} methods={methods} breakdown={breakdown}"
                )
        lines.append("")
    return "\n".join(lines).rstrip()
