"""Shared, standard-library helpers for PayResolve reporting automation."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path


WEEK_RANGE = range(0, 6)
WEEK_SUBDIRECTORIES = ("daily", "experiments", "results", "exports")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO date {value!r}; expected YYYY-MM-DD") from exc


def week_path(root: Path, week: int) -> Path:
    if week not in WEEK_RANGE:
        raise ValueError("Week must be between 0 (bootstrap) and 5")
    return root / "reports" / f"week_{week:02d}"


def git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def markdown_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("*.md") if path.is_file())


def render_week_markdown(root: Path, week: int) -> str:
    week_dir = week_path(root, week)
    summary = week_dir / f"week_{week:02d}_summary.md"
    if not summary.is_file():
        raise FileNotFoundError(f"Missing weekly summary: {summary}")

    sources: list[Path] = [summary]
    sources.extend(markdown_files(week_dir / "daily"))
    sources.extend(markdown_files(week_dir / "experiments"))
    sources.extend(markdown_files(week_dir / "results"))

    header = (
        f"<!-- GENERATED FILE: edit canonical sources, not this aggregate. -->\n"
        f"<!-- Built: {date.today().isoformat()} | Source commit: {git_commit(root)} -->\n\n"
        f"# PayResolve AI — Week {week:02d} Report\n\n"
        "## Included canonical sources\n\n"
    )
    source_list = "".join(
        f"- `{path.relative_to(root).as_posix()}`\n" for path in sources
    )
    sections = []
    for path in sources:
        relative = path.relative_to(root).as_posix()
        content = path.read_text(encoding="utf-8").strip()
        sections.append(f"\n---\n\n<!-- Source: {relative} -->\n\n{content}\n")
    return header + source_list + "".join(sections)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}"),
    "openai-key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "aws-access-key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "slack-token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
}

