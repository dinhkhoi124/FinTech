"""Generate reader-friendly documents from the authoritative MASTER_PRD.md.

The generated files are navigation copies only. ``docs/MASTER_PRD.md`` remains
the sole source of truth and must be edited directly before regenerating copies.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


SECTION_RE = re.compile(r"^# (?P<number>\d+)\. ", re.MULTILINE)

DOCUMENTS: tuple[tuple[str, str, tuple[int, ...]], ...] = (
    (
        "Brief.md",
        "Business Brief & Research Direction",
        (0, 1, 2),
    ),
    (
        "PRD.md",
        "Scope, Principles & Product Requirements",
        (3, 4, 7, 12),
    ),
    (
        "Data_Strategy.md",
        "Data Strategy",
        (5,),
    ),
    (
        "Evaluation_Plan.md",
        "Evaluation Plan & Failure Taxonomy",
        (6, 11),
    ),
    (
        "System_Architecture.md",
        "System Architecture & Technology Strategy",
        (8, 9),
    ),
    (
        "Internship_Plan.md",
        "5-Week AI Engineering Workflow",
        (10,),
    ),
    (
        "Delivery_and_Success.md",
        "Demo, Deliverables & Definition of Success",
        (13, 14, 15, 16, 17, 19),
    ),
    (
        "References.md",
        "References",
        (18,),
    ),
)


def parse_master(text: str) -> tuple[str, dict[int, str]]:
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        raise ValueError("No numbered sections found in MASTER_PRD.md")

    preamble = text[: matches[0].start()].rstrip() + "\n"
    sections: dict[int, str] = {}
    for index, match in enumerate(matches):
        number = int(match.group("number"))
        if number in sections:
            raise ValueError(f"Duplicate section number in master: {number}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[number] = text[match.start() : end].rstrip() + "\n"
    return preamble, sections


def generated_notice(title: str, section_numbers: tuple[int, ...]) -> str:
    section_list = ", ".join(str(number) for number in section_numbers)
    return (
        f"# {title}\n\n"
        "> **Bản tách phục vụ đọc.** Nguồn chuẩn duy nhất là "
        "[`docs/MASTER_PRD.md`](../docs/MASTER_PRD.md). "
        "Không chỉnh sửa yêu cầu trực tiếp trong file này; hãy sửa master rồi "
        "chạy lại script sinh tài liệu.\n\n"
        f"> Nội dung nguyên văn từ các section: {section_list}.\n\n"
        "---\n\n"
    )


def render_documents(master_path: Path, output_dir: Path) -> dict[str, str]:
    text = master_path.read_text(encoding="utf-8")
    preamble, sections = parse_master(text)
    expected = set(range(20))
    if set(sections) != expected:
        missing = sorted(expected - set(sections))
        extra = sorted(set(sections) - expected)
        raise ValueError(f"Unexpected master sections; missing={missing}, extra={extra}")

    assigned = [number for _, _, numbers in DOCUMENTS for number in numbers]
    if len(assigned) != len(set(assigned)):
        raise ValueError("A numbered section is assigned to more than one output")
    if set(assigned) != expected:
        missing = sorted(expected - set(assigned))
        extra = sorted(set(assigned) - expected)
        raise ValueError(f"Invalid output mapping; missing={missing}, extra={extra}")

    rendered: dict[str, str] = {}
    for filename, title, numbers in DOCUMENTS:
        body_parts = [generated_notice(title, numbers)]
        if 0 in numbers:
            body_parts.extend((preamble, "\n"))
        for number in numbers:
            body_parts.extend((sections[number], "\n"))
        rendered[filename] = "".join(body_parts).rstrip() + "\n"

    return rendered


def render_readme(master_path: Path) -> str:
    rows = []
    for filename, title, numbers in DOCUMENTS:
        section_list = ", ".join(str(number) for number in numbers)
        rows.append(f"| [`{filename}`]({filename}) | {title} | {section_list} |")
    table = "\n".join(rows)
    return f"""# Tài liệu đọc riêng — PayResolve AI

Thư mục này chia nội dung của [`docs/MASTER_PRD.md`](../{master_path.as_posix()})
thành các tài liệu ngắn hơn để dễ đọc.

> **Quy tắc nguồn chuẩn:** `docs/MASTER_PRD.md` vẫn là tài liệu authoritative duy
> nhất. Các file ở đây là bản sinh tự động phục vụ đọc, không thay thế master và
> không nên được chỉnh sửa độc lập.

## Mục lục

| File | Nội dung | Section trong master |
|---|---|---:|
{table}

## Cập nhật bản đọc

Chạy từ thư mục gốc repository:

```powershell
py -3.11 scripts/reporting/split_master_prd.py --root .
```

Kiểm tra mà không ghi file:

```powershell
py -3.11 scripts/reporting/split_master_prd.py --root . --check
```
"""


def generate(root: Path, check: bool) -> int:
    master_path = Path("docs/MASTER_PRD.md")
    absolute_master = root / master_path
    output_dir = root / "tai_lieu"
    expected_files = render_documents(absolute_master, output_dir)
    expected_files["README.md"] = render_readme(master_path)

    if check:
        errors: list[str] = []
        for filename, expected in expected_files.items():
            path = output_dir / filename
            if not path.exists():
                errors.append(f"missing: {path.relative_to(root)}")
                continue
            actual = path.read_text(encoding="utf-8")
            if actual != expected:
                errors.append(f"stale or modified: {path.relative_to(root)}")

        if output_dir.exists():
            actual_names = {path.name for path in output_dir.glob("*.md")}
            extra_names = sorted(actual_names - set(expected_files))
            errors.extend(f"unexpected Markdown file: tai_lieu/{name}" for name in extra_names)

        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print("PASS: tai_lieu contains complete, current reader copies of sections 0-19")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in expected_files.items():
        (output_dir / filename).write_text(content, encoding="utf-8", newline="\n")
    print(f"Generated {len(expected_files)} Markdown files in {output_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return generate(args.root.resolve(), args.check)


if __name__ == "__main__":
    raise SystemExit(main())
