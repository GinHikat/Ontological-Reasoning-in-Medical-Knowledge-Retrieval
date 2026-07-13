#!/usr/bin/env python3
"""Run the frozen baseline_hybrid track."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Frozen baseline_hybrid (reference / fallback / comparison)."
    )
    parser.add_argument(
        "--model",
        default="vihealthbert",
        help="Generic NER backbone weights (default: vihealthbert).",
    )
    parser.add_argument("--samples", type=int, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output" / "baseline_hybrid",
    )
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--no-trace", action="store_true")
    args = parser.parse_args()

    from modules.evaluation.run_pipeline import main as run_main

    argv = [
        "run_pipeline",
        "--pipeline",
        "baseline_hybrid",
        "--model",
        args.model,
        "--output-dir",
        str(args.output_dir),
    ]
    if args.samples is not None:
        argv.extend(["--samples", str(args.samples)])
    if args.input_dir is not None:
        argv.extend(["--input-dir", str(args.input_dir)])
    if args.no_trace:
        argv.append("--no-trace")

    sys.argv = argv
    run_main()


if __name__ == "__main__":
    main()
