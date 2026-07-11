#!/usr/bin/env python3
"""Preview / analyze v10 LLM conflict-resolution replacements.

Offline preview (no NER/SapBERT): uses existing v7 snapshot JSON + v9 LLM cache
to count high-confidence rule hits before a full pipeline run.

Post-run mode: aggregate diagnostics from output/v10_*/trace metadata via
replaying submission vs base_v7_snapshot (span diffs).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.components.postprocessing.llm_conflict_resolution import (
    OverlapHit,
    classify_one_to_one,
    decision_to_dict,
    find_overlapping_v7,
)
from modules.components.postprocessing.llm_recall import (
    document_sha256,
    load_cache_record,
)
from modules.core.schemas import FinalEntity, Span


def _load_submission_entities(path: Path) -> list[FinalEntity]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    entities: list[FinalEntity] = []
    for item in raw:
        start, end = item["position"]
        entities.append(
            FinalEntity(
                text=item["text"],
                type=item["type"],
                span=Span(int(start), int(end)),
                candidates=list(item.get("candidates") or []),
                assertions=list(item.get("assertions") or []),
            )
        )
    return entities


def preview_document(
    text: str,
    frozen_v7: list[FinalEntity],
    cache_dir: Path,
) -> dict[str, Any]:
    sha = document_sha256(text)
    record = load_cache_record(cache_dir, sha)
    out: dict[str, Any] = {
        "sha256": sha,
        "cache_hit": record is not None,
        "frozen_v7_count": len(frozen_v7),
        "replacements": [],
        "multi_rejected": 0,
        "rule_miss": 0,
        "no_overlap": 0,
    }
    if record is None:
        return out

    claimed_v7: set[int] = set()
    for cand in record.get("final_accepted_candidates") or []:
        text_c = str(cand.get("text", ""))
        ent_type = str(cand.get("type", ""))
        start = cand.get("start")
        end = cand.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if text[start:end] != text_c:
            continue
        overlaps = find_overlapping_v7(start, end, frozen_v7)
        if not overlaps:
            out["no_overlap"] += 1
            continue
        if len(overlaps) != 1:
            out["multi_rejected"] += 1
            continue
        v7_index, v7_entity = overlaps[0]
        assert v7_entity.span.start is not None and v7_entity.span.end is not None
        if v7_index in claimed_v7:
            continue
        hit = OverlapHit(
            llm_text=text_c,
            llm_type=ent_type,
            llm_start=start,
            llm_end=end,
            v7_index=v7_index,
            v7_text=v7_entity.text,
            v7_type=v7_entity.type,
            v7_start=int(v7_entity.span.start),
            v7_end=int(v7_entity.span.end),
        )
        decision = classify_one_to_one(hit)
        if decision is None:
            out["rule_miss"] += 1
            continue
        claimed_v7.add(v7_index)
        out["replacements"].append(decision_to_dict(decision))
    return out


def run_preview(args: argparse.Namespace) -> int:
    input_dir = Path(args.input_dir)
    snapshot_dir = Path(args.base_v7_snapshot)
    cache_dir = Path(args.cache_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(input_dir.glob("*.txt"))
    if args.samples:
        files = files[: args.samples]

    rows: list[dict[str, Any]] = []
    cat_counts: Counter[str] = Counter()
    totals = Counter()

    for path in files:
        text = path.read_text(encoding="utf-8")
        snap_path = snapshot_dir / f"{path.stem}.json"
        if not snap_path.exists():
            print(f"WARN missing snapshot: {snap_path}")
            continue
        frozen = _load_submission_entities(snap_path)
        result = preview_document(text, frozen, cache_dir)
        totals["docs"] += 1
        totals["cache_hit"] += int(result["cache_hit"])
        totals["multi_rejected"] += result["multi_rejected"]
        totals["rule_miss"] += result["rule_miss"]
        totals["replacements"] += len(result["replacements"])
        for rep in result["replacements"]:
            cat_counts[rep["category"]] += 1
            rows.append({"file": path.stem, **rep})

    tsv_path = out_dir / "v10_replacement_preview.tsv"
    fields = [
        "file",
        "category",
        "reason",
        "start",
        "end",
        "text",
        "type",
        "existing_start",
        "existing_end",
        "existing_text",
        "existing_type",
    ]
    with tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    report = out_dir / "v10_conflict_preview_report.md"
    report.write_text(
        "\n".join(
            [
                "# v10 conflict-resolution preview (offline)",
                "",
                f"- docs: {totals['docs']}",
                f"- cache hits: {totals['cache_hit']}",
                f"- rule-based replacement candidates: {totals['replacements']}",
                f"- category counts: A={cat_counts['A']} B={cat_counts['B']} "
                f"C={cat_counts['C']} D={cat_counts['D']}",
                f"- multi-v7 overlaps rejected: {totals['multi_rejected']}",
                f"- overlap rule misses: {totals['rule_miss']}",
                "",
                "Note: post-link gates (RxNorm/ICD lexical + isNegated) are NOT "
                "applied in this offline preview.",
                "",
                f"TSV: `{tsv_path}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(report.read_text(encoding="utf-8"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        default=str(ROOT / "v_dataset" / "var" / "test"),
    )
    parser.add_argument(
        "--base-v7-snapshot",
        default=str(ROOT / "output" / "v9_llm_recall" / "base_v7_snapshot"),
        help="Frozen v7 JSON dir (preview uses v9 same-run snapshot if present)",
    )
    parser.add_argument(
        "--cache-dir",
        default=str(ROOT / "cache" / "v9_llm_recall"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "analysis"),
    )
    parser.add_argument("--samples", type=int, default=0)
    args = parser.parse_args()
    return run_preview(args)


if __name__ == "__main__":
    raise SystemExit(main())
