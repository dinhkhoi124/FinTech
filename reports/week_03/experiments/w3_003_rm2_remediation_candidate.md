# W3-003-RM2 — publication closure candidate (PUB1)

## Current decision

Independent Senior review accepted the RCV2 implementation, the RPF1
reporting/evidence reconciliation, and the WF1 whitespace normalization. The
implementation publication commit
`cd97de602140e334ec499e8dfa27fa08ec1a6260` was pushed to `main` and
independently remote verified. RM2 remediation is **CLOSED**; no further RM2
semantic remediation is currently authorized.

This is not product-gate success. W3 P0 remains blocked. A separately authored,
frozen, reviewed, and authorized independent product evaluation is required
before the Week 3 gate can close; Week 4 remains blocked.

## Historical RCV1 context

The line v1 through FIX4 is rejected/preserved review history; FIX5 is not
approved for publication; SA1 is Senior reviewed with its scope amendment
authorized. RED1 is the historical remediation line. RCV1 is a historical
contamination-recovery predecessor only. It cleanly reverified RED1 after the
previous-session `VERIFICATION_BOUNDARY_BREACH / CONSUMED_HOLDOUT_READ`, but
Senior found the retained executable legacy multi-membership helper insufficiently
fail-closed. The consumed result remains invalid and unused. No authoritative
incident timestamp or complete prior command log exists; the post-access audit
therefore records its limitation rather than claiming impossible proof.

## RCV2 production identity

| File | Bytes | SHA-256 |
|---|---:|---|
| `routing_v3.py` | 29,572 | `a3ca581dfcd963fa8e36179c65bc1854a6b1748e86486de6a73a98dcb38093a9` |
| `pipeline_v3.py` | 18,543 | `832efe715586fd50f24c6c1a2bfb5969dc60f9fb870998d3b3c01be0df270058` |
| `support_v2.py` | 13,006 | `1f354bb160d3c75891dc2c004734fdfdf2e6650475c172ffb7e029f6cb8f09c9` |
| `targeted_extractive.py` | 3,518 | `e7a1a8af4b2b89d6652348ea3267d2ace99ad7d64583dfaf4d77553ce8fa27ea` |

Only `pipeline_v3.py` changed from the historical RCV1 identity (24,717 bytes,
`4d5b96679fd610f7ddadc245486aec0750fc02f3045c453409f49b645940f203`).
That RCV2 change replaces `run_nonlocked_regression()` with a deterministic
`PipelineV3Error` before any I/O; it does not alter the explicit hash-bound
RED1 verifier or the observed clean semantic results.

## Executable verification evidence

- Legacy fail-closed regression: 1/1 PASS, with `Path.read_text=0` and
  `load_jsonl=0` before the deterministic error.
- RED1 membership boundary: 5/5 PASS; consumed, EV1, unknown, and wrong-path
  memberships are rejected before open.
- Focused RED1 remediation: 20/20 PASS.
- Exact safe V3 allowlist: 24/24 PASS. The former 23-test RCV1 set is expanded
  by the mandatory legacy fail-closed regression; no legacy safety test is
  deselected.
- W3-003 synthetic clean replay: 14/14 PASS twice; 2 STANDARD / 7 CORRECTIVE /
  5 ABSTAIN; zero citation failures, ineligible selections, or network calls;
  SHA-256 `285bcc3187eeb7252cbe9f4c9d61fca00fc57af8cba873ae83e4b2df72ca4a6a`.
- W3-001 exact non-locked allowlist replay: 7/10 safe STANDARD, 3 abstentions,
  10/10 safe probes, zero unsafe STANDARD, citation failures, ineligible
  selections, and forbidden opens; SHA-256
  `2ec13e0fb237ebae6d7635b6ff4e9ae628ee25c50694e4f973d136ddf818708d` twice.

The machine-readable command/exit-code record is
`reports/week_03/results/w3_003_rm2_red1_rcv2_command_evidence.json`.

## Safety and scope

RCV2 verification opened no consumed holdout, EV1, or W2 locked evidence. No
notebook, new independent evaluation, or Week 4 work occurred. PUB2 later
staged, committed, pushed, and remotely verified the approved implementation
publication. W3 P0 remains `BLOCKED / REMEDIATION REQUIRED`; W4 remains blocked.

## RPF1 and publication status

The detached RPF1 package was reconciled against the frozen RCV2 source/tests
and accepted by independent Senior review. PUB1 was Senior byte reviewed;
PUB2-WF1 whitespace normalization was Senior approved; and PUB2 published the
exact implementation candidate at
`cd97de602140e334ec499e8dfa27fa08ec1a6260`. The remote commit was independently
verified. RM2 is closed, while W3 P0 remains blocked pending a new independent
product evaluation.
