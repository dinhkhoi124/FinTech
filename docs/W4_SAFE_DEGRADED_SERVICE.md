# W4 Safe-Degraded Service

## Scope

This service exposes the real PayResolve candidate for a local, non-autonomous
demo. It is not a production banking service, does not execute account or money
movement operations, and does not claim that the Week-3 autonomous P0 gate
passed.

Every factual response requires human review. Autonomous action and production
approval are always false. An abstention escalates. Runtime failures use a
separate SYSTEM_ERROR envelope and are never represented as abstentions.

## Architecture

    FastAPI
      -> QueryService
         -> RealPayResolveAIAdapter (process-level, read-only assets)
            -> frozen MiniLM encoder + portable Banking77 classifier
            -> selected R0 dense retrieval
            -> generation.pipeline_v3.run_case_v3
               -> target-aware response plan
               -> extractive generation
               -> citation verification
         -> safe-degraded release policy
         -> structured query audit log

The adapter loads the model, classifier, corpus, embeddings, generation config,
lexicon, and IDF tables once during startup. It reads no Gold mapping, official
EV3 result, evaluator mapping, or shell fixture.

## Frozen local-demo startup runbook

This runbook starts the approved local demo only. It does not install or
upgrade dependencies, download model assets, enable autonomous action, or make
a production-readiness claim.

### A. Backend

Open PowerShell in:

    E:\merged_partition_content\Khoi_Project\VinSmartFuture\FinTech-w4-safe-degraded-e2e

Use the existing semantic Python runtime and the already-installed, ignored W4
service dependency target. The runtime root must be the read-only original
FinTech checkout carrying the frozen model and retrieval assets:

    $backend = 'E:\merged_partition_content\Khoi_Project\VinSmartFuture\FinTech-w4-safe-degraded-e2e'
    $runtime = 'E:\merged_partition_content\Khoi_Project\VinSmartFuture\FinTech'
    Set-Location -LiteralPath $backend
    $env:PYTHONPATH = "$backend\artifacts\w4-service-deps;$backend\src"
    $env:PAYRESOLVE_RUNTIME_ROOT = $runtime
    $env:HF_HUB_OFFLINE = '1'
    $env:TRANSFORMERS_OFFLINE = '1'
    $env:HF_DATASETS_OFFLINE = '1'
    & "$runtime\.venv-semantic\Scripts\python.exe" -m uvicorn payresolve_ai.service.app:app --host 127.0.0.1 --port 8765

In a second PowerShell window, verify only liveness/readiness/version:

    Invoke-RestMethod http://127.0.0.1:8765/health
    Invoke-RestMethod http://127.0.0.1:8765/ready
    Invoke-RestMethod http://127.0.0.1:8765/version

The Week-3 semantic environment is not upgraded. Default CORS origins are only
http://localhost:8080 and http://127.0.0.1:8080. `PAYRESOLVE_CORS_ORIGINS` may
override these with an explicit, comma-separated, non-wildcard list.

### B. Frontend

Open a new PowerShell window in:

    E:\merged_partition_content\Khoi_Project\VinSmartFuture\payresolve-copilot-shell-real-api

Start the published feature branch in HTTP mode. Do not write these values to
the tracked historical `.env` file:

    Set-Location -LiteralPath 'E:\merged_partition_content\Khoi_Project\VinSmartFuture\payresolve-copilot-shell-real-api'
    $env:VITE_QUERY_RUNTIME = 'http'
    $env:VITE_PAYRESOLVE_API_BASE_URL = 'http://127.0.0.1:8765'
    npm run dev -- --port 8080

Open http://localhost:8080 in the browser. The approved demo labels are REAL
AI, Safe Degraded Demo, Human Review Required, and No Autonomous Action.

### C. Demo operating boundary

- Product: PayResolve AI — Banking Support Agent Copilot.
- Mode: `REAL_SAFE_DEGRADED`; local end-to-end demo is authorized.
- Production readiness: not claimed. Autonomous P0: not authorized. Banking
  side effects: none. Human review: required.
- Week-3 EV3 is official `INVALID`, immutable, and not rerun. EV4 is not
  authorized. W4-002 is not started.

### D. Troubleshooting

- **Port collision:** identify and stop only the intended transient process, or
  use an unused frontend port and add that explicit origin to
  `PAYRESOLVE_CORS_ORIGINS` before backend startup.
- **Backend unavailable:** HTTP-mode shell must show `SYSTEM_ERROR`. It must
  not fall back to a mock fixture or silently substitute an abstention.
- **Model asset path:** confirm `PAYRESOLVE_RUNTIME_ROOT` names the original
  read-only FinTech checkout and that all three offline flags remain `1`; do
  not download or replace model assets.
- **Windows ACL/build note:** if Nitro cannot write `.output` in the sibling
  worktree, build an exact-current-source scratch mirror for verification. This
  is a filesystem limitation, not a product fallback or a reason to alter
  source.

## API

- GET /health: process liveness.
- GET /ready: model/runtime readiness.
- GET /version: service, contract, model, KB, retrieval, and candidate identity.
- POST /query: PAYRESOLVE_QUERY_API_V1.

Example request:

    {"request_id":"demo-001","query":"What approved guidance is available for this pending withdrawal?"}

Success responses use REAL_SAFE_DEGRADED and one of ANSWER_STANDARD,
ANSWER_SAFE_CORRECTIVE, or ABSTAIN_ESCALATE. They include classifier intent,
answer/reason, citations, evidence, release policy, version metadata, and
measured total/stage latency.

## Structured logging

Each query log stores a SHA-256 query hash, request ID, intent, response type,
release flags, evidence IDs, citation count, grounded/escalation flags, latency,
versions, and success/error status. It does not persist the raw query, secrets,
Gold labels, evaluator labels, or mock fixture identifiers.

## Frontend integration seam

The published sibling React shell selects `MockQueryClient` or
`HttpQueryClient` through `VITE_QUERY_RUNTIME`. HTTP mode requires
`VITE_PAYRESOLVE_API_BASE_URL`, maps `PAYRESOLVE_QUERY_API_V1` DTOs to the UI
contract, has no automatic retry, and never falls back to fixtures after an
HTTP, network, timeout, malformed-payload, or configuration error. Real raw
query text is not persisted by the frontend; backend audit logging is
authoritative. Backend requests intentionally reject the mock-only `fixtureId`
field.

## Known limitations

- Demo-only, local, single-process baseline.
- No authentication, rate limiting, TLS, or external observability.
- No production approval or autonomous banking action.
- Candidate abstentions remain visible and escalated; the wrapper does not tune
  or change candidate behavior.
- W4-002 remains blocked until Senior review.
