# Data

Local dataset payloads are not committed. The ignored `raw/`, `interim/`, and
`processed/` directories are runtime workspaces. Commit only small, non-sensitive
manifests, schemas, checksums, and deterministic split/config definitions needed
to reproduce results.

## Banking77 W1-001 contract

Authoritative mentor-provided source:
`https://github.com/PolyAI-LDN/task-specific-datasets/tree/master/banking_data`.
The locked revision, CC-BY-4.0 license reference, and expected SHA-256 checksums
are in `configs/data/banking77_w1_locked.json` and
`data/banking77_source_manifest.json`.

Acquire exactly `categories.json`, `train.csv`, and `test.csv` from the pinned
revision:

```powershell
py -3.11 scripts/data/banking77.py --root . --config configs/data/banking77_w1_locked.json acquire --refresh
```

Raw payloads go under the ignored revision-specific `data/raw/banking77/`
directory. No mirror, nested clone, or repackaged distribution is used. The
official `test.csv` is the frozen test set. Deterministic validation membership is
derived only from official `train.csv`; downstream tasks must verify and use
`data/banking77_split_manifest.json` unchanged.
