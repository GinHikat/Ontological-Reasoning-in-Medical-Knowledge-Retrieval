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
        description="Run an active clinical track (baseline_hybrid / ner / llm)."
    )
    parser.add_argument(
        "--pipeline",
        choices=available_pipelines(),
        default="baseline_hybrid",
        help="Active track to run (historical v5–v10 names are archived).",
    )
    parser.add_argument(
        "--model",
        choices=NER_MODEL_CHOICES,
        default="vihealthbert",
        help="Base NER model used by baseline_hybrid (ignored by llm).",
    )
    parser.add_argument(
        "--version-name",
        type=str,
        default=None,
        help=(
            "Output version folder under output/ (default: --pipeline name). "
            "Usually omit this."
        ),
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "v_dataset" / "var" / "test",
        help="Directory containing .txt clinical notes.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="Root folder where version/run directories are saved.",
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
            "Overrides the version/run structure; use only for flat submission exports."
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
        help="Enable writing step-by-step trace logging files under run/trace/.",
    )
    parser.add_argument(
        "--no-trace",
        action="store_false",
        dest="trace",
        help="Disable writing step-by-step trace logging files.",
    )
    return parser.parse_args()


def _next_run_name(version_dir: Path) -> str:
    """Return the next `runN` name within `version_dir` (run1, run2, ...)."""
    existing: list[int] = []
    if version_dir.exists():
        for child in version_dir.iterdir():
            if child.is_dir() and child.name.startswith("run"):
                suffix = child.name[len("run") :]
                if suffix.isdigit():
                    existing.append(int(suffix))
    return f"run{(max(existing) + 1) if existing else 1}"


def _resolve_run_dirs(
    args: argparse.Namespace,
) -> tuple[Path, Path | None, bool]:
    """Return (submission_dir, trace_dir, structured).

    structured=True means the version/run layout with submission/ and trace/.
    Flat ``--output-dir`` still nests ``submission/``, ``trace/``, and (for v9)
    ``base_v7_snapshot/`` under that root so exports match the brief layout.
    """
    if args.output_dir is not None:
        submission_dir = args.output_dir / "submission"
        trace_dir = args.output_dir / "trace" if args.trace else None
        return submission_dir, trace_dir, True

    version_name = args.version_name or args.pipeline
    version_dir = args.output_root / version_name

    if args.run_name:
        run_dir = version_dir / args.run_name
    elif args.samples is not None:
        run_dir = version_dir / f"samples_{args.samples}"
    else:
        run_dir = version_dir / _next_run_name(version_dir)

    submission_dir = run_dir / "submission"
    trace_dir = run_dir / "trace" if args.trace else None
    return submission_dir, trace_dir, True


def main() -> None:
    from modules.components.formatting.competition_json import CompetitionJSONFormatter
    from modules.core.schemas import Document
    from modules.pipelines.factory import build_pipeline

    args = parse_args()

    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")

    submission_dir, trace_dir, structured = _resolve_run_dirs(args)
    submission_dir.mkdir(parents=True, exist_ok=True)
    if trace_dir is not None:
        trace_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(args.input_dir.glob("*.txt"))
    if args.samples is not None:
        files = files[: args.samples]

    print(f"Building pipeline: {args.pipeline} (model={args.model})")
    pipeline = build_pipeline(args.pipeline, model_name=args.model)
    formatter = CompetitionJSONFormatter(
        include_empty_candidates_for_linkable_types=True
    )

    print(f"Processing {len(files)} files from {args.input_dir}")
    print(f"Submission -> {submission_dir}")
    if trace_dir is not None:
        print(f"Traces     -> {trace_dir}")

    for file_path in tqdm(files, desc=f"Running {args.pipeline}/{args.model}"):
        text = file_path.read_text(encoding="utf-8")
        document = Document(doc_id=file_path.stem, text=text)
        entities = pipeline.process_document(document)
        output = formatter.format(entities)

        out_json_path = submission_dir / f"{file_path.stem}.json"
        indent = None if args.indent == 0 else args.indent
        out_json_path.write_text(
            json.dumps(output, ensure_ascii=False, indent=indent),
            encoding="utf-8",
        )

        if args.trace and "trace_txt" in document.metadata:
            assert trace_dir is not None
            trace_path = trace_dir / f"{file_path.stem}_trace.txt"
            trace_path.write_text(
                document.metadata["trace_txt"],
                encoding="utf-8",
            )

    print(f"Done. Submission written to {submission_dir}")
    if args.trace and trace_dir is not None:
        print(f"Traces written to {trace_dir}")


if __name__ == "__main__":
    main()
