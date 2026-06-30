from __future__ import annotations

from pathlib import Path


def detect_source(path: str | Path) -> str | None:
    p = Path(path)
    name = p.name.lower()
    suffix = p.suffix.lower()
    if suffix == ".csv":
        return "recruiter_csv"
    if suffix == ".json":
        return "ats_json"
    if name in {"resume.txt", "resume.pdf", "resume.docx"} or suffix in {".pdf", ".docx"}:
        return "resume"
    if name.startswith("notes") and suffix == ".txt":
        return "notes"
    if name.startswith("github") and suffix == ".txt":
        return "github"
    if name.startswith("leetcode") and suffix == ".txt":
        return "leetcode"
    return None
