#!/usr/bin/env python3
"""Run openrouter_schema_teacher_reduced (EXTERNAL_API_DIAGNOSTIC_ONLY)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.external.openrouter_client import OpenRouterClient, load_dotenv_file
from modules.external.reduced_teacher_pipeline import (
    DEFAULT_EXTRACTOR,
    DEFAULT_JUDGE,
    config_from_env,
    list_all_doc_ids,
)


# Representative 10-doc benchmark set (lengths / schema-audit roles)
BENCHMARK_10 = [
    "55",  # short/simple
    "31",  # short/simple
    "3",  # long
    "41",  # long
    "75",  # procedure-heavy
    "2",  # procedure-heavy
    "36",  # lab-heavy
    "37",  # drug-heavy
    "20",  # symptom/diagnosis-heavy
    "24",  # high-disagreement / paid-pilot reference
]


def main() -> None:
    load_dotenv_file()
    parser = argparse.ArgumentParser(
        description="Reduced one-extractor OpenRouter teacher"
    )
    parser.add_argument(
        "--docs",
        nargs="*",
        default=None,
        help="Document IDs (default: all or --benchmark-10)",
    )
    parser.add_argument(
        "--benchmark-10",
        action="store_true",
        help="Run the fixed 10-document benchmark set",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run all 100 documents",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override output directory",
    )
    parser.add_argument(
        "--microbatch-size",
        type=int,
        default=None,
        help="1 (default) or 2",
    )
    args = parser.parse_args()

    cfg = config_from_env(args.output_dir)
    if args.microbatch_size is not None:
        cfg.microbatch_size = max(1, min(2, args.microbatch_size))

    if args.benchmark_10:
        doc_ids = list(BENCHMARK_10)
    elif args.full:
        doc_ids = list_all_doc_ids(cfg.test_dir)
    elif args.docs:
        doc_ids = [str(d).replace(".txt", "").replace(".json", "") for d in args.docs]
    else:
        parser.error("Specify --benchmark-10, --full, or --docs")

    print("EXTERNAL_API_DIAGNOSTIC_ONLY")
    print(f"extractor={cfg.extractor_model}")
    print(f"judge={cfg.judge_model}")
    print(f"docs={len(doc_ids)} -> {doc_ids}")
    print(f"output={cfg.output_dir}")
    print(f"cache={cfg.cache_root}")

    with OpenRouterClient(
        cache_dir=cfg.cache_root / "extraction",
        max_concurrency=1,
        budget_usd=cfg.budget_usd,
        usage_log_path=cfg.output_dir / "traces" / "usage_ledger.jsonl",
    ) as client:
        from modules.external.reduced_teacher_pipeline import ReducedTeacherPipeline

        pipe = ReducedTeacherPipeline(client, cfg)
        summary = pipe.run(doc_ids)
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    # Defaults echoed for operators
    _ = (DEFAULT_EXTRACTOR, DEFAULT_JUDGE)
    main()
