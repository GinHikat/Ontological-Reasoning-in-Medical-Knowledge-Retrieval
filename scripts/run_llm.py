#!/usr/bin/env python3
"""Run the schema-aware LLM track (diagnostic OpenRouter or competition localhost)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Representative 10-doc benchmark (shared with archived reduced runner)
BENCHMARK_10 = [
    "55",
    "31",
    "3",
    "41",
    "75",
    "2",
    "36",
    "37",
    "20",
    "24",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "LLM direction: one schema-aware extraction call + local ontology. "
            "diagnostic=OpenRouter (not competition-compliant); "
            "competition=self-hosted ≤9B."
        )
    )
    parser.add_argument(
        "--mode",
        choices=["diagnostic", "competition"],
        default="competition",
        help="diagnostic uses OpenRouter; competition requires localhost ≤9B.",
    )
    parser.add_argument("--benchmark-10", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--docs", nargs="*", default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--microbatch-size", type=int, default=None)
    args = parser.parse_args()

    from modules.pipelines.llm.extractor import mode_banner

    print(mode_banner(args.mode))

    if args.mode == "diagnostic":
        from modules.external.openrouter_client import OpenRouterClient, load_dotenv_file
        from modules.external.reduced_teacher_pipeline import (
            ReducedTeacherPipeline,
            config_from_env,
            list_all_doc_ids,
        )

        load_dotenv_file()
        cfg = config_from_env(args.output_dir)
        if args.microbatch_size is not None:
            cfg.microbatch_size = max(1, min(2, args.microbatch_size))
        if args.benchmark_10:
            doc_ids = list(BENCHMARK_10)
        elif args.full:
            doc_ids = list_all_doc_ids(cfg.test_dir)
        elif args.docs:
            doc_ids = [
                str(d).replace(".txt", "").replace(".json", "") for d in args.docs
            ]
        else:
            parser.error("diagnostic mode requires --benchmark-10, --full, or --docs")

        print(f"extractor={cfg.extractor_model}")
        print(f"judge={cfg.judge_model}")
        print(f"docs={len(doc_ids)} -> {doc_ids}")
        print(f"output={cfg.output_dir}")

        with OpenRouterClient(
            cache_dir=cfg.cache_root / "extraction",
            max_concurrency=1,
            budget_usd=cfg.budget_usd,
            usage_log_path=cfg.output_dir / "traces" / "usage_ledger.jsonl",
        ) as client:
            pipe = ReducedTeacherPipeline(client, cfg)
            summary = pipe.run(doc_ids)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    print(
        "Competition mode uses the same prompts/schemas/alignment/ontology as "
        "diagnostic, but must call a localhost model ≤9B.\n"
        "Serve a local model (scripts/serve_v9_qwen*.sh), then wire the localhost "
        "backend under modules/pipelines/llm/.\n"
        "Do not use OpenRouter for competition submissions."
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
