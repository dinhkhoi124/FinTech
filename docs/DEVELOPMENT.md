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

## W1-003 semantic experiment

Create an isolated Python 3.11 environment and install the fully pinned CPU stack:

```powershell
py -3.11 -m venv .venv-semantic
.\.venv-semantic\Scripts\python.exe -m pip install --upgrade pip==24.3.1
.\.venv-semantic\Scripts\python.exe -m pip install -r requirements/week1-semantic.txt
.\.venv-semantic\Scripts\python.exe -m pip install -e . --no-deps
```

Verify contracts, run the realistic smoke test, execute the one primary
configuration, and verify its local embedding cache:

```powershell
.\.venv-semantic\Scripts\python.exe scripts/baselines/semantic.py --root . --config configs/models/banking77_semantic_w1.json verify-contract
.\.venv-semantic\Scripts\python.exe scripts/baselines/semantic.py --root . --config configs/models/banking77_semantic_w1.json smoke
.\.venv-semantic\Scripts\python.exe scripts/baselines/semantic.py --root . --config configs/models/banking77_semantic_w1.json run --run-label primary --refresh-cache
.\.venv-semantic\Scripts\python.exe scripts/baselines/semantic.py --root . --config configs/models/banking77_semantic_w1.json verify-cache
.\.venv-semantic\Scripts\python.exe scripts/baselines/semantic.py --root . --config configs/models/banking77_semantic_w1.json inspect-errors --limit 20
```

An independent numerical rerun uses the same configuration and refreshes both
train and validation embeddings:

```powershell
.\.venv-semantic\Scripts\python.exe scripts/baselines/semantic.py --root . --config configs/models/banking77_semantic_w1.json run --run-label reproducibility_rerun --refresh-cache
```

The exact encoder revision and weights are cached only under ignored
`artifacts/cache/w1-003/`. Full embeddings and the fitted classifier parameters
also remain ignored. Trackable manifests contain revision, file checksums,
embedding shape/alignment checksums, runtime, predictions, metrics, and comparison
metadata. Neither `test.csv` nor a test embedding cache is used by this workflow.

## W1-004 final locked evaluation

W1-004 is complete. The following commands document the immutable evaluation
workflow; do not rerun `primary` or modify the frozen config after test access.

```powershell
.\.venv-semantic\Scripts\python.exe scripts/evaluation/week1_final.py --root . --config configs/evaluation/banking77_w1_final.json verify-pretest
.\.venv-semantic\Scripts\python.exe scripts/evaluation/week1_final.py --root . --config configs/evaluation/banking77_w1_final.json run --run-label primary
.\.venv-semantic\Scripts\python.exe scripts/evaluation/week1_final.py --root . --config configs/evaluation/banking77_w1_final.json run --run-label reproducibility_rerun
.\.venv-semantic\Scripts\python.exe scripts/evaluation/week1_final.py --root . --config configs/evaluation/banking77_w1_final.json finalize
.\.venv-semantic\Scripts\python.exe scripts/evaluation/week1_final.py --root . --config configs/evaluation/banking77_w1_final.json verify-results
```

The first four commands are historical execution commands retained for exact
reproduction/audit. Routine post-completion verification should run only
`verify-results`, unit tests, and the project validator. Final-fit scope is all
10,003 non-test rows for each frozen candidate; official test contains 3,080 rows.
Tracked evidence is under `reports/week_01/results/`. Test embeddings and fitted
models remain ignored under `artifacts/cache/w1-004/` and `artifacts/models/w1-004/`.

## Future service launch

The service is a Week 4 P0 deliverable. No service command is claimed during
bootstrap; document and test it only when `W4-001` is active.

## W2-001 controlled synthetic KB

W2-001 uses the standard-library validator and the fixed reference date in
`configs/kb/kb_v1.json`. It does not load the Banking77 official test, create
queries, build embeddings, or run retrieval.

```powershell
.\.venv-semantic\Scripts\python.exe scripts/kb/validate.py --root . --config configs/kb/kb_v1.json
.\.venv-semantic\Scripts\python.exe scripts/kb/validate.py --root . --config configs/kb/kb_v1.json --write-results
.\.venv-semantic\Scripts\python.exe -m unittest discover -s tests -p "test_kb_validation.py" -v
```

The first command is read-only. `--write-results` regenerates the validation
report, manifest, and coverage CSV under `reports/week_02/results/`. The
validation timestamp is run metadata and is excluded from the canonical dataset
SHA-256.

The implementation deliberately uses a complete standard-library custom
validator for the required document, lifecycle-plan, and hard-negative contracts;
it does not claim to execute the JSON Schema file. This avoids adding a Week 2
dependency for one bounded format, at the cost of keeping the schema artifact and
the custom checks synchronized. Focused mutation tests therefore cover field
types/lengths, enums and family/product consistency, exact lifecycle chains, and
the complete hard-negative relationship contract. The first-28 gate counts only
families and relationships that pass those structural checks.
