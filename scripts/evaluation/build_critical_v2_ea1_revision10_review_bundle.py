"""Entry point for the EA1 readiness Revision-10 review-bundle builder."""

import build_critical_v2_ea1_revision7_review_bundle as builder


REVISION10_PATHS = (
    "data/evaluation/critical_eval_v2_revision_10_disclosure_literal_registry.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision10_finding_closure.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision10_disclosure_guard_results.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision10_provenance_regressions.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision10_focused_verification.txt",
    "reports/week_03/results/critical_eval_v2_ea1_revision10_stale_binding_audit.json",
    "reports/week_03/results/critical_eval_v2_revision_10_ea1_failed_attempts.json",
    "reports/week_03/results/critical_eval_v2_revision_10_ea1_reuse_rebind_report.json",
    "scripts/evaluation/build_critical_v2_ea1_revision10_review_bundle.py",
    "tests/test_critical_v2_execution_revision10.py",
)


if __name__ == "__main__":
    builder.BUNDLE_REVISION = 10
    builder.TASK_PATHS = builder.TASK_PATHS + REVISION10_PATHS
    builder.FOCUSED_MODULES = (
        "tests.test_critical_v2_execution_revision10",
        "tests.test_critical_v2_execution_readiness",
    )
    builder.EXTRA_COMPILE_PATHS = (
        "scripts/evaluation/build_critical_v2_ea1_revision10_review_bundle.py",
        "tests/test_critical_v2_execution_revision10.py",
    )
    raise SystemExit(builder.main())
