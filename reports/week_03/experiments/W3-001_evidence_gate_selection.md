# W3-001 Evidence Gate Selection

## Frozen development protocol

- 20 cases: ten W2 development ANSWER references and ten new negative probes.
- Zero W2 locked ID/exact/normalized overlap.
- Zero Banking77 train/test exact/normalized overlap; official-test contents were
  not manually inspected.
- Grid: top-1 `{0.40, 0.45, 0.50, 0.55}` × coverage `{0.30, 0.45, 0.60}`;
  ambiguity gap fixed at `0.03`.
- Tie-break: safe accuracy descending, unsafe rate ascending, positive grounded
  resolution recall descending, negative abstention descending, then lower thresholds.

## Candidate metrics

| Candidate | Safe | Unsafe | Positive answer / relevant / wrong | Grounded recall | Negative abstention | Total A / Abstain |
|---|---:|---:|---:|---:|---:|---:|
| S0.40_C0.30 | 0.50 | 0.10 | 1 / 1 / 0 | 0.10 | 0.90 | 2 / 18 |
| S0.40_C0.45 | 0.50 | 0.00 | 0 / 0 / 0 | 0.00 | 1.00 | 0 / 20 |
| S0.40_C0.60 | 0.50 | 0.00 | 0 / 0 / 0 | 0.00 | 1.00 | 0 / 20 |
| S0.45_C0.30 | 0.50 | 0.10 | 1 / 1 / 0 | 0.10 | 0.90 | 2 / 18 |
| S0.45_C0.45 | 0.50 | 0.00 | 0 / 0 / 0 | 0.00 | 1.00 | 0 / 20 |
| S0.45_C0.60 | 0.50 | 0.00 | 0 / 0 / 0 | 0.00 | 1.00 | 0 / 20 |
| S0.50_C0.30 | 0.50 | 0.10 | 1 / 1 / 0 | 0.10 | 0.90 | 2 / 18 |
| S0.50_C0.45 | 0.50 | 0.00 | 0 / 0 / 0 | 0.00 | 1.00 | 0 / 20 |
| S0.50_C0.60 | 0.50 | 0.00 | 0 / 0 / 0 | 0.00 | 1.00 | 0 / 20 |
| S0.55_C0.30 | 0.45 | 0.10 | 0 / 0 / 0 | 0.00 | 0.90 | 1 / 19 |
| S0.55_C0.45 | 0.50 | 0.00 | 0 / 0 / 0 | 0.00 | 1.00 | 0 / 20 |
| S0.55_C0.60 | 0.50 | 0.00 | 0 / 0 / 0 | 0.00 | 1.00 | 0 / 20 |

## Frozen decision

Select `S0.40_C0.45`. Several policies tie at safe accuracy 0.50; the second
criterion prefers unsafe rate 0.00 over candidates with grounded recall 0.10 but
unsafe rate 0.10, then lower thresholds break the remaining tie.

This is a faithful but degenerate safety-first selection: negative abstention is
perfect and unsafe answers are zero, while positive grounded resolution recall is
zero. The selected run has zero answers and zero claims; its citation correctness
and unsupported-claim rate are `null` / not applicable. No thresholds were added
or tuned after observing outcomes. Overall gate result: PARTIAL — UTILITY NOT
DEMONSTRATED. Senior verdict is `APPROVE_COMMIT — PARTIAL BASELINE`; W3-001
overall is PARTIAL / REVIEWED / ACCEPTED, not PASS. The selected gate is not
accepted as a useful production candidate because it answered zero of ten
positive development queries. W3-001-CR1 is recommended but NOT STARTED.
