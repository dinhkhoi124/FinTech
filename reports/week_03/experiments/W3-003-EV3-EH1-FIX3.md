# W3-003-EV3-EH1-FIX3 — Executable package/harness compatibility closure

## Scope

P0 pre-consumption compatibility repair only. EV3 execution, JIT, scoring, Gold
semantics, and production inference were forbidden and not invoked.

## Root cause and minimal repair

Historical harness SHA-256 `3383e364...359d9` accepted the FIX1 package
schema/status while the frozen evaluator and FIX2 package accepted FIX2. The
historical harness correctly failed with `EV3_PACKAGE_SCHEMA_INVALID` before
runtime validation. FIX3 changes only `PACKAGE_SCHEMA` and `PACKAGE_STATUS` in
the harness to their FIX2 values. Corrected harness SHA-256 is
`8a7d598a...da2ff`.

FIX3 package SHA-256 is `f78ad12f...24889`; it is a byte-derived copy of FIX2
with only `e1_harness_sha256` and `artifact_sha256.e1_harness` rebound.

## Verification

- Compatibility matrix: 10/10 PASS.
- Negative controls: 14/14 fail closed before consumption.
- `py_compile`: PASS.
- AST comparison: all 22 function bodies are identical; only the two approved
  constant values changed.
- Historical runtime receipt rejects FIX3 at package binding as expected.
- A temporary, non-canonical receipt structurally validates the FIX3 chain.

No model load, query encoding, ranking, Gold semantic access, production
inference, consumption, raw artifact, scorer, commit, or push occurred.

## Next

Senior byte review of FIX3 is required. If approved, authorize a fresh load-only
runtime re-attestation bound to the FIX3 package/harness, then issue a new E1
authorization. The prior E1 authorization is suspended and must not be used.
