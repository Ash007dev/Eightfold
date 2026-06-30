from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests

from transformer.cache import SQLiteCache, stable_hash
from transformer.config import AppConfig
from transformer.models import Observation
from transformer.normalize import normalize_skill

logger = logging.getLogger(__name__)

LEETCODE_GRAPHQL = "https://leetcode.com/graphql"
LANGUAGE_QUERY = """
query userLanguages($username: String!) {
  matchedUser(username: $username) {
    languageProblemCount {
      languageName
      problemsSolved
    }
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
  }
}
"""


def _request_leetcode(username: str, config: AppConfig, cache: SQLiteCache) -> dict[str, Any] | None:
    key = stable_hash(f"leetcode|{username.casefold()}")
    cached = cache.get(key)
    if cached is not None:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            return None
    try:
        response = requests.post(
            LEETCODE_GRAPHQL,
            json={"query": LANGUAGE_QUERY, "variables": {"username": username}},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code in {403, 404, 429, 500, 502, 503, 504}:
            logger.warning("leetcode request failed for %s: status %s", username, response.status_code)
            return None
        response.raise_for_status()
        cache.set(key, response.text)
        return response.json()
    except Exception as exc:
        logger.warning("leetcode request failed for %s: %s", username, exc)
        return None


def extract_username(username: str, config: AppConfig, candidate_hint: str | None = None) -> list[Observation]:
    if not config.leetcode_enabled:
        return []
    username = username.strip().strip("/")
    if not username:
        return []
    try:
        cache = SQLiteCache(config.cache_path)
        data = _request_leetcode(username, config, cache)
        rows = (
            data.get("data", {})
            .get("matchedUser", {})
            .get("languageProblemCount", [])
            if isinstance(data, dict)
            else []
        )
        if not isinstance(rows, list):
            return []
        observations: list[Observation] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            solved = int(row.get("problemsSolved") or 0)
            if solved <= 0:
                continue
            skill = normalize_skill(row.get("languageName"))
            if not skill:
                continue
            observations.append(
                Observation(
                    field="skills",
                    value=skill,
                    source="leetcode",
                    method="leetcode_solved",
                    candidate_hint=candidate_hint or f"leetcode:{username}",
                    confidence_signals={"solved": solved},
                )
            )
        return observations
    except Exception as exc:
        logger.warning("leetcode extraction failed for %s: %s", username, exc)
        return []


def extract_file(path: Path, config: AppConfig) -> list[Observation]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            return []
        username = text.rstrip("/").split("/")[-1]
        return extract_username(username, config, candidate_hint=str(path))
    except Exception as exc:
        logger.warning("leetcode source failed for %s: %s", path, exc)
        return []
