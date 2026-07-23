"""Create a daily Markdown report from the canonical template, without overwrite."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from reporting_common import parse_iso_date, repository_root, week_path


def create_daily_report(root: Path, week: int, report_date: date) -> Path:
    template_path = root / "reports" / "_templates" / "DAILY_REPORT_TEMPLATE.md"
    if not template_path.is_file():
        raise FileNotFoundError(f"Missing template: {template_path}")

    daily_dir = week_path(root, week) / "daily"
    if not daily_dir.is_dir():
        raise FileNotFoundError(f"Missing week daily directory: {daily_dir}")

    target = daily_dir / f"{report_date.isoformat()}.md"
    content = template_path.read_text(encoding="utf-8").replace(
        "YYYY-MM-DD", report_date.isoformat()
    )
    with target.open("x", encoding="utf-8", newline="\n") as output:
        output.write(content)
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", type=int, required=True, help="0 for bootstrap, 1-5 for project weeks")
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="ISO date (YYYY-MM-DD); defaults to today",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        target = create_daily_report(
            repository_root(), args.week, parse_iso_date(args.date)
        )
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

