"""Recent-activity scoring must use configured dates, not wall-clock time."""

from transformer.confidence import confidence_for_skill
from transformer.models import ProvenanceEntry


def test_recent_signal_scores_the_same_twice() -> None:
    provenance = [
        ProvenanceEntry(
            field="skills",
            source="github",
            method="github_authored",
            value="Python",
            confidence_signals={"recent": True, "stars": 12},
        )
    ]
    first = confidence_for_skill("Python", provenance).confidence
    second = confidence_for_skill("Python", provenance).confidence
    assert first == second
