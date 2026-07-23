"""Validate PayResolve repository, reporting, and public-safety invariants."""

from __future__ import annotations

import subprocess
from pathlib import Path

from reporting_common import (
    SECRET_PATTERNS,
    ValidationIssue,
    WEEK_RANGE,
    WEEK_SUBDIRECTORIES,
    repository_root,
    week_path,
)


REQUIRED_FILES = (
    "AGENTS.md",
    "CODEX_BOOTSTRAP_PROMPT.md",
    "PROJECT_STATE.md",
    "TASKS.md",
    "README.md",
    "pyproject.toml",
    "docs/PROJECT_CONTEXT.md",
    "docs/MASTER_PRD.md",
    "docs/ROADMAP.md",
    "docs/EXECUTION_RULES.md",
    "docs/REPORTING_POLICY.md",
    "docs/DEVELOPMENT.md",
    ".agents/skills/payresolve-task-lifecycle/SKILL.md",
    "reports/_templates/DAILY_REPORT_TEMPLATE.md",
    "reports/_templates/EXPERIMENT_NOTE_TEMPLATE.md",
    "reports/_templates/WEEKLY_SUMMARY_TEMPLATE.md",
    "reports/_templates/INCIDENT_POSTMORTEM_TEMPLATE.md",
    "reports/_templates/CHANGE_REQUEST_TEMPLATE.md",
    "scripts/reporting/new_daily_report.py",
    "scripts/reporting/build_week_report.py",
    "scripts/reporting/validate_project_docs.py",
)

REQUIRED_DIRECTORIES = (
    "src/payresolve_ai",
    "tests",
    "configs",
    "data/raw",
    "data/interim",
    "data/processed",
    "experiments",
    "artifacts",
)

REQUIRED_IGNORE_RULES = (
    "document/",
    "file_zip/",
    ".venv/",
    ".env",
    ".env.*",
    "secrets/",
    "credentials/",
    "artifacts/**",
)

FORBIDDEN_TRACKED_PREFIXES = ("document/", "file_zip/", ".venv/", "secrets/", "credentials/")
SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


def git_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return []
    return [root / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def tracked_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return []
    return [item.decode("utf-8").replace("\\", "/") for item in result.stdout.split(b"\0") if item]


def validate_repository(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            issues.append(ValidationIssue("missing-file", relative))
    for relative in REQUIRED_DIRECTORIES:
        if not (root / relative).is_dir():
            issues.append(ValidationIssue("missing-directory", relative))

    for week in WEEK_RANGE:
        directory = week_path(root, week)
        if not directory.is_dir():
            issues.append(ValidationIssue("missing-week", str(directory.relative_to(root))))
            continue
        for name in WEEK_SUBDIRECTORIES:
            child = directory / name
            if not child.is_dir():
                issues.append(ValidationIssue("missing-report-directory", str(child.relative_to(root))))
        for filename in ("README.md", f"week_{week:02d}_summary.md"):
            path = directory / filename
            if not path.is_file():
                issues.append(ValidationIssue("missing-week-file", str(path.relative_to(root))))

    ignore_path = root / ".gitignore"
    ignore_text = ignore_path.read_text(encoding="utf-8") if ignore_path.is_file() else ""
    for rule in REQUIRED_IGNORE_RULES:
        if rule not in ignore_text.splitlines():
            issues.append(ValidationIssue("missing-ignore-rule", rule))

    pyproject_path = root / "pyproject.toml"
    pyproject_text = pyproject_path.read_text(encoding="utf-8") if pyproject_path.is_file() else ""
    if 'requires-python = ">=3.11,<3.12"' not in pyproject_text:
        issues.append(
            ValidationIssue(
                "unsupported-python-strategy",
                "pyproject.toml must lock the reviewed Week 1 runtime to CPython 3.11.x",
            )
        )

    for path in tracked_paths(root):
        normalized = path.lower()
        if normalized.startswith(FORBIDDEN_TRACKED_PREFIXES):
            issues.append(ValidationIssue("unsafe-tracked-path", path))
        name = Path(normalized).name
        if name == ".env" or name.startswith(".env.") and name != ".env.example":
            issues.append(ValidationIssue("unsafe-tracked-secret", path))
        if normalized.endswith(SENSITIVE_SUFFIXES):
            issues.append(ValidationIssue("unsafe-tracked-secret", path))

    for path in git_paths(root):
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                issues.append(
                    ValidationIssue(label, str(path.relative_to(root)).replace("\\", "/"))
                )

    prd_files = [
        path for path in root.rglob("*PRD*.md")
        if ".git" not in path.parts and ".venv" not in path.parts
    ]
    expected_prd = root / "docs" / "MASTER_PRD.md"
    if set(prd_files) != {expected_prd}:
        paths = ", ".join(str(path.relative_to(root)) for path in prd_files) or "none"
        issues.append(ValidationIssue("competing-prd", paths))

    state_path = root / "PROJECT_STATE.md"
    if state_path.is_file() and "YYYY-MM-DD" in state_path.read_text(encoding="utf-8"):
        issues.append(ValidationIssue("state-placeholder", "PROJECT_STATE.md still has YYYY-MM-DD"))

    tasks_path = root / "TASKS.md"
    tasks_text = tasks_path.read_text(encoding="utf-8") if tasks_path.is_file() else ""
    for task_id in ("W1-001", "W1-002", "W1-003", "W1-004"):
        required_heading = f"### {task_id}"
        if required_heading not in tasks_text:
            issues.append(ValidationIssue("incomplete-week1-plan", required_heading))

    done_task_ids = []
    for line in tasks_text.splitlines():
        if line.startswith("|") and line.rstrip().endswith("| DONE |"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if cells:
                done_task_ids.append(cells[0])
    daily_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "reports").glob("week_*/daily/*.md")
    ) if (root / "reports").is_dir() else ""
    for task_id in done_task_ids:
        if task_id not in daily_text:
            issues.append(ValidationIssue("done-task-without-daily-evidence", task_id))

    return issues


def main() -> int:
    root = repository_root()
    issues = validate_repository(root)
    if issues:
        print(f"VALIDATION FAILED ({len(issues)} issue(s))")
        for issue in issues:
            print(f"- [{issue.code}] {issue.message}")
        return 1
    print("VALIDATION PASSED")
    print("Required project/report structure, Week 1 plan, and public-safety checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
