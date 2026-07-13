#!/usr/bin/env python3
"""Run the task-specific NER track (five labels + NONE)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Task-specific NER direction: direct competition labels + NONE, "
            "shared ontology linking."
        )
    )
    parser.add_argument(
        "--backend",
        choices=["gliner", "span_classifier", "token_classifier", "clinical_lm"],
        default="token_classifier",
    )
    parser.add_argument("--checkpoint", type=str, default=None)
    parser.add_argument("--samples", type=int, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output" / "ner",
    )
    parser.add_argument("--train-notes", action="store_true")
    args = parser.parse_args()

    if args.train_notes:
        from modules.pipelines.ner.training import training_notes

        print(training_notes())
        return

    # Pipeline build will raise NotImplementedError until a model is wired.
    from modules.pipelines.ner import build_ner_pipeline

    try:
        build_ner_pipeline(backend=args.backend, checkpoint=args.checkpoint)
    except TypeError:
        build_ner_pipeline()

    from modules.evaluation.run_pipeline import main as run_main

    argv = [
        "run_pipeline",
        "--pipeline",
        "ner",
        "--output-dir",
        str(args.output_dir),
    ]
    if args.samples is not None:
        argv.extend(["--samples", str(args.samples)])
    sys.argv = argv
    run_main()


if __name__ == "__main__":
    main()
