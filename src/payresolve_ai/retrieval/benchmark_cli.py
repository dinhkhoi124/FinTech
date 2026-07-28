"""CLI for the W2-003 benchmark lifecycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import (
    audit_dev_selection,
    build,
    finalize,
    finalize_review_correction,
    run_locked,
    select_r1,
    verify_contract,
    verify_prelocked,
    verify_results,
    verify_runtime_reproduction,
)


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--root",type=Path,default=Path(".")); parser.add_argument("--config",type=Path,default=Path("configs/retrieval/kb_v1_r0_r1.json"))
    sub=parser.add_subparsers(dest="command",required=True)
    for name in ("verify-contract","build-corpus","select-r1","verify-prelocked","finalize","audit-dev-selection","finalize-review-correction","verify-results","verify-runtime-reproduction"): sub.add_parser(name)
    locked=sub.add_parser("run-locked"); locked.add_argument("--run-label",required=True,choices=("primary","reproducibility_rerun"))
    args=parser.parse_args(); root=args.root.resolve(); config=(root/args.config).resolve() if not args.config.is_absolute() else args.config.resolve()
    actions={"verify-contract":verify_contract,"build-corpus":build,"select-r1":select_r1,"verify-prelocked":verify_prelocked,"finalize":finalize,"audit-dev-selection":audit_dev_selection,"finalize-review-correction":finalize_review_correction,"verify-results":verify_results,"verify-runtime-reproduction":verify_runtime_reproduction}
    result=run_locked(root,config,args.run_label) if args.command=="run-locked" else actions[args.command](root,config)
    print(json.dumps(result,indent=2,sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
