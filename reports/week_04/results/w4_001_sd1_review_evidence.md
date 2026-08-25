# W4-001-SD1 Review Evidence

## Status and isolation

- Status: W4_001_SAFE_DEGRADED_SERVICE_READY_FOR_SENIOR_REVIEW.
- Branch: feat/w4-safe-degraded-e2e.
- Worktree: E:\merged_partition_content\Khoi_Project\VinSmartFuture\FinTech-w4-safe-degraded-e2e.
- Baseline commit: 38eccbf51c6ac418837a87e4fd94dd6048e665ef.
- Baseline tree: 8ef7c7859d6a3a23aa0bfc5585ff1cc829932c83.
- Dirty main preserved: true. Final staged count is 0; no dirty-path
  last-write time is at or after clean-worktree creation.
- Frontend mutations: 0. Audit operations were read-only.
- No stage, commit, or push.

## Real runtime audit

| Area | Existing production path used |
|---|---|
| Query/generation entrypoint | payresolve_ai.generation.pipeline_v3.run_case_v3 |
| Classifier | frozen MiniLM query embedding plus portable Banking77 coefficients |
| Retrieval | selected R0 dense scoring and deterministic top-3 rank |
| Generation | target-aware V3 response plan plus TargetedExtractiveGenerator |
| Citation safety | generation.citations.verify_draft inside run_case_v3 |
| Outcome | STANDARD, CORRECTIVE, or ABSTAIN response plan |
| Model | local-only all-MiniLM-L6-v2 at pinned revision, CPU, normalized 384-D |
| KB/config | kb_v1, frozen R0 config/cache, generation V3 config, lexicon V2 |
| Reused tests | test_grounded_pipeline_v3.py plus focused service tests |

The adapter composes these existing primitives and does not copy an evaluation
harness or select fixture responses. It loads read-only assets once per process.

## Shell seam audit

The sibling shell is React UI -> QueryClient -> active MockQueryClient.
HttpQueryClient exists but is inert. Runtime mode is MOCK-only and the shell
contract is DRAFT_API_CONTRACT_V0_1. The backend does not accept fixtureId.

## Public contract and policy

Contract: PAYRESOLVE_QUERY_API_V1.

Endpoints: GET /health, GET /ready, GET /version, POST /query.

Every factual answer has human review required, autonomous action false, and
production approval false. Abstentions set escalation true. Runtime errors
return HTTP 503 with a distinct SYSTEM_ERROR envelope. Default CORS is limited
to localhost/127.0.0.1 port 8080, without credentials or wildcards.

## Dependency delta

The Week-3 semantic environment was not upgraded. FastAPI 0.115.12, Pydantic
2.11.5, Uvicorn 0.34.2, HTTPX 0.28.1, pytest 8.3.5, and exact transitive pins are
declared in requirements/week4-service.txt and installed only under ignored
artifacts/w4-service-deps.

## Verification evidence

| Check | Result |
|---|---|
| py_compile service modules | PASS |
| W4 unit/API/policy/adapter tests | 11/11 PASS |
| W4 plus existing grounded V3 focused run | 26/26 PASS |
| Real process-level adapter query | PASS |
| Real Uvicorn health/version/query HTTP smoke | 3/3 HTTP 200 |
| Smoke response | ABSTAIN_ESCALATE |
| Smoke intent | pending_cash_withdrawal |
| Smoke citations / evidence | 0 / 3 |
| Smoke total latency | 42.4869 ms |
| Model/KB/retrieval | pinned MiniLM / kb_v1 / R0 |
| Candidate commit surfaced | 38eccbf51c6ac418837a87e4fd94dd6048e665ef |
| Network model downloads | 0; offline variables enforced |
| Gold/evaluator/official EV3 result data opens | 0 |
| Log raw-query field | absent |
| Log Gold/evaluator fields | absent |
| Server after smoke | stopped |
| Staged / commit / push | 0 / false / false |

The manual smoke query was authored without opening locked evaluation inputs.

## Security audit

The sibling shell tracks a root .env. Names found were Supabase URL/project ID
and publishable-key variables, including VITE variants. No variable name
indicated a service-role, private, secret, token, password, or API-key value.
Values were not printed. Tracking a root environment file remains a
repository-hygiene finding for a separately authorized frontend/security task.

## Changed files

Service implementation:

- src/payresolve_ai/service/__init__.py
- src/payresolve_ai/service/__main__.py
- src/payresolve_ai/service/adapters.py
- src/payresolve_ai/service/app.py
- src/payresolve_ai/service/audit_logging.py
- src/payresolve_ai/service/contracts.py
- src/payresolve_ai/service/query_service.py
- src/payresolve_ai/service/release_policy.py
- requirements/week4-service.txt
- tests/test_w4_safe_degraded_service.py

