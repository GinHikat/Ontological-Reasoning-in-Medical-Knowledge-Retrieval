from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tqdm import tqdm

# Allow running as: python modules/evaluation/run_pipeline.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    from modules.pipelines.factory import NER_MODEL_CHOICES, available_pipelines

    parser = argparse.ArgumentParser(
        description="Run a versioned clinical NER/linking pipeline."
    )
    parser.add_argument(
        "--pipeline",
        choices=available_pipelines(),
        default="v5_refactored",
        help="Pipeline implementation to run.",
    )
    parser.add_argument(
        "--model",
        choices=NER_MODEL_CHOICES,
        default="vihealthbert",
        help="Base NER model; used to namespace outputs under output/<model>/.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "var" / "test",
        help="Directory containing .txt clinical notes.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="Root folder where model/run directories are saved.",
    )
    parser.add_argument(
        "--run-name",
        type=str,
        default=None,
        help="Optional explicit run folder name (e.g. run1). Default auto-increments.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Exact directory where .json outputs will be written. "
            "Overrides the model/run structure; use only for flat submission exports."
        ),
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=None,
        help="Optional limit for quick smoke tests.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=4,
        help="JSON indentation level. Use 0 for compact JSON.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        default=True,
        help="Enable writing step-by-step trace logging files next to JSON output.",
    )
    parser.add_argument(
        "--no-trace",
        action="store_false",
        dest="trace",
        help="Disable writing step-by-step trace logging files.",
    )
    return parser.parse_args()


def _next_run_name(model_dir: Path) -> str:
    """Return the next `runN` name within `model_dir` (run1, run2, ...)."""
    existing: list[int] = []
    if model_dir.exists():
        for child in model_dir.iterdir():
            if child.is_dir() and child.name.startswith("run"):
                suffix = child.name[len("run") :]
                if suffix.isdigit():
                    existing.append(int(suffix))
    return f"run{(max(existing) + 1) if existing else 1}"


def main() -> None:
    from modules.components.formatting.competition_json import CompetitionJSONFormatter
    from modules.core.schemas import Document
    from modules.pipelines.factory import build_pipeline

    args = parse_args()

    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")

    if args.output_dir is not None:
        output_dir = args.output_dir
    else:
        pipeline_dir = args.output_root / args.pipeline
        if args.run_name:
            output_dir = pipeline_dir / args.model / args.run_name
        elif args.samples is not None:
            output_dir = pipeline_dir / f"{args.model}_samples_{args.samples}"
        else:
            model_dir = pipeline_dir / args.model
            run_name = _next_run_name(model_dir)
            output_dir = model_dir / run_name
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(args.input_dir.glob("*.txt"))
    if args.samples is not None:
        files = files[: args.samples]

    print(f"Building pipeline: {args.pipeline} (model={args.model})")
    pipeline = build_pipeline(args.pipeline, model_name=args.model)
    formatter = CompetitionJSONFormatter(
        include_empty_candidates_for_linkable_types=True
    )

    print(f"Processing {len(files)} files from {args.input_dir}")
    print(f"Outputs -> {output_dir}")
    for file_path in tqdm(files, desc=f"Running {args.pipeline}/{args.model}"):
        text = file_path.read_text(encoding="utf-8")
        document = Document(doc_id=file_path.stem, text=text)
        entities = pipeline.process_document(document)
        output = formatter.format(entities)

        out_json_path = output_dir / f"{file_path.stem}.json"
        indent = None if args.indent == 0 else args.indent
        out_json_path.write_text(
            json.dumps(output, ensure_ascii=False, indent=indent),
            encoding="utf-8",
        )

        if args.trace and "trace_txt" in document.metadata:
            trace_dir = output_dir.parent / f"{output_dir.name}_traces"
            trace_dir.mkdir(parents=True, exist_ok=True)
            trace_path = trace_dir / f"{file_path.stem}_trace.txt"
            trace_path.write_text(
                document.metadata["trace_txt"],
                encoding="utf-8",
            )

    print(f"Done. Outputs written to {output_dir}")
    if args.trace:
        print(f"Traces written to {output_dir.parent / f'{output_dir.name}_traces'}")


if __name__ == "__main__":
    main()
