# W2-001 — Controlled Synthetic KB Specification, Generation, and Validation

## Engineering question

Can a compact English synthetic banking KB provide version/status traps,
fine-grained intent boundaries, and machine-checkable coverage strong enough for
later gold evidence mapping without starting retrieval work?

## Scope and hypothesis

W2-001 is P0 and freezes exactly ten Banking77 labels. The hypothesis was that a
36-document design could meet all lifecycle and coverage invariants while keeping
the content human-reviewable. The fixed as-of date is `2026-07-28`; no machine
clock determines eligibility.

No Banking77 official-test outcomes, gold queries, embeddings, indexes, retrievers,
generation components, or P1 variants were used.

## Controlled setup

- Dataset: `payresolve_synthetic_kb/kb_v1`.
- Organization: fictional PayResolve Demo Bank.
- Language/source: English/synthetic.
- Canonical records: one JSONL source.
- Locked intents: four transfer, three card-payment, and three cash-withdrawal
  labels, including exact `reverted_card_payment?`.
- Canonical slug for that label: `reverted_card_payment`.
- Validator: Python standard library; no new framework or model.

## Intent-boundary design

The intent cards make three clusters operational:

- transfer: non-terminal pending vs terminal technical failure vs explicit refusal
  vs completed-but-not-received;
- card: open merchant authorization vs immediate refusal vs later reversal;
- cash: recognized pending ATM entry vs recognized refusal vs unrecognized
  high-risk ATM event.

`cash_withdrawal_not_recognised` has approved policy, runbook, and immediate
escalation evidence. `declined_card_payment` intentionally has FAQ and runbook
but no approved policy, creating a later evidence-sufficiency case without
creating a query or gold mapping in W2-001.

## First-28 quality gate

The document plan freezes a meaningful first tranche rather than treating the
first 28 JSONL rows as accidental generation order.

| Check | Result |
|---|---:|
| Documents | 28 |
| Eligible approved | 20 |
| Intents with at least two eligible docs and two types | 10/10 |
| Complete EXPIRED → APPROVED → DRAFT families | 4 |
| Fully resolved hard-negative relationships | 9 |
| Gate | PASS |

The gate supported expansion to 36 because eight added records increased runbook
and escalation depth, added an attractive future draft and a retired escalation
trap, and did not change the intent subset, schema, eligibility rule, or scope.

## Final dataset

| Dimension | Result |
|---|---:|
| Documents | 36 |
| Eligible approved | 26 |
| APPROVED / DRAFT / EXPIRED | 26 / 5 / 5 |
| FAQ / Policy / Runbook / Escalation | 10 / 12 / 9 / 5 |
| Complete version families | 4 |
| Hard-negative relationships | 12 |
| Exact/normalized duplicate groups | 0 |
| Token-Jaccard candidates at 0.72 | 0 |
| Validation | PASS |

Each intent has two or three eligible approved documents and at least two document
types. DRAFT and EXPIRED eligible counts are both zero. All hard-negative
references resolve to eligible documents with the expected labels.

## Version and conflict evidence

Four complete families encode meaningful changes rather than metadata-only copies:

1. pending transfer: retired five-business-day window, active two-business-day
   window, and unapproved six-hour proposal;
2. card reversal: retired seven-calendar-day return, active five-business-day
   return, and unapproved provisional-credit proposal;
3. unrecognized cash: retired wait/general-support path, active immediate
   security handoff, and unapproved automation;
4. recipient not received: retired four-business-day wait, active one-business-day
   window, and unapproved immediate tracing.

## Debugging evidence

### Senior-review validator false-pass

- **Reproduce:** malformed mutations for integer `title`, empty `approved_by`,
  compatible-enum but incorrect family/product, disconnected or non-monotonic
  lifecycle chains, and incomplete hard-negative records returned `PASS`.
  Same-intent and overlapping hard-negative sets failed only incidentally through
  label checks, not their intended invariants.
- **Root cause:** the first validator enforced many contract checks but did not
  execute the JSON Schema or fully mirror several schema, lifecycle, and
  hard-negative invariants. Therefore malformed mutations could pass.
- **Fix:** retain the dependency-free custom validator but completely mirror the
  required field and enum rules, family/product mapping, exact planned lifecycle
  chains, and hard-negative relationship structure. The first-28 gate now counts
  only structurally valid families and relationships.
- **Regression tests:** 14 focused cases were added (29 W2-001 tests total), and
  all nine independent mutation probes now return `FAIL` with explicit codes.
- **Lesson:** storing a JSON Schema does not enforce it. A custom mirror needs
  direct mutation coverage and must validate the structures used by aggregate
  quality gates.

The valid full KB still passes with 36 documents and 26 eligible records. DRAFT
and EXPIRED eligible counts remain zero. Canonical dataset bytes did not change;
canonical SHA-256 remains
`e54a21529c516659265f82ca4818e1c844c05e8e7d7a692b02154115869d4c88`.

1. `py -3.11` was unavailable through Python Launcher in this shell. The frozen
   Python 3.11 semantic environment was used instead.
2. PowerShell sorting initially introduced a UTF-8 BOM. The strict JSONL loader
   rejected it; the file was rewritten as UTF-8 without BOM and a regression test
   now protects the encoding contract.
3. The first phone-number scanner examined metadata dates/IDs and produced 36
   false positives. The scan was narrowed to title/headings/content, retaining
   the safety check without treating ISO dates as contacts.

## Decision

Freeze the 36-document `kb_v1`. Senior review verdict: `APPROVE_COMMIT`.
W2-001 is DONE / REVIEWED / ACCEPTED in the current repository history. Do not
alter the dataset for retrieval scores and do not start W2-002 until separately
authorized.

## Limitations

- Token-Jaccard is deterministic lexical screening, not semantic duplicate
  detection; zero candidates is not proof of zero semantic overlap.
- Synthetic timelines are intentionally fictional and must not be interpreted as
  actual banking policy.
- Gold evidence quality and retrieval usefulness remain unevaluated because they
  belong to W2-002 and W2-003.

## Evidence

- Config/schema/intent definitions: `configs/kb/`.
- Canonical documents: `data/kb/kb_v1.jsonl`.
- Generation guideline: `docs/kb/KB_GENERATION_GUIDELINE_V1.md`.
- Validation/manifest/coverage: `reports/week_02/results/`.
- Tests: `tests/test_kb_validation.py`.
