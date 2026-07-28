# PayResolve Synthetic KB Generation Guideline v1

## Purpose and identity

This guideline controls `payresolve_synthetic_kb` version `kb_v1`. Every record
is English fictional content for **PayResolve Demo Bank** and exists only for
retrieval research. It is not a real policy, legal statement, compliance rule,
customer instruction, or representation of VinSmartFuture or any bank.

## Allowed scope and vocabulary

Use only the ten canonical Banking77 intents locked in
`configs/kb/kb_v1.json`. Preserve the exact taxonomy label
`reverted_card_payment?`; use `reverted_card_payment` only as its filesystem-safe
slug. Content may use generic terms such as transfer, merchant, card payment,
ATM, pending, declined, failed, reversed, recipient, review, and escalation.

Do not generate account-specific advice, real legal/compliance claims, real bank
names, real phone numbers, real customer data, or operational instructions that
could be mistaken for an actual bank policy.

## Document-type contract

- `faq`: concise customer-facing explanation of one state and its boundary.
- `policy`: fictional eligibility, timing, and decision rules.
- `runbook`: ordered agent checks that never request passwords, PINs, or full
  credentials.
- `escalation_guide`: explicit trigger, safe handoff, and prohibited actions for
  higher-risk cases.

Each document must provide focused, independently retrievable sections. A section
contains one coherent fact or procedure and uses a stable lowercase safe ID.

## Status and version semantics

- `APPROVED`: eligible only when effective on the fixed as-of date and not expired.
- `DRAFT`: never eligible, even when wording looks more attractive or current.
- `EXPIRED`: never eligible and must have a valid expiry date.

Version families use stable `document_family_id` values. A successor references
the immediately superseded document. V1/V2/V3 histories must differ in meaningful
fictional handling windows, criteria, guidance, or verification steps; metadata-
only copies are forbidden.

All time windows and numbers are deliberately fictional controls and must stay
internally consistent within the active approved version.

## Fine-grained intent and hard-negative construction

Shared vocabulary is intentional only when a decisive fact keeps the evidence
human-resolvable:

- transfer state: pending versus technical failure versus explicit decline versus
  completed-but-not-received;
- merchant card state: pending versus declined versus later reversed;
- ATM state: pending versus declined versus not recognized.

A hard negative should share rail or state vocabulary but contradict the decisive
fact. Do not make a record support two labels accidentally. Multi-intent records
are allowed only when both labels genuinely share one controlled workflow and the
mapping remains explicit.

## Safety and evidence granularity

Never request PINs, passwords, one-time codes, or full card/account numbers.
High-risk unrecognized cash withdrawals require an escalation path and must not
be framed as ordinary troubleshooting. Where policy evidence is intentionally
absent, do not imply that an FAQ or runbook is a policy substitute.

## Consistency and duplicate prevention

Before freeze:

1. validate schema, enums, dates, IDs, slugs, references, and eligibility;
2. compare exact and normalized section content;
3. review deterministic token-Jaccard near-duplicate candidates;
4. confirm every similar pair has a meaningful state, rail, workflow, or version
   difference;
5. confirm every active family has at most one eligible approved version;
6. confirm no placeholders, lorem ipsum, PII, real institution, or real contact
   information appears.

## Manual review checklist

- [ ] Canonical intent and slug are aligned.
- [ ] Decisive state/rail cue is explicit.
- [ ] The document type serves its defined purpose.
- [ ] Status and dates match the intended lifecycle.
- [ ] Successor content differs meaningfully from the previous version.
- [ ] Fictional time windows are internally consistent.
- [ ] Hard negatives are similar but resolvable.
- [ ] No secrets, PII, real policy, or unsafe instruction appears.
- [ ] Sections are non-empty, focused, and not duplicated.
- [ ] Synthetic disclaimer and fictional organization are present.
