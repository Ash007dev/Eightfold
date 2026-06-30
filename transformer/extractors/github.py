from __future__ import annotations

import json
import logging
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import requests

from transformer.config import AppConfig
from transformer.cache import SQLiteCache, stable_hash
from transformer.models import Observation
from transformer.normalize import clean_text, normalize_link, normalize_skill

logger = logging.getLogger(__name__)

PROFILE_RE = re.compile(r"https?://(?:www\.)?github\.com/([A-Za-z0-9-]+)")
URL_RE = re.compile(r"https?://[^\s)>\"]+")

FILE_SIGNALS: list[tuple[str, str]] = [
    (".github/workflows/*.yml", "GitHub Actions"),
    (".github/workflows/*.yaml", "GitHub Actions"),
    (".gitlab-ci.yml", "CI/CD"),
    (".circleci/config.yml", "CI/CD"),
    ("Jenkinsfile", "CI/CD"),
    ("Dockerfile", "Docker"),
    ("Dockerfile.*", "Docker"),
    ("docker-compose.yml", "Docker Compose"),
    ("docker-compose.yaml", "Docker Compose"),
    ("compose.yml", "Docker Compose"),
    ("compose.yaml", "Docker Compose"),
    ("k8s/*.yaml", "Kubernetes"),
    ("manifests/*.yaml", "Kubernetes"),
    ("Chart.yaml", "Helm"),
    ("*.tf", "Terraform"),
    ("*.tfvars", "Terraform"),
    ("prisma/schema.prisma", "Prisma"),
    ("schema.graphql", "GraphQL"),
    ("openapi.yaml", "OpenAPI"),
    ("openapi.json", "OpenAPI"),
    ("*.proto", "gRPC"),
    ("next.config.js", "Next.js"),
    ("next.config.mjs", "Next.js"),
    ("next.config.ts", "Next.js"),
    ("vite.config.ts", "Vite"),
    ("vite.config.js", "Vite"),
]


def _login_from_text(text: str) -> str | None:
    match = PROFILE_RE.search(text)
    return match.group(1) if match else None


def _headers(config: AppConfig) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if config.github_token:
        headers["Authorization"] = f"Bearer {config.github_token}"
    return headers


def _get_json(url: str, config: AppConfig, cache: SQLiteCache) -> Any | None:
    key = stable_hash(url)
    cached = cache.get(key)
    if cached is not None:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            return None
    try:
        response = requests.get(url, headers=_headers(config), timeout=10)
        if response.status_code in {403, 404}:
            return None
        response.raise_for_status()
        text = response.text
        cache.set(key, text)
        return response.json()
    except Exception as exc:
        logger.warning("github request failed for %s: %s", url, exc)
        return None


def _authored_commit_count(owner: str, repo: str, login: str, config: AppConfig, cache: SQLiteCache) -> int:
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?author={login}&per_page=100"
    data = _get_json(url, config, cache)
    return len(data) if isinstance(data, list) else 0


def _tree_paths(owner: str, repo: str, branch: str, config: AppConfig, cache: SQLiteCache) -> list[str]:
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    data = _get_json(url, config, cache)
    if not isinstance(data, dict) or not isinstance(data.get("tree"), list):
        return []
    return sorted(item["path"] for item in data["tree"] if isinstance(item, dict) and isinstance(item.get("path"), str))


def _file_signal_skills(paths: list[str]) -> list[str]:
    skills: set[str] = set()
    for path in paths:
        normalized_path = path.replace("\\", "/")
        for pattern, skill in FILE_SIGNALS:
            if fnmatch(normalized_path, pattern):
                canonical = normalize_skill(skill)
                if canonical:
                    skills.add(canonical)
    return sorted(skills)


def extract(path: Path, config: AppConfig) -> list[Observation]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        login = _login_from_text(text)
        if not login:
            return []
        cache = SQLiteCache(config.cache_path)
        user = _get_json(f"https://api.github.com/users/{login}", config, cache)
        if not isinstance(user, dict):
            return []
        hint = str(path)
        observations: list[Observation] = [
            Observation(field="links.github", value=f"https://github.com/{login}", source="github", method="regex", candidate_hint=hint)
        ]
        name = clean_text(user.get("name"))
        if name:
            observations.append(Observation(field="full_name", value=name, source="github", method="exact", candidate_hint=hint))
        for key in ("blog", "html_url"):
            link = normalize_link(user.get(key))
            if link and "github.com" not in link:
                observations.append(Observation(field="links.portfolio", value=link, source="github", method="regex", candidate_hint=hint))
        bio = clean_text(user.get("bio")) or ""
        for url in sorted(set(URL_RE.findall(bio))):
            link = normalize_link(url)
            if link:
                observations.append(Observation(field="links.other", value=link, source="github", method="regex", candidate_hint=hint))

        repos = _get_json(f"https://api.github.com/users/{login}/repos?per_page=100", config, cache)
        if not isinstance(repos, list):
            return observations
        for repo in sorted(repos[: config.max_repos], key=lambda item: str(item.get("full_name", ""))):
            if not isinstance(repo, dict):
                continue
            owner = repo.get("owner", {}).get("login") if isinstance(repo.get("owner"), dict) else login
            repo_name = repo.get("name")
            if not owner or not repo_name:
                continue
            if _authored_commit_count(owner, repo_name, login, config, cache) <= 0:
                continue
            languages = _get_json(f"https://api.github.com/repos/{owner}/{repo_name}/languages", config, cache)
            if isinstance(languages, dict):
                for language in sorted(languages):
                    skill = normalize_skill(language)
                    if skill:
                        observations.append(
                            Observation(field="skills", value=skill, source="github", method="github_authored", candidate_hint=hint)
                        )
            branch = repo.get("default_branch") or "main"
            for skill in _file_signal_skills(_tree_paths(owner, repo_name, branch, config, cache)):
                observations.append(
                    Observation(field="skills", value=skill, source="github", method="github_filesignal", candidate_hint=hint)
                )
        return observations
    except Exception as exc:
        logger.warning("failed to parse github source %s: %s", path, exc)
        return []
