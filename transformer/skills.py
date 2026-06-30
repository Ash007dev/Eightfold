from __future__ import annotations

import re


_ACRONYMS = {
    "API",
    "AWS",
    "CSS",
    "CI/CD",
    "GCP",
    "HTML",
    "JSON",
    "PHP",
    "SQL",
    "XML",
    "YAML",
}

_ALIASES: dict[str, str] = {
    "api": "API",
    "aws": "AWS",
    "css": "CSS",
    "gcp": "GCP",
    "html": "HTML",
    "json": "JSON",
    "php": "PHP",
    "sql": "SQL",
    "xml": "XML",
    "yaml": "YAML",
    "yml": "YAML",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "graphql": "GraphQL",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "objective c": "Objective-C",
    "objective-c": "Objective-C",
    "jupyter notebook": "Jupyter Notebook",
    "shell": "Shell",
    "bash": "Shell",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "dart": "Dart",
    "scala": "Scala",
    "hcl": "Terraform (HCL)",
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
    original = raw.strip()
    key = _key(raw)
    if not key or key in {"n/a", "na", "none", "null", "see resume", "-"}:
        return None, False
    if key in _ALIASES:
        return _ALIASES[key], True
    if original.upper() in _ACRONYMS:
        return original.upper(), True
    if original.isupper() or "+" in original or "#" in original:
        return original, False
    return " ".join(part.capitalize() for part in key.split()), False
