"""A LeetCode language cross-confirmed by another source should outrank a single-source skill."""

from transformer.confidence import confidence_for_skill
from transformer.models import ProvenanceEntry


def test_cross_confirmed_skill_outranks_resume_only_skill() -> None:
    provenance = [
        ProvenanceEntry(field="skills", source="resume", method="llm_extraction", value="Python"),
        ProvenanceEntry(
            field="skills",
            source="leetcode",
            method="leetcode_solved",
            value="Python",
            confidence_signals={"solved": 12},
        ),
        ProvenanceEntry(field="skills", source="resume", method="llm_extraction", value="JavaScript"),
    ]
    assert confidence_for_skill("Python", provenance).confidence > confidence_for_skill("JavaScript", provenance).confidence
