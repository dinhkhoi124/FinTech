# W3-003-EV2-E1-INC1-R1 — Raw-manifest provenance incident

## Incident

After the Senior-authorized one-shot E1 command, the Codex execution cell
completed without persisted stdout/stderr, exit code, or traceback. A separate
structural check then reported
`MISSING:w3_003_ev2_e1_raw_manifest.json`, so the consumed execution was stopped
for Senior adjudication. A later preflight observed the manifest present.

## Scope and safety boundary

This investigation was P0 integrity work. It did not retry, rerun, or resume E1;
call the model/retriever; load Gold, Pass B, or Pass C; score R1; or alter any
live E1 artifact. The receipt, raw output, and raw manifest remained untracked
and byte-immutable.

## Evidence

- Receipt: 861 bytes, SHA `169e47629d614c4bc0df0ccbeaab4a859814f1ca767d6eec563faad5d0a022d0`.
- Raw output: 218,133 bytes, SHA `d7c9a16fb4867f52ded6b793ccda227b3a9c0210eca44c17869d1cab4a60d263`.
- Raw manifest: 11,129 bytes, SHA `5be5e1e4535f60413c56867ba4f4b4fb11e5b95190d28b609acf3a2cafe5d413`, matching the Senior copy.
- Raw structure: 60 physical/valid object rows, 60 unique IDs, zero duplicates, malformed rows, or trailing partial row.
- Integrity: raw SHA exact, receipt SHA exact, 60/60 row hashes, and 60/60 for case-ID, query-hash, and raw-query-ID order.
- Manifest: exact V2 20/20 fields, no extras, all frozen bindings exact, reconstruction deep-equal and byte-equal.
- Timeline: the manifest was created 26.0462 ms after the final raw write, the exact normal control-flow location after a successful 60-row loop.

## Root-cause boundary

The prior failure assertion was produced by the separate structural check, not
by a captured E1 exception. A genuine canonical manifest strongly contradicts
an E1 failure before completion because the frozen harness has no normal step
after atomic manifest emission except returning. The false missing observation
cannot be explained further because the check implementation/timestamp and E1
process exit code were not persisted.

## Disposition

Manifest provenance: `A_CONSISTENT_WITH_ORIGINAL_E1`, accepted by Senior.

Final classification: `CLASS_A_CANONICAL_COMPLETE_E1_ARTIFACT_SET`.

Final Senior-adjudicated execution state: `E1_RAW_CANONICAL_COMPLETE`.

R1 remains not executed until separate explicit authorization. Retry and resume
remain permanently false. The E1 process exit code is unknown/not persisted;
canonical completion is established by the frozen byte-level postconditions.
