"""Build a weekly Markdown aggregate and optionally export it with Pandoc."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from reporting_common import render_week_markdown, repository_root, week_path


def write_markdown(root: Path, week: int, *, force: bool = False) -> Path:
    exports = week_path(root, week) / "exports"
    if not exports.is_dir():
        raise FileNotFoundError(f"Missing exports directory: {exports}")
    target = exports / f"week_{week:02d}_report.md"
    if target.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite generated report without --force: {target}")
    target.write_text(render_week_markdown(root, week), encoding="utf-8", newline="\n")
    return target


def export_with_pandoc(root: Path, week: int, output_format: str, *, force: bool = False) -> Path:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise RuntimeError(
            f"Pandoc is unavailable; cannot export {output_format.upper()}. "
            "Markdown remains canonical."
        )

    exports = week_path(root, week) / "exports"
    if not exports.is_dir():
        raise FileNotFoundError(f"Missing exports directory: {exports}")
    target = exports / f"week_{week:02d}_report.{output_format}"
    if target.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite generated export without --force: {target}")

    markdown = render_week_markdown(root, week)
    source_handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    )
    # Keep the converter output on the destination volume so the final atomic
    # replace also works when the system temp directory is on another drive.
    output_handle = tempfile.NamedTemporaryFile(
        suffix=f".{output_format}", delete=False, dir=exports
    )
    source_path = Path(source_handle.name)
    output_path = Path(output_handle.name)
    output_handle.close()
    try:
        source_handle.write(markdown)
        source_handle.close()
        result = subprocess.run(
            [pandoc, str(source_path), "--standalone", "--output", str(output_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise RuntimeError(
                f"Pandoc {output_format.upper()} export failed: {detail}. "
                "Markdown remains canonical."
            )
        os.replace(output_path, target)
    finally:
        source_handle.close()
        source_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--format", choices=("md", "pdf", "docx"), default="md")
    parser.add_argument("--force", action="store_true", help="Replace an existing generated output")
    parser.add_argument(
        "--check-converters",
        action="store_true",
        help="Report converter availability without generating a file",
    )
    args = parser.parse_args()

    if args.check_converters:
        pandoc = shutil.which("pandoc")
        print(f"pandoc: {pandoc or 'NOT FOUND'}")
        print("DOCX: supported when Pandoc is available")
        print("PDF: attempted through Pandoc; a PDF engine must also be installed")
        return 0 if pandoc else 1

    root = repository_root()
    try:
        if args.format == "md":
            target = write_markdown(root, args.week, force=args.force)
        else:
            target = export_with_pandoc(root, args.week, args.format, force=args.force)
    except (FileExistsError, FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
