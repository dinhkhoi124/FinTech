"""Entry point for the narrow EA1 readiness Revision-11 review bundle."""

import build_critical_v2_ea1_revision7_review_bundle as builder
import build_critical_v2_ea1_revision10_review_bundle as revision10


REVISION11_PATHS = (
    "reports/week_03/results/critical_eval_v2_ea1_revision10_lineage.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision11_finding_closure.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision11_focused_verification.txt",
    "reports/week_03/results/critical_eval_v2_ea1_revision11_provenance_regressions.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision11_stale_binding_audit.json",
    "reports/week_03/results/critical_eval_v2_revision_11_ea1_failed_attempts.json",
    "reports/week_03/results/critical_eval_v2_revision_11_ea1_reuse_rebind_report.json",
    "scripts/evaluation/build_critical_v2_ea1_revision10_review_bundle.py",
    "scripts/evaluation/build_critical_v2_ea1_revision11_review_bundle.py",
    "tests/test_critical_v2_execution_revision10.py",
    "tests/test_critical_v2_execution_revision11.py",
)


if __name__ == "__main__":
    builder.BUNDLE_REVISION = 11
    builder.TASK_PATHS = tuple(
        dict.fromkeys(builder.TASK_PATHS + revision10.REVISION10_PATHS + REVISION11_PATHS)
    )
    builder.FOCUSED_MODULES = (
        "tests.test_critical_v2_execution_revision11",
        "tests.test_critical_v2_execution_revision10",
        "tests.test_critical_v2_execution_readiness",
    )
    builder.EXTRA_COMPILE_PATHS = (
        "scripts/evaluation/build_critical_v2_ea1_revision10_review_bundle.py",
        "scripts/evaluation/build_critical_v2_ea1_revision11_review_bundle.py",
        "tests/test_critical_v2_execution_revision10.py",
        "tests/test_critical_v2_execution_revision11.py",
    )
    raise SystemExit(builder.main())
