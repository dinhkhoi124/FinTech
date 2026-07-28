"""Repository-root wrapper for W2-002 gold mapping validation."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from payresolve_ai.evaluation.gold_mapping_cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
