from __future__ import annotations

import json
import logging
import re
import base64
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import requests

from transformer.config import AppConfig
from transformer.cache import SQLiteCache, stable_hash
from transformer.evidence.file_signals import FILE_SIGNALS, OWNERSHIP_FILES
from transformer.models import Observation
from transformer.normalize import clean_text, normalize_link, normalize_skill

logger = logging.getLogger(__name__)

PROFILE_RE = re.compile(r"https?://(?:www\.)?github\.com/([A-Za-z0-9-]+)")
URL_RE = re.compile(r"https?://[^\s)>\"]+")
LINK_CLASSIFIERS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"https?://(?:www\.)?leetcode\.com/(?:u/)?([A-Za-z0-9_-]+)/?", re.IGNORECASE), "links.leetcode"),
    (re.compile(r"https?://(?:www\.)?linkedin\.com/in/([^/\s]+)/?", re.IGNORECASE), "links.linkedin"),
    (re.compile(r"https?://(?:www\.)?orcid\.org/([0-9Xx-]+)/?", re.IGNORECASE), "links.orcid"),
]

def _login_from_text(text: str) -> str | None:
    match = PROFILE_RE.search(text)
    return match.group(1) if match else None


def _headers(config: AppConfig) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json, application/vnd.github.mercy-preview+json", "X-GitHub-Api-Version": "2022-11-28"}
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


def _parse_github_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).astimezone(timezone.utc)
    except ValueError:
        return None


def _recency_as_of(repos: list[dict[str, Any]], config: AppConfig) -> datetime | None:
    configured = _parse_github_datetime(config.recency_as_of)
    if configured:
        return configured
    pushed_dates = [_parse_github_datetime(repo.get("pushed_at")) for repo in repos]
    valid = [item for item in pushed_dates if item is not None]
    return max(valid) if valid else None


def _is_recent(repo: dict[str, Any], as_of: datetime | None, days: int) -> bool:
    pushed = _parse_github_datetime(repo.get("pushed_at"))
    if not pushed or not as_of:
        return False
    return pushed >= as_of - timedelta(days=max(0, days))


def _repo_topics(owner: str, repo: str, repo_data: dict[str, Any], config: AppConfig, cache: SQLiteCache) -> list[str]:
    topics = repo_data.get("topics")
    if isinstance(topics, list):
        return sorted(str(topic) for topic in topics if str(topic).strip())
    data = _get_json(f"https://api.github.com/repos/{owner}/{repo}/topics", config, cache)
    if isinstance(data, dict) and isinstance(data.get("names"), list):
        return sorted(str(topic) for topic in data["names"] if str(topic).strip())
    return []


def _tree_paths(owner: str, repo: str, branch: str, config: AppConfig, cache: SQLiteCache) -> list[str]:
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    data = _get_json(url, config, cache)
    if not isinstance(data, dict) or not isinstance(data.get("tree"), list):
        return []
    return sorted(item["path"] for item in data["tree"] if isinstance(item, dict) and isinstance(item.get("path"), str))


def _pattern_matches(path: str, pattern: str) -> bool:
    return fnmatch(path, pattern) or fnmatch(path.lower(), pattern.lower())


def _file_signal_skills(paths: list[str]) -> list[tuple[str, str]]:
    skills: dict[str, str] = {}
    for path in paths:
        normalized_path = path.replace("\\", "/")
        for pattern, skill, tier in FILE_SIGNALS:
            if _pattern_matches(normalized_path, pattern):
                canonical = normalize_skill(skill)
                if canonical:
                    existing = skills.get(canonical)
                    if existing is None or existing == "tooling":
                        skills[canonical] = tier
    return sorted(skills.items(), key=lambda item: (item[0].casefold(), item[1]))


