# W3-003-EV3-EH1-FIX4 — Canonical runtime-fingerprint file binding

## Scope and hypothesis

P0 pre-consumption integrity repair only. The FIX3 receipt could claim any
64-character digest because neither harness nor evaluator resolved and hashed
the canonical environment-fingerprint file. The hypothesis is that binding the
receipt and raw-manifest claims to one package-declared file, then validating
the file's package/runtime identities and zero-activity counters, closes this
gap before any authorization, consumption, raw execution, Gold access, or
scoring.

## Controlled change

- Added `paths.runtime_environment_fingerprint` only to the derived FIX4
  package; it contains a future path, not a future artifact hash.
- Harness now resolves that path under the execution root, hashes it against
  the receipt claim, validates its package/candidate/source/runtime identity,
  and requires all six activity counters to be zero.
- Evaluator repeats this file binding against both receipt and raw-manifest
  claims inside `verify_raw_before_gold`, before `score_frozen` can open Gold.
- Metric, response, safety, causal, mapping, product-gate, and scorer logic
  remain unchanged.

## Results

The original FIX3 defect reproduced: the actual FIX3 harness accepted the
canonical JIT2 receipt and also accepted a receipt where only its fingerprint
digest changed to another valid hex value; a matching temporary evaluator
fixture also accepted it. FIX4 structural fixtures pass without opening Gold.
All 20 required negative controls reject, including digest/file tampering,
package and identity drift, activity counters, and evaluator raw/receipt claim
drift. `py_compile` passes. AST comparison against preserved FIX3 snapshots
finds all unaffected functions AST-identical; `score_frozen` is unchanged.

## Boundary and next step

No model was loaded. No canonical FIX4 fingerprint or receipt was created.
No authorization, consumption, E1, raw output, Gold access, score, stage,
commit, or push occurred. JIT2-FIX3 remains valid load-only evidence but is
superseded for execution. Senior review must approve FIX4 before a separately
authorized fresh FIX4 runtime re-attestation and new E1 authorization.
