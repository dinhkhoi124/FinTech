# W3-003-EV3-E1-TOPOLOGY-CORR1 — module invocation and one-shot authorization 0003

## Scope

Authorization 0002 is preserved unchanged and closed before consumption because the direct script command could not import the repository `scripts` package. This correction changes only invocation topology: E1 and the scorer run with `python -m` under one new authorization.

## Pre-consumption evidence

The safe module import probe passed with zero model, query, or Gold calls. Fresh remote/HEAD/tree, all frozen source/package/runtime identities, the complete Gold package by SHA-256 only, and final `validate_pre_inference` all passed. Authorization 0003 bound the unchanged FIX4 package, harness, evaluator, input, canonical fingerprint, and runtime receipt.

## One-shot result

The single module-mode harness consumed EV3 and emitted a complete 60-row raw manifest. Raw-before-Gold validation passed. The single official module-mode scorer emitted `INVALID`: overall safe resolution 0.18333333333333332, wrong abstention 15, zero-tolerance total 52, and evaluator integrity `FAIL`.

## Terminal state

`EV3_INVALID_READY_FOR_SENIOR_INTEGRITY_ADJUDICATION`. There was no retry, re-score, EV4, staging, commit, or push.
