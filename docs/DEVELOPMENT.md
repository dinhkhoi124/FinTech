# Reproducible Developer Workflow

Run commands from the repository root. The Phase 0 reporting tools use only the
Python standard library; ML dependencies are intentionally not selected until the
corresponding Week 1 task records and verifies them.

## Environment setup

Supported Week 1 runtime: **CPython 3.11.x**. This narrow constraint is deliberate:
the semantic/model dependency set has not been verified on Python 3.13/3.14. The
constraint can be widened only after a recorded compatibility test.

PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
```

Bash-compatible shell:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
```

The expected version output is `Python 3.11.x`. Do not commit `.venv/`. Before Week 1 execution,
`W1-001` must record the exact interpreter, data adapter, package versions, data
source/version, and checksums used. Do not reuse the current local environment as
evidence unless its dependencies are explicitly captured and verified.

The current bootstrap `.venv` uses Python 3.14.3 and is retained only to preserve
local state during review. It is **not supported for Week 1 ML work**. After the
bootstrap commit/review, recreate it without deleting the current environment
upfront:

```powershell
deactivate  # only if a virtual environment is active
Rename-Item -LiteralPath .venv -NewName .venv.bootstrap-3.14
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
```

The backup name is ignored by `.gitignore`. Remove it later only after the Python
3.11 environment and Week 1 dependency lock have been verified; this review does
not move or delete the existing environment.

## Stable Phase 0 commands

```powershell
python -m unittest discover -s tests -v
python scripts/reporting/validate_project_docs.py
python scripts/reporting/new_daily_report.py --week 0 --date YYYY-MM-DD
python scripts/reporting/build_week_report.py --week 0 --format md
python scripts/reporting/build_week_report.py --week 0 --format docx
python scripts/reporting/build_week_report.py --week 0 --format pdf
python scripts/reporting/build_week_report.py --week 0 --format md --force
```

Daily report creation refuses to overwrite an existing date. Weekly outputs are
generated under `reports/week_XX/exports/`; rebuilding an existing output requires
`--force`. DOCX/PDF commands require Pandoc, and PDF additionally requires a
working PDF engine. Conversion failure is explicit and does not change the fact
that Markdown is canonical.

## Quality checks

Phase 0 has no required third-party linter/type-checker. If `ruff` or `mypy` is
used locally, record its version and exact command; its presence is not claimed as
a reproducible project dependency until pinned.

The required bootstrap gate is:

```powershell
python -m unittest discover -s tests -v
python scripts/reporting/validate_project_docs.py
```

## Experiments and evaluation

No Week 1 experiment entry point exists yet by design. Each Week 1 task must add a
CLI/script with explicit config, seed, input version, output path, and a command
that runs outside a notebook. Locked tests are never used for tuning.

Planned stable command families (implemented and finalized only in Week 1):

```text
python -m payresolve_ai.<data_audit_command> --config configs/<locked-config>
python -m payresolve_ai.<train_command> --config configs/<baseline-config>
python -m payresolve_ai.<evaluate_command> --config configs/<eval-config>
```

These placeholders document the interface contract, not completed functionality.
The exact module names must be recorded in `TASKS.md`, the daily report, and the
relevant experiment note when implemented.

## Future service launch

The service is a Week 4 P0 deliverable. No service command is claimed during
bootstrap; document and test it only when `W4-001` is active.
