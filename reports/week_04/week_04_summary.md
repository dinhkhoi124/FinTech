# Week 04 Summary

## P0 objective
Minimal API/logging/versioning/tests + one incident exercise.

## Status
W4-001 is Senior-approved for feature-branch publication and a local
REAL_SAFE_DEGRADED demo. W4-002 remains blocked.

## Deliverables completed
- Real FastAPI wrapper over frozen classifier, selected R0 retrieval, and
  grounded V3 generation/citation verification.
- PAYRESOLVE_QUERY_API_V1 health/readiness/version/query contract.
- Mandatory safe-degraded release policy and privacy-minimized logs.
- Focused tests, real offline adapter integration, and local HTTP smoke.
- Architecture/runbook and compact Senior review evidence.

## Key evidence
| Claim | Evidence | Result | Decision |
|---|---|---|---|
| Real candidate path used | W4-001 evidence and adapter integration | PASS | Senior-approved safe-degraded demo only |
| Safe-degraded policy enforced | 11 W4 tests and HTTP smoke | PASS | Demo-only, non-autonomous |
| Existing grounded pipeline unaffected | combined focused run | 26/26 PASS | No candidate change |
| Local service is operable | health/version/query | 3/3 HTTP 200 | Integration may be reviewed |
| Gold/evaluator isolation | runtime source/open audit | 0 data opens | PASS |

## P0 exit criteria
See `docs/ROADMAP.md`.

## Risks / limitations
- The official Week-3 autonomous P0 did not pass.
- Service is local demo-only and has no authentication, TLS, rate limiting, or
  production approval.
- A tracked frontend root .env contains publishable Supabase variable names;
  values were not printed and remediation is out of W4-001 scope.

## Handoff
- W4-001-PUB1 may publish the two approved feature branches and freeze the
  local demo startup runbook. W4-002 remains blocked.
- Production readiness and autonomous banking action are not claimed.
