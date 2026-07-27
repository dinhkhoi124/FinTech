"""Repository-local wrapper for the W1-003 semantic baseline CLI."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from payresolve_ai.baselines.semantic_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
