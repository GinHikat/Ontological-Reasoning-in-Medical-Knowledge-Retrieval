from __future__ import annotations

"""Enrich v9 traces with offline LLM cache details for each addition."""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.components.postprocessing.llm_recall import document_sha256


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", type=Path, default=PROJECT_ROOT / "v_dataset" / "var" / "test")
    p.add_argument("--cache-dir", type=Path, default=PROJECT_ROOT / "cache" / "v9_llm_recall")
    p.add_argument("--trace-dir", type=Path, required=True)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="If set, write enriched copies here; else append in-place.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.output_dir or args.trace_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    cache_by_sha = {}
    for path in args.cache_dir.glob("*.json"):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        cache_by_sha[data["document_sha256"]] = data

    n = 0
    for txt_path in sorted(args.input_dir.glob("*.txt")):
        text = txt_path.read_text(encoding="utf-8")
        sha = document_sha256(text)
        cache = cache_by_sha.get(sha)
        trace_path = args.trace_dir / f"{txt_path.stem}_trace.txt"
        if not trace_path.exists():
            continue
        body = trace_path.read_text(encoding="utf-8")
        # Avoid double-enrichment.
        if "LLM CACHE DETAIL" in body:
            out_path = out_dir / trace_path.name
            if out_path != trace_path:
                out_path.write_text(body, encoding="utf-8")
            n += 1
            continue

        lines = ["", "=" * 80, "LLM CACHE DETAIL", "=" * 80]
        if cache is None:
            lines.append(f"  cache miss for sha256={sha}")
        else:
            lines.append(f"  document_sha256: {sha}")
            lines.append(f"  model: {cache.get('model')}")
            lines.append(f"  prompt_versions: {cache.get('prompt_versions')}")
            lines.append(f"  generation_settings: {cache.get('generation_settings')}")
            lines.append(f"  repair_used: {cache.get('repair_used')}")
            lines.append(f"  parse_failures: {cache.get('parse_failures')}")
            lines.append("  raw_proposals:")
            for p in cache.get("parsed_proposals") or []:
                lines.append(f"    - {p}")
            lines.append("  alignment_results:")
            for a in cache.get("alignment_results") or []:
                lines.append(
                    f"    - id={a.get('proposal_id')} status={a.get('status')} "
                    f"line={a.get('line_id')} type={a.get('type')} text={a.get('text')!r} "
                    f"span=[{a.get('start')}:{a.get('end')}] detail={a.get('detail')}"
                )
            lines.append("  verifier_decisions:")
            for d in cache.get("verifier_decisions") or []:
                lines.append(f"    - {d}")
            lines.append("  final_accepted_candidates:")
            for c in cache.get("final_accepted_candidates") or []:
                lines.append(f"    - {c}")
            diag = cache.get("diagnostics") or {}
            if diag.get("type_disagreements"):
                lines.append("  type_disagreements:")
                for item in diag["type_disagreements"]:
                    lines.append(f"    - {item}")
            if diag.get("verifier_rejected"):
                lines.append("  verifier_rejected:")
                for item in diag["verifier_rejected"]:
                    lines.append(f"    - {item}")

        enriched = body.rstrip() + "\n" + "\n".join(lines) + "\n"
        (out_dir / trace_path.name).write_text(enriched, encoding="utf-8")
        n += 1

    print(f"Enriched {n} traces -> {out_dir}")


if __name__ == "__main__":
    main()
