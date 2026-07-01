from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from transformer.batch import run_batch


SKILLS = [
    ["Python", "SQL", "Docker"],
    ["Go", "Kubernetes", "Terraform"],
    ["JavaScript", "React", "CSS"],
    ["Java", "Spring Boot", "API"],
    ["Python", "Jupyter Notebook", "SQL"],
]


def _phone(index: int) -> str:
    return f"9{index % 10}{(10000000 + index):08d}"[:10]


def _write_candidate(root: Path, index: int) -> None:
    directory = root / f"cand_{index:04d}"
    directory.mkdir(parents=True, exist_ok=True)
    name = f"Candidate {index:04d}"
    email = f"candidate{index:04d}@example.com"
    phone = _phone(index)
    skills = SKILLS[index % len(SKILLS)]
    ats = {
        "candidateName": name,
        "emailAddress": email,
        "mobile": phone,
        "currentEmployer": f"Company {index % 25:02d} ATS",
        "jobTitle": f"Engineer {index % 7}",
        "skillTags": skills,
        "city": "Bengaluru",
        "region": "Karnataka",
        "country": "India",
    }
    directory.joinpath("ats.json").write_text(json.dumps(ats, sort_keys=True), encoding="utf-8")
    directory.joinpath("recruiter.csv").write_text(
        "name,email,phone,current_company,title\n"
        f"{name},{email},+91 {phone[:5]} {phone[5:]},Company {index % 25:02d} Recruiter,Senior Engineer {index % 7}\n",
        encoding="utf-8",
    )


def generate_dataset(root: Path, n: int) -> None:
    for index in range(1, n + 1):
        _write_candidate(root, index)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic structured-source scale benchmark")
    parser.add_argument("--n", type=int, default=1000, help="Number of synthetic candidate folders to generate")
    parser.add_argument("--config", type=Path, default=Path("configs/default.json"), help="Projection config path")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="eightfold_scale_") as tmp:
        root = Path(tmp)
        generate_dataset(root, args.n)
        first_profiles, first_stats = run_batch(root, args.config)
        second_profiles, second_stats = run_batch(root, args.config)
        first_json = json.dumps(first_profiles, indent=2, sort_keys=True)
        second_json = json.dumps(second_profiles, indent=2, sort_keys=True)
        if first_json != second_json:
            raise AssertionError("batch output was not deterministic")
        print(json.dumps(first_stats, sort_keys=True))
        print(json.dumps(second_stats, sort_keys=True))
        print("DETERMINISTIC: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
