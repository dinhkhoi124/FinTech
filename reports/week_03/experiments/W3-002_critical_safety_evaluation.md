# W3-002 Critical Safety Evaluation

## Protocol integrity

The 60-query `critical_eval_v1` set was authored scenario-first, corrected only
before evaluation with a ledger, exhaustively mapped against all 52 eligible
approved sections, overlap-audited, and frozen before encoder execution. Primary
and reproduction stable outputs are identical.

## V0 production-candidate result

| Metric | Result |
|---|---:|
| Positive grounded resolution recall | 0.625 (25/40) |
| Positive wrong-evidence answers | 6/40 |
| Positive unnecessary abstentions/non-resolutions | 15/40 |
| Complete multi-document resolution | 0/6 |
| Negative abstention accuracy | 1.000 (20/20) |
| Unsafe negative answers | 0 |
| Safe resolution | 0.750 (45/60) |
| Citation correctness on answered responses | 1.000 (31/31) |
| Unsupported factual claims | 0/93 |
| DRAFT / EXPIRED citations | 0 / 0 |
| Wrong-status context / metadata failures / system errors | 0 / 0 / 0 |

Family recall is transfer 0.750, card_payment 0.583, and cash_withdrawal 0.500.
Although headline utility thresholds are met, the six wrong-evidence positive
answers violate the hard gate. Approved citations are not automatically relevant.

## Invalidated verdict

The table is historical numerical evidence only. Senior review found the original
mapping audit self-referential, so critical-set integrity is `INVALIDATED` and the
model/pipeline verdict is `NOT ESTABLISHED`. Week 3 P0 is `BLOCKED / IN PROGRESS`;
no production variant is selected and Week 4 remains blocked.
