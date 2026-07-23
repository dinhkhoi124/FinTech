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

## Week 1 data protocol

W1-001 uses only the mentor-provided PolyAI GitHub source at the exact commit and
checksums locked in `configs/data/banking77_w1_locked.json`:

```powershell
py -3.11 scripts/data/banking77.py --root . --config configs/data/banking77_w1_locked.json acquire --refresh
py -3.11 scripts/data/banking77.py --root . --config configs/data/banking77_w1_locked.json audit-lock
py -3.11 scripts/data/banking77.py --root . --config configs/data/banking77_w1_locked.json verify
```

`test.csv` remains the official frozen test set. Validation is a deterministic,
per-label 10% allocation from official train using seed `20260723` and a SHA-256
ordering rule. W1-002 and W1-003 must consume and verify the same locked manifest;
they must not resplit, tune on, or inspect test outcomes for model selection.

## W1-002 lexical experiment

Install only the pinned lexical stack into the Python 3.11 environment:

```powershell
py -3.11 -m pip install -r requirements/week1-lexical.txt
py -3.11 -m pip install -e . --no-deps
```

Run the controlled validation-only experiment and optional error inspection:

```powershell
py -3.11 scripts/data/banking77.py --root . --config configs/data/banking77_w1_locked.json verify
py -3.11 scripts/baselines/lexical.py --root . --config configs/models/banking77_lexical_w1.json
py -3.11 scripts/baselines/lexical.py --root . --config configs/models/banking77_lexical_w1.json --inspect-errors 20
```

The CLI reads only the official `train.csv` content, partitions it using the
locked train/validation membership, and asserts the source/protocol hashes. It
does not load or evaluate `test.csv`. The fitted portable parameter artifact is
local under ignored `artifacts/models/w1-002/`; trackable metrics, predictions,
per-class scores, confusions, and the version manifest are under
`reports/week_01/results/`. W1-003 and W1-004 must add their own reviewed entry
points; the frozen test remains untouched until W1-004.

## Future service launch

The service is a Week 4 P0 deliverable. No service command is claimed during
bootstrap; document and test it only when `W4-001` is active.
