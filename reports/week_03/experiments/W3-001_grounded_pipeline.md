# W3-001 Grounded Pipeline

## Hypothesis and boundary

A deterministic extractive generator can provide an auditable ANSWER path while
an evidence gate prevents factual output when approved/effective evidence is
insufficient. This development task does not estimate final Week 3 safety.

## Pipeline

`query → frozen classifier trace → R0 top-3 → approved context → evidence gate →
extractive generator → citation verifier → ANSWER or ABSTAIN_ESCALATE`

R0 never consumes predicted intent. Context rejects DRAFT, EXPIRED, and
future-effective chunks. Every answer claim must equal a verbatim support quote,
resolve through a unique citation alias to selected evidence, and render with its
citation. Any generator or citation failure returns the generic fallback with no
claims or citations.

## Reproducibility and verification

Primary and rerun JSONL files are byte-identical with SHA-256
`ef405bec24bfac9723b930ac0ed4bd6a3c14d139b0ca3c0fb450e219f86bc118`.
Tracked verification recomputes candidates, outputs, metrics, membership, and
hashes without `_rank_queries`, encoder cache, fitted model, or network.

## Senior review correction

### Reproduce

- A citation with the correct `evidence_id` but fabricated document/section/title,
  type/status/version metadata passed.
- Selected-run citation correctness was reported as 1.00 despite zero answers.
- Any positive ANSWER counted as success without checking frozen evidence roles.
- Extractive weights were hard-coded as `0.7/0.3` in implementation.

### Root cause

The verifier resolved only citation alias/evidence ID and exact quotes. Metrics
treated abstentions as citation-correct and used cases rather than answered items
or claims as denominators. Positive success used response type alone. Generator
construction did not consume the frozen weight fields.

### Fix

Citation objects now require an exact metadata schema and equality with selected
`EvidenceChunk`; claims require unique typed IDs and aligned evidence/quote/alias
lists. Positive success requires a verifier-passing answer citing gold or
acceptable evidence, with every strict gold ID required for multi-document cases.
Answer- and claim-level rates use applicable denominators and `null` when empty.
The generator receives and validates both configured weights.

### Regression tests

Controlled mutations cover fabricated citation metadata, malformed claim arrays,
wrong approved evidence, multi-document incompleteness, vacuous rates, claim-level
unsupported counts, configured weights, and tracked config drift.

### Lesson

Syntactic grounding and vacuous aggregate rates are not evidence of relevant
grounded resolution. Identity, metadata, evidence role, and denominator semantics
must all be verified explicitly.

## Observed limitation

The frozen selected gate produces 20 abstentions. Fixture tests prove the ANSWER
and citation paths work, but the selected development configuration has no
observed grounded resolution recall. Citation correctness and unsupported-claim
rate are not applicable on this run. W3-002 must not inherit a utility claim.

## Scope confirmation

The preregistered gate-v1 experiment completed successfully as an experiment,
but its selected policy is not a usable production candidate because it abstains
on all positive development queries. Senior verdict is `APPROVE_COMMIT — PARTIAL
BASELINE`: implementation is DONE / REVIEWED / ACCEPTED and overall status is
PARTIAL / REVIEWED / ACCEPTED. Review lifecycle: initial implementation → Senior
`FIX_REQUIRED` → citation metadata binding → evidence relevance metrics →
non-vacuous citation metrics → config-driven generator weights → final
approval. No external LLM, critical set, ablation, API/UI, W3-001-CR1, W3-002,
or P1 work was created; Week 4 remains NOT STARTED.
