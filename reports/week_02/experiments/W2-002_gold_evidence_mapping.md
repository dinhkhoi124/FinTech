# W2-002 — Gold Evidence Mapping

## Engineering question

Can the frozen `kb_v1` support a manually reviewable 60-query evidence dataset
that separates answerable requests from attractive DRAFT/EXPIRED or policy-gap
traps without introducing retrieval work?

## Scope and protocol

W2-002 is P0 evaluation-data work. Inputs were frozen `kb_v1`, its ten intent
cards, metadata, and fixed eligibility date `2026-07-28`. Embeddings, indexes,
retrievers, R0/R1, generation, API/UI, P1 work, and model tuning remained closed.

Authoring used two passes. Pass A created scenario-first English queries from
intent boundaries, metadata, document types, and high-level scenarios. The
canonical scenario plan was frozen at SHA-256
The initial scenario hash was
`580c7c301e1348725590c3cae50ed747d5c14d2817a26658f00854f67d96cef4`.
Only then did Pass B inspect full KB sections and assign evidence. No query text
changed during initial Pass B. Senior review later required 12 recorded query
corrections; the new scenario hash is
`97cdf1ae69b280af14043e987452040db925c3e93acb869c1072dfb4cb32c486`.

## Dataset result

| Dimension | Result |
|---|---:|
| Total queries | 60 |
| Development / locked test | 10 / 50 |
| ANSWER / ABSTAIN_ESCALATE | 50 / 10 |
| Development ANSWER per intent | 1 × 10 |
| Locked ANSWER per intent | 4 × 10 |
| Gold / acceptable / hard-negative / forbidden section references | 56 / 50 / 50 / 10 |
| Eligible documents represented | 26 / 26 |
| Ineligible documents represented as forbidden | 10 / 10 |
| Valid locked multi-document mappings | 4 |
| Validation | PASS |

Locked ANSWER coverage includes 26 normal tags, 10 hard-negative/confusion tags,
four multi-document tags, three short-query tags, and four version-sensitive
tags. Gold evidence includes FAQ, policy, runbook, and escalation-guide types.

## Senior-review correction

The initial construction review accepted 60/60 rows but did not establish direct
support for the information requested. The validator proved structural validity,
not whether primary gold answered timing, checks, action, retry, escalation, or
explanation. It also treated draft/expired requests as automatic abstentions when
approved sections sometimes supported a corrective answer.

The correction audited all 50 ANSWER rows, changed 19 primary-gold roles and 19
acceptable roles, rewrote two unsupported/weak ANSWER queries, and replaced all
ten safety probes. All 50 ANSWER rationales now name the requested dimension,
primary section, supporting fact, and secondary evidence role. The correction
ledger preserves old and new values; the initial 60/60 claim remains historical
evidence rather than being erased.

Senior v2 review accepted every other correction and identified one residual
primary/acceptable inversion in `Q_LOCK_CASH_PEND_002`. The FAQ section that
establishes recognition plus pending state is now primary; the runbook recognition
gate is secondary. Query/scenario/membership bytes were unchanged.

## Safety mapping

Ten redesigned locked safety probes cover every ineligible record: five DRAFT
and five EXPIRED. Each requests a precise unsupported operational or entitlement
detail, has empty gold and acceptable evidence, a section-level forbidden
reference, `no_approved_evidence`, and `ABSTAIN_ESCALATE`. Each rationale records
the approved sections checked and why they cannot provide a complete corrective
answer. `Q_SAFE_010` retains the declined-card approved-policy gap without asking
for a claim that FAQ/runbook evidence could directly correct.

## Leakage controls

| Audit | Result |
|---|---:|
| Exact query duplicates | 0 |
| Normalized query duplicates | 0 |
| Near-duplicate candidates at token-Jaccard 0.72 | 0 |
| Query-to-KB candidates at token-Jaccard 0.72 | 0 |
| Banking77 train exact / normalized overlap | 0 / 0 |
| Banking77 official-test exact / normalized overlap | 0 / 0 |

The Banking77 comparison was automated equality only. Official-test query text
was neither printed nor manually inspected and did not influence authoring or
mapping. No embedding-based semantic overlap analysis was introduced.

## Reproducibility hashes

- KB raw: `e14aa83ed37c8de1ab3fc0fb8a0cae50f1b1e14083b774252a687bc5f0cf67c4`.
- KB canonical: `e54a21529c516659265f82ca4818e1c844c05e8e7d7a692b02154115869d4c88`.
- Initial → corrected scenario: `580c7c301e1348725590c3cae50ed747d5c14d2817a26658f00854f67d96cef4` → `97cdf1ae69b280af14043e987452040db925c3e93acb869c1072dfb4cb32c486`.
- Initial → corrected query dataset: `8774cea99a8e798e76f5e16bd2a6ba444cf5befe60a9e492daa6f1725da81cae` → `73d65c1209beac734123b9d1421f1fdefe32330712e4fe9359f26b7c620345aa`.
- Initial → v2 → one-row-patched mapping: `9925335db80712f1e465fcb17ce7f30ddf335f00131d2357decf25cdcdd476c4` → `fce991f536f88b593e078ccba1e460ec9a9ff3343d33aca130a822d7b39d6d98` → `4ed85198ac1929ea40356fb86d0e959ea81d8c3630aff405ac04e6540160069c`.
- Development membership: `15ee4de30609e67d65208a2d13fffb801964bc52a46288fa2e2c3bed43cab458`.
- Locked-test membership: `5682d314c17cae0d4c58274cc51b9e6e75dbec56d5be16e9bac712e709dc09b8`.

## Validation and tests

The dependency-light validator checks schema/enums, exact distributions,
canonical label/slug/family alignment, section existence and eligibility,
role disjointness, response invariants, document/type/case coverage, deterministic
ordering and hashes, frozen scenario alignment, and lexical leakage results.

Focused mutation testing passed 43/43 cases. Seven explicit Senior-review direct
mutations also failed as expected. Full-suite and project-document
validation results are recorded in the daily report after final verification.

## Decision and limitations

Senior final review verdict is `APPROVE_COMMIT`. W2-002 is DONE / REVIEWED /
ACCEPTED. Review history is preserved: initial construction review → Senior
`FIX_REQUIRED` → direct-support and safety correction → validator hardening →
residual one-row role inversion → final patch → `APPROVE_COMMIT`.

The dataset is appropriate as a locked input for a separately authorized W2-003,
but no retrieval claim is made here. Token Jaccard does not prove semantic
independence, one construction reviewer is not independent annotation, and all
banking procedures remain fictional research controls.
