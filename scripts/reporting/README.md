# Reporting Automation

The reporting CLIs are standard-library Python scripts and may be run from the
repository root:

```bash
python scripts/reporting/new_daily_report.py --week 1 --date YYYY-MM-DD
python scripts/reporting/validate_project_docs.py
python scripts/reporting/build_week_report.py --week 1 --format md
python scripts/reporting/build_week_report.py --week 1 --format pdf
python scripts/reporting/build_week_report.py --week 1 --format docx
```

Use `--force` only to intentionally rebuild a generated weekly output. Daily
creation never overwrites. `validate_project_docs.py` checks required structure,
the detailed Week 1 task contract, completed-task daily evidence, protected Git
paths, ignore rules, competing PRD filenames, and high-confidence secret patterns.

Markdown remains canonical. Pandoc is optional: DOCX/PDF export fails clearly when
the converter (or a PDF engine) is unavailable. Generated outputs go to
`reports/week_XX/exports/` and are never committed automatically.
