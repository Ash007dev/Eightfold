from __future__ import annotations

import re


_ALIASES: dict[str, str] = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "node": "JavaScript",
    "node.js": "JavaScript",
    "nodejs": "JavaScript",
    "py": "Python",
    "python": "Python",
    "gh actions": "GitHub Actions",
    "github action": "GitHub Actions",
    "github actions": "GitHub Actions",
    "actions": "GitHub Actions",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "dockerfile": "Docker",
    "docker compose": "Docker Compose",
    "compose": "Docker Compose",
    "terraform": "Terraform",
    "tf": "Terraform",
    "react": "React",
    "next": "Next.js",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "prisma": "Prisma",
    "fastapi": "FastAPI",
    "typescript": "TypeScript",
    "ts": "TypeScript",
}


def _key(raw: str) -> str:
    value = raw.strip().lower()
    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def canonicalize_skill(raw: str | None) -> tuple[str | None, bool]:
    if raw is None:
        return None, False
    key = _key(raw)
    if not key or key in {"n/a", "na", "none", "null", "see resume", "-"}:
        return None, False
    if key in _ALIASES:
        return _ALIASES[key], True
    return " ".join(part.capitalize() for part in key.split()), False
