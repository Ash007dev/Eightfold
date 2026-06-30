from pathlib import Path

from transformer.__main__ import run_pipeline
from transformer.config import load_app_config
from transformer.extractors import extract_file
from transformer.merge import merge_observations
from transformer.project import resolve_path


ROOT = Path(__file__).resolve().parents[1]


def test_custom_projection_example() -> None:
    output = run_pipeline(ROOT / "samples" / "candidate_01", ROOT / "configs" / "custom_example.json")
    assert output == [
        {
            "_confidence": {
                "full_name": 0.5,
                "phone": 0.5,
                "primary_email": 0.5,
                "skills": 0.9,
            },
            "full_name": "Ananya Rao",
            "primary_email": "ananya.rao@example.com",
            "phone": "+919988776655",
            "skills": ["Python", "Kubernetes", "TypeScript", "JavaScript", "Docker", "GitHub Actions"],
        }
    ]


def test_path_resolver_array_projection() -> None:
    config = load_app_config()
    observations = []
    for path in sorted((ROOT / "samples" / "candidate_01").iterdir()):
        if path.suffix != ".gold.json":
            observations.extend(extract_file(path, config))
    record = merge_observations(observations, config)[0]
    assert resolve_path(record, "emails[0]") == "ananya.rao@example.com"
    assert resolve_path(record, "skills[].name")[:2] == ["Python", "Kubernetes"]
