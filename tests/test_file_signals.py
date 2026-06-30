"""Repository config files are weak evidence tiers, with tooling kept at zero skill credit."""

from transformer.confidence import confidence_for_skill
from transformer.evidence.file_signals import FILE_SIGNALS
from transformer.extractors.github import _file_signal_skills
from transformer.models import ProvenanceEntry


def test_file_signal_taxonomy_has_expected_tiers() -> None:
    signals = dict(_file_signal_skills(["Dockerfile", "main.tf", ".github/workflows/ci.yml"]))
    assert signals["Docker"] == "infra"
    assert signals["Terraform"] == "infra"
    assert signals["GitHub Actions"] == "cicd"
    assert ("tsconfig.json", "TypeScript", "tooling") in FILE_SIGNALS


def test_tooling_only_file_signal_has_zero_skill_credit() -> None:
    skill = confidence_for_skill(
        "TypeScript",
        [
            ProvenanceEntry(
                field="skills",
                source="github",
                method="github_filesignal",
                value="TypeScript",
                confidence_signals={"tier": "tooling"},
            )
        ],
    )
    assert skill.confidence == 0.0
