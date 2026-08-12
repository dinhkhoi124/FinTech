"""CLI for W3-002-CR1-EA1 execution readiness and future lifecycle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--root", type=Path, default=Path("."))
    result.add_argument(
        "--config",
        type=Path,
        default=Path("configs/evaluation/critical_eval_v2_execution.json"),
    )
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("verify-contract", "prepare-readiness", "verify-execution-readiness"):
        commands.add_parser(name)
    run = commands.add_parser("run-critical")
    run.add_argument("--run-label", required=True, choices=("primary", "reproducibility_rerun"))
    run.add_argument("--variant", required=True, choices=("V0", "V1", "V2"))
    for name in (
        "freeze-primary",
        "evaluate-frozen-primary",
        "freeze-reproducibility",
        "evaluate-frozen-reproducibility",
        "verify-reproducibility",
        "finalize",
        "verify-results",
    ):
        commands.add_parser(name)
    return result


def main() -> int:
    args = parser().parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    sys.path.insert(0, str(root / "src"))
    from payresolve_ai.evaluation.critical_v2_execution import (
        CriticalV2ExecutionError,
        assert_evaluator_load_allowed,
        evaluate_frozen_run,
        execute_variant_runtime,
        finalize_results,
        freeze_raw_run,
        prepare_readiness,
        run_critical,
        verify_execution_contract,
        verify_reproducibility,
        verify_readiness,
        verify_results,
    )

    try:
        if args.command == "verify-contract":
            payload = verify_execution_contract(root, config_path)
        elif args.command == "prepare-readiness":
            payload = prepare_readiness(root, config_path)
        elif args.command == "verify-execution-readiness":
            payload = verify_readiness(root, config_path)
        elif args.command == "run-critical":
            payload = run_critical(
                root,
                config_path,
                args.run_label,
                args.variant,
                executor=lambda payloads, config, label, variant, loaded: execute_variant_runtime(
                    payloads, config, label, variant, loaded, root=root
                ),
            )
        elif args.command == "freeze-primary":
            payload = freeze_raw_run(root, config_path, "primary")
        elif args.command == "freeze-reproducibility":
            payload = freeze_raw_run(root, config_path, "reproducibility_rerun")
        elif args.command == "evaluate-frozen-primary":
            payload = evaluate_frozen_run(root, config_path, "primary")
        elif args.command == "evaluate-frozen-reproducibility":
            payload = evaluate_frozen_run(root, config_path, "reproducibility_rerun")
        elif args.command == "verify-reproducibility":
            payload = verify_reproducibility(root, config_path)
        elif args.command == "finalize":
            payload = finalize_results(root, config_path)
        elif args.command == "verify-results":
            payload = verify_results(root, config_path)
        else:
            raise CriticalV2ExecutionError(
                f"{args.command} requires completed authorized lifecycle artifacts"
            )
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, indent=2))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
