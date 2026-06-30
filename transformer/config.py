from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class AppConfig:
    llm_provider: str = "OpenAI"
    llm_model: str = ""
    llm_model_cheap: str = ""
    llm_temperature: float = 0.0
    default_region: str = "IN"
    max_repos: int = 30
    max_files_to_read: int = 10
    recency_days: int = 365
    recency_as_of: str = ""
    github_token: str = ""
    leetcode_enabled: bool = True
    cache_path: str = "./.cache/responses.db"
    source_trust: dict[str, dict[str, int]] | None = None


DEFAULT_SOURCE_TRUST: dict[str, dict[str, int]] = {
    "emails": {"recruiter_csv": 5, "ats_json": 5, "resume": 3, "notes": 1, "github": 1},
    "phones": {"recruiter_csv": 5, "ats_json": 5, "resume": 3, "notes": 1, "github": 0},
    "location": {"recruiter_csv": 5, "ats_json": 5, "resume": 3, "notes": 1, "github": 1},
    "skills": {"github": 6, "resume": 5, "ats_json": 4, "leetcode": 3, "notes": 2, "recruiter_csv": 1},
    "experience": {"resume": 5, "ats_json": 4, "notes": 2, "recruiter_csv": 3, "github": 1},
    "education": {"resume": 5, "ats_json": 3, "notes": 2, "recruiter_csv": 0, "github": 0},
    "default": {"recruiter_csv": 5, "ats_json": 5, "resume": 3, "notes": 2, "github": 1, "leetcode": 0},
}


def load_app_config(env_path: str | Path = ".env", config_path: str | Path | None = None) -> AppConfig:
    _load_dotenv(Path(env_path))
    extra: dict[str, Any] = {}
    if config_path:
        path = Path(config_path)
        if path.exists():
            extra = json.loads(path.read_text(encoding="utf-8"))

    trust = extra.get("source_trust") or DEFAULT_SOURCE_TRUST
    return AppConfig(
        llm_provider=os.getenv("LLM_PROVIDER", extra.get("LLM_PROVIDER", "OpenAI")),
        llm_model=os.getenv("LLM_MODEL", extra.get("LLM_MODEL", "")),
        llm_model_cheap=os.getenv("LLM_MODEL_CHEAP", extra.get("LLM_MODEL_CHEAP", "")),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", extra.get("LLM_TEMPERATURE", 0))),
        default_region=os.getenv("DEFAULT_REGION", extra.get("DEFAULT_REGION", "IN")),
        max_repos=int(os.getenv("MAX_REPOS", extra.get("MAX_REPOS", 30))),
        max_files_to_read=int(os.getenv("MAX_FILES_TO_READ", extra.get("MAX_FILES_TO_READ", 10))),
        recency_days=int(os.getenv("RECENCY_DAYS", extra.get("RECENCY_DAYS", 365))),
        recency_as_of=os.getenv("RECENCY_AS_OF", extra.get("RECENCY_AS_OF", "")),
        github_token=os.getenv("GITHUB_TOKEN", extra.get("GITHUB_TOKEN", "")),
        leetcode_enabled=os.getenv("LEETCODE_ENABLED", str(extra.get("LEETCODE_ENABLED", "true"))).lower() == "true",
        cache_path=os.getenv("CACHE_PATH", extra.get("CACHE_PATH", "./.cache/responses.db")),
        source_trust=trust,
    )


def load_projection_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else Path("configs/default.json")
    return json.loads(config_path.read_text(encoding="utf-8"))
