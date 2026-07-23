"""Repository-root wrapper for the W1-001 Banking77 CLI."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from payresolve_ai.data.banking77_cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

