from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTING_DIR = REPO_ROOT / "scripts" / "reporting"
sys.path.insert(0, str(REPORTING_DIR))

from build_week_report import export_with_pandoc, write_markdown  # noqa: E402
from new_daily_report import create_daily_report  # noqa: E402
from reporting_common import parse_iso_date, render_week_markdown  # noqa: E402
from validate_project_docs import validate_repository  # noqa: E402


class DailyReportTests(unittest.TestCase):
    def test_parse_iso_date_rejects_non_iso_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected YYYY-MM-DD"):
            parse_iso_date("23/07/2026")

    def test_create_daily_report_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template_dir = root / "reports" / "_templates"
            daily_dir = root / "reports" / "week_00" / "daily"
            template_dir.mkdir(parents=True)
            daily_dir.mkdir(parents=True)
            (template_dir / "DAILY_REPORT_TEMPLATE.md").write_text(
                "# Daily Report — YYYY-MM-DD\n", encoding="utf-8"
            )

            target = create_daily_report(root, 0, date(2026, 7, 23))
            self.assertEqual("# Daily Report — 2026-07-23\n", target.read_text(encoding="utf-8"))
            with self.assertRaises(FileExistsError):
                create_daily_report(root, 0, date(2026, 7, 23))
            self.assertEqual("# Daily Report — 2026-07-23\n", target.read_text(encoding="utf-8"))


class WeekReportTests(unittest.TestCase):
    def prepare_week(self, root: Path) -> Path:
        week = root / "reports" / "week_00"
        for directory in ("daily", "experiments", "results", "exports"):
            (week / directory).mkdir(parents=True, exist_ok=True)
        (week / "week_00_summary.md").write_text("# Summary\n", encoding="utf-8")
        (week / "daily" / "2026-07-23.md").write_text("# Daily\n", encoding="utf-8")
        return week

    def test_render_week_markdown_combines_canonical_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_week(root)
            output = render_week_markdown(root, 0)
            self.assertIn("reports/week_00/week_00_summary.md", output)
            self.assertIn("reports/week_00/daily/2026-07-23.md", output)
            self.assertIn("# Summary", output)
            self.assertIn("# Daily", output)

    def test_week_markdown_requires_force_to_replace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_week(root)
            target = write_markdown(root, 0)
            original = target.read_text(encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_markdown(root, 0)
            self.assertEqual(original, target.read_text(encoding="utf-8"))
            self.assertEqual(target, write_markdown(root, 0, force=True))

    def test_converter_output_is_created_on_destination_volume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            week = self.prepare_week(root)

            def fake_pandoc(command: list[str], **_: object) -> object:
                output = Path(command[-1])
                self.assertEqual(week / "exports", output.parent)
                output.write_bytes(b"fake-docx")
                return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

            with patch("build_week_report.shutil.which", return_value="pandoc"), patch(
                "build_week_report.render_week_markdown", return_value="# Report\n"
            ), patch("build_week_report.subprocess.run", side_effect=fake_pandoc):
                target = export_with_pandoc(root, 0, "docx")

            self.assertEqual(week / "exports" / "week_00_report.docx", target)
            self.assertEqual(b"fake-docx", target.read_bytes())


class RepositoryContractTests(unittest.TestCase):
    def test_repository_contract(self) -> None:
        issues = validate_repository(REPO_ROOT)
        self.assertEqual([], issues, "\n".join(f"{i.code}: {i.message}" for i in issues))


if __name__ == "__main__":
    unittest.main()