def _content_text(owner: str, repo: str, path: str, config: AppConfig, cache: SQLiteCache) -> str:
    encoded_path = "/".join(part for part in path.split("/") if part)
    data = _get_json(f"https://api.github.com/repos/{owner}/{repo}/contents/{encoded_path}", config, cache)
    if not isinstance(data, dict):
        return ""
    content = data.get("content")
    if not isinstance(content, str):
        return ""
    try:
        return base64.b64decode(content).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _identity_confirmed(paths: list[str], owner: str, repo: str, login: str, config: AppConfig, cache: SQLiteCache) -> bool:
    needles = {login.casefold()}
    for path in paths:
        filename = path.rsplit("/", 1)[-1]
        if filename not in OWNERSHIP_FILES:
            continue
        content = _content_text(owner, repo, path, config, cache).casefold()
        if any(needle in content for needle in needles):
            return True
    return False


def _classify_link(url: str, portfolio_seen: bool) -> tuple[str, str | None, bool]:
    for pattern, field in LINK_CLASSIFIERS:
        match = pattern.match(url)
        if match:
            return field, match.group(1), portfolio_seen
    if not portfolio_seen:
        return "links.portfolio", None, True
    return "links.other", None, portfolio_seen


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
        leetcode_usernames: set[str] = set()
        portfolio_seen = any(row.field == "links.portfolio" for row in observations)
        for url in sorted(set(URL_RE.findall(bio))):
            link = normalize_link(url)
            if link:
                field, username, portfolio_seen = _classify_link(link, portfolio_seen)
                if field == "links.leetcode" and username:
                    leetcode_usernames.add(username)
                observations.append(Observation(field=field, value=link, source="github", method="regex", candidate_hint=hint))

        repos = _get_json(f"https://api.github.com/users/{login}/repos?per_page=100", config, cache)
        if not isinstance(repos, list):
            return observations
        authored_repos: list[tuple[dict[str, Any], str, str]] = []
        for repo in sorted(repos[: config.max_repos], key=lambda item: str(item.get("full_name", ""))):
            if not isinstance(repo, dict):
                continue
            owner = repo.get("owner", {}).get("login") if isinstance(repo.get("owner"), dict) else login
            repo_name = repo.get("name")
            if not owner or not repo_name:
                continue
            if _authored_commit_count(owner, repo_name, login, config, cache) <= 0:
                continue
            authored_repos.append((repo, owner, repo_name))
        as_of = _recency_as_of([repo for repo, _, _ in authored_repos], config)
        total_stars = sum(int(repo.get("stargazers_count") or 0) for repo, _, _ in authored_repos)
        for repo, owner, repo_name in authored_repos:
            branch = repo.get("default_branch") or "main"
            paths = _tree_paths(owner, repo_name, branch, config, cache)
            identity_confirmed = _identity_confirmed(paths, owner, repo_name, login, config, cache)
            base_signals = {
                "identity_confirmed": identity_confirmed,
                "recent": _is_recent(repo, as_of, config.recency_days),
                "stars": total_stars,
            }
            languages = _get_json(f"https://api.github.com/repos/{owner}/{repo_name}/languages", config, cache)
            if isinstance(languages, dict):
                for language in sorted(languages):
                    skill = normalize_skill(language)
                    if skill:
                        observations.append(
                            Observation(
                                field="skills",
                                value=skill,
                                source="github",
                                method="github_authored",
                                candidate_hint=hint,
                                confidence_signals=base_signals,
                            )
                        )
            for topic in _repo_topics(owner, repo_name, repo, config, cache):
                skill = normalize_skill(topic)
                if skill:
                    observations.append(
                        Observation(
                            field="skills",
                            value=skill,
                            source="github",
                            method="github_topic",
                            candidate_hint=hint,
                            confidence_signals=base_signals,
                        )
                    )
            for skill, tier in _file_signal_skills(paths):
                observations.append(
                    Observation(
                        field="skills",
                        value=skill,
                        source="github",
                        method="github_filesignal",
                        candidate_hint=hint,
                        confidence_signals={**base_signals, "tier": tier},
                    )
                )
        return observations
    except Exception as exc:
        logger.warning("failed to parse github source %s: %s", path, exc)
        return []
