#!/usr/bin/env python3
"""DEPRECATED — use ``python scripts/run_llm.py --mode diagnostic ...`` instead."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.argv = ["run_llm.py", "--mode", "diagnostic", *sys.argv[1:]]
print(
    "NOTE: scripts/run_openrouter_reduced.py is deprecated; "
    "prefer: python scripts/run_llm.py --mode diagnostic ...",
    file=sys.stderr,
)
runpy.run_path(str(ROOT / "scripts" / "run_llm.py"), run_name="__main__")
