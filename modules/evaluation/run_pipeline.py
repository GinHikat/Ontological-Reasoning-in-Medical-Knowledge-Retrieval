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
    from modules.pipelines.factory import available_pipelines

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
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "var" / "test",
        help="Directory containing .txt clinical notes.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="Directory where .json outputs will be written.",
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
    return parser.parse_args()


def main() -> None:
    from modules.components.formatting.competition_json import CompetitionJSONFormatter
    from modules.core.schemas import Document
    from modules.pipelines.factory import build_pipeline

    args = parse_args()

    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(args.input_dir.glob("*.txt"))
    if args.samples is not None:
        files = files[: args.samples]

    print(f"Building pipeline: {args.pipeline}")
    pipeline = build_pipeline(args.pipeline)
    formatter = CompetitionJSONFormatter(
        include_empty_candidates_for_linkable_types=True
    )

    print(f"Processing {len(files)} files from {args.input_dir}")
    for file_path in tqdm(files, desc=f"Running {args.pipeline}"):
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

    print(f"Done. Outputs written to {output_dir}")


if __name__ == "__main__":
    main()