Documentation/evidence/lifecycle:

- docs/W4_SAFE_DEGRADED_SERVICE.md
- reports/week_04/daily/2026-08-26.md
- reports/week_04/results/w4_001_sd1_review_evidence.md
- reports/week_04/week_04_summary.md
- PROJECT_STATE.md
- TASKS.md

## Requested Senior decision

APPROVE_W4_001_SERVICE_BASELINE_AND_AUTHORIZE_SHELL_HTTP_INTEGRATION.

W4-002 remains blocked and no Week-5 advancement is authorized.

## W4-001-PUB1 backend publication manifest

Publication branch: `feat/w4-safe-degraded-e2e`. Baseline parent:
`38eccbf51c6ac418837a87e4fd94dd6048e665ef`. The staged path set must equal
the 17-path allowlist below, with no ignored dependency target, model cache,
scratch build, temporary log, or review bundle.

| Path | Bytes | SHA-256 | Role |
|---|---:|---|---|
| `PROJECT_STATE.md` | 110439 | `81a7cddd04f2eb1e03c10f80fe73edb16a95e98320acddb6c5419d1552d64ab6` | lifecycle handoff |
| `TASKS.md` | 66555 | `49abdb0356b5e08d447f8873e99030a0099c0eabaa07d8e92611e5799dc82868` | task board |
| `docs/W4_SAFE_DEGRADED_SERVICE.md` | 6513 | `5ed39d2fce3af20daa0318778f347c6dce0d003f90caad9876dd3712f26f523e` | frozen demo runbook |
| `reports/week_04/daily/2026-08-26.md` | 1758 | `7ed054ff29fd2f322dd34fbbe813402c53939327d903c56cf4df0d46d683bb25` | daily evidence |
| `reports/week_04/results/w4_001_sd1_source_audit.json` | 9726 | `952a0d7199531b1a64743a0c7d025a87ae9c75614eec9071a864bc9c0a7eb7d3` | source audit |
| `reports/week_04/week_04_summary.md` | 1788 | `0283cd2119831196838b40e48d5b62553de7665a4c98a00438e0d49eecc2eb0e` | weekly summary |
| `requirements/week4-service.txt` | 474 | `aa0790149f16956ac61c7548a8c8fd3f24a0302ad8221a86432d1aefbe6a7bee` | isolated service dependency lock |
| `src/payresolve_ai/service/__init__.py` | 122 | `f2fc824b1a3629d86286fd7bebbb2e454ccf21b0149b293c11dca5931f397dad` | service package |
| `src/payresolve_ai/service/__main__.py` | 161 | `415c1e507eafa4803d6f83f0edd7e904f24067f134742d1a01ba331f1d2283c1` | service entrypoint |
| `src/payresolve_ai/service/adapters.py` | 9676 | `5c8745c1ff414ea92f9a67ec79d2e4af6f16f3edaf3767e339730e0befddf356` | frozen-runtime adapter |
| `src/payresolve_ai/service/app.py` | 5080 | `d43c7039fa9b464b40389f6400a9a86e66c80a3a588bb1dacea713b4d497dcb9` | FastAPI application |
| `src/payresolve_ai/service/audit_logging.py` | 2601 | `6eee44f05acdd7e78a517a1a9c27d3b45f2d9b82e71a989c1938abef5df644ae` | raw-query-free audit log |
| `src/payresolve_ai/service/contracts.py` | 3166 | `2bfdcfb10ed1abfaba56040ed9176a779d4b608d5edffd7ab9669f9881d75244` | API contract |
| `src/payresolve_ai/service/query_service.py` | 2043 | `3eed1b4aac83ac92312905dcb829119abf6ff97a95bcc2e8bb9e572dafb0eb7a` | query orchestration |
| `src/payresolve_ai/service/release_policy.py` | 2323 | `617fc089f333feb35f110a1c939b1a42e67f5807a8db4189ecfdad523d2bbeed` | safe-degraded release policy |
| `tests/test_w4_safe_degraded_service.py` | 8217 | `c195418c9bb1326d7f9529d883157d423f488784913b3e263a2714ef44678524` | focused regression test |

The seventeenth allowlisted path is this manifest/evidence document:
`reports/week_04/results/w4_001_sd1_review_evidence.md`. Its materialized
bytes and SHA-256 are recorded by the final release receipt, rather than a
self-referential table row. Its role is `backend_publication_manifest`.
