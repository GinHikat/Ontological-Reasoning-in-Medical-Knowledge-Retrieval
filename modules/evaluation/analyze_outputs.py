from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TARGET_TYPES = [
    "CHẨN_ĐOÁN",
    "THUỐC",
    "TRIỆU_CHỨNG",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
]
LINKABLE = {"CHẨN_ĐOÁN", "THUỐC"}
ASSERTION_ELIGIBLE = {"CHẨN_ĐOÁN", "THUỐC", "TRIỆU_CHỨNG"}
CONTEXT_CHARS = 50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose competition JSON outputs without gold labels."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "v_dataset" / "var" / "test",
        help="Directory of original .txt notes.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory of predicted .json files.",
    )
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=PROJECT_ROOT / "analysis",
        help="Where to write TSV/JSON summaries.",
    )
    parser.add_argument(
        "--run-name",
        type=str,
        default=None,
        help="Name used for analysis artifacts (default: output-dir name).",
    )
    return parser.parse_args()


def _load_entities(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {path}")
    return data


def _context(text: str, start: int, end: int) -> tuple[str, str]:
    left = text[max(0, start - CONTEXT_CHARS) : start]
    right = text[end : min(len(text), end + CONTEXT_CHARS)]
    return left.replace("\n", " "), right.replace("\n", " ")


def _span_issues(text: str, entities: list[dict[str, Any]]) -> dict[str, int]:
    issues = Counter()
    seen: dict[tuple[int, int], int] = defaultdict(int)
    spans: list[tuple[int, int, int]] = []

    for idx, ent in enumerate(entities):
        pos = ent.get("position") or [None, None]
        if not isinstance(pos, list) or len(pos) != 2:
            issues["invalid_start_end"] += 1
            continue
        start, end = pos
        if not isinstance(start, int) or not isinstance(end, int):
            issues["invalid_start_end"] += 1
            continue
        if start < 0 or end < 0 or start > end or end > len(text):
            issues["invalid_start_end"] += 1
            continue
        if start == end:
            issues["zero_length"] += 1
        extracted = text[start:end]
        if extracted != ent.get("text", ""):
            issues["text_mismatch"] += 1
        seen[(start, end)] += 1
        spans.append((start, end, idx))

    for count in seen.values():
        if count > 1:
            issues["duplicate_exact_spans"] += count - 1

    for i, (s1, e1, _) in enumerate(spans):
        for s2, e2, _ in spans[i + 1 :]:
            if s1 == s2 and e1 == e2:
                continue
            overlap = max(0, min(e1, e2) - max(s1, s2))
            if overlap <= 0:
                continue
            issues["overlapping_spans"] += 1
            if (s1 <= s2 and e2 <= e1) or (s2 <= s1 and e1 <= e2):
                issues["nested_spans"] += 1

    return dict(issues)


def resolve_submission_dir(output_dir: Path) -> Path:
    """Accept either a run folder (`.../runN`) or a flat/submission JSON folder."""
    submission = output_dir / "submission"
    if submission.is_dir():
        return submission
    return output_dir


def analyze_run(
    input_dir: Path,
    output_dir: Path,
    analysis_dir: Path,
    run_name: str,
) -> dict[str, Any]:
    submission_dir = resolve_submission_dir(output_dir)
    json_files = sorted(submission_dir.glob("*.json"))
    type_counts: Counter[str] = Counter()
    assertion_counts: Counter[str] = Counter()
    diag_with = diag_without = 0
    drug_with = drug_without = 0
    eligible_no_assertion = 0
    total_entities = 0
    span_issue_totals: Counter[str] = Counter()
    entity_rows: list[dict[str, Any]] = []

    for json_path in json_files:
        stem = json_path.stem
        txt_path = input_dir / f"{stem}.txt"
        text = txt_path.read_text(encoding="utf-8") if txt_path.exists() else ""
        entities = _load_entities(json_path)
        total_entities += len(entities)
        span_issue_totals.update(_span_issues(text, entities))

        for ent in entities:
            etype = str(ent.get("type", ""))
            type_counts[etype] += 1
            candidates = ent.get("candidates") or []
            assertions = ent.get("assertions") or []
            for a in assertions:
                assertion_counts[str(a)] += 1
            if etype == "CHẨN_ĐOÁN":
                if candidates:
                    diag_with += 1
                else:
                    diag_without += 1
            if etype == "THUỐC":
                if candidates:
                    drug_with += 1
                else:
                    drug_without += 1
            if etype in ASSERTION_ELIGIBLE and not assertions:
                eligible_no_assertion += 1

            pos = ent.get("position") or [None, None]
            start = int(pos[0]) if isinstance(pos[0], int) else -1
            end = int(pos[1]) if isinstance(pos[1], int) else -1
            left, right = ("", "")
            if text and start >= 0 and end >= start:
                left, right = _context(text, start, end)

            entity_rows.append(
                {
                    "file": stem,
                    "start": start,
                    "end": end,
                    "text": ent.get("text", ""),
                    "type": etype,
                    "candidates": "|".join(str(c) for c in candidates),
                    "assertions": "|".join(str(a) for a in assertions),
                    "left_context": left,
                    "right_context": right,
                }
            )

    n_files = len(json_files)
    summary: dict[str, Any] = {
        "run_name": run_name,
        "output_dir": str(output_dir),
        "input_dir": str(input_dir),
        "num_files": n_files,
        "total_entities": total_entities,
        "avg_entities_per_file": (total_entities / n_files) if n_files else 0.0,
        "count_by_type": {t: type_counts.get(t, 0) for t in TARGET_TYPES},
        "other_types": {
            k: v for k, v in type_counts.items() if k not in TARGET_TYPES
        },
        "diagnosis": {
            "total": type_counts.get("CHẨN_ĐOÁN", 0),
            "with_candidates": diag_with,
            "without_candidates": diag_without,
        },
        "drug": {
            "total": type_counts.get("THUỐC", 0),
            "with_candidates": drug_with,
            "without_candidates": drug_without,
        },
        "assertions": {
            "isHistorical": assertion_counts.get("isHistorical", 0),
            "isNegated": assertion_counts.get("isNegated", 0),
            "isFamily": assertion_counts.get("isFamily", 0),
            "eligible_with_no_assertion": eligible_no_assertion,
        },
        "span_quality": {
            "text_mismatch": span_issue_totals.get("text_mismatch", 0),
            "invalid_start_end": span_issue_totals.get("invalid_start_end", 0),
            "zero_length": span_issue_totals.get("zero_length", 0),
            "duplicate_exact_spans": span_issue_totals.get("duplicate_exact_spans", 0),
            "overlapping_spans": span_issue_totals.get("overlapping_spans", 0),
            "nested_spans": span_issue_totals.get("nested_spans", 0),
        },
    }

    analysis_dir.mkdir(parents=True, exist_ok=True)
    summary_path = analysis_dir / f"{run_name}_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    tsv_path = analysis_dir / f"{run_name}_entities.tsv"
    headers = [
        "file",
        "start",
        "end",
        "text",
        "type",
        "candidates",
        "assertions",
        "left_context",
        "right_context",
    ]
    with tsv_path.open("w", encoding="utf-8") as f:
        f.write("\t".join(headers) + "\n")
        for row in entity_rows:
            values = []
            for h in headers:
                val = str(row.get(h, "")).replace("\t", " ").replace("\n", " ")
                values.append(val)
            f.write("\t".join(values) + "\n")

    _print_summary(summary, summary_path, tsv_path)
    return summary


def _print_summary(summary: dict[str, Any], summary_path: Path, tsv_path: Path) -> None:
    print(f"Number of files: {summary['num_files']}")
    print(f"Total predicted entities: {summary['total_entities']}")
    print(f"Average entities per file: {summary['avg_entities_per_file']:.2f}")
    print("\nCount by type:")
    for t, c in summary["count_by_type"].items():
        print(f"  {t}: {c}")

    print("\nFor CHẨN_ĐOÁN:")
    d = summary["diagnosis"]
    print(f"  total: {d['total']}")
    print(f"  with candidates: {d['with_candidates']}")
    print(f"  without candidates: {d['without_candidates']}")

    print("\nFor THUỐC:")
    drug = summary["drug"]
    print(f"  total: {drug['total']}")
    print(f"  with candidates: {drug['with_candidates']}")
    print(f"  without candidates: {drug['without_candidates']}")

    print("\nAssertions:")
    a = summary["assertions"]
    print(f"  total isHistorical: {a['isHistorical']}")
    print(f"  total isNegated: {a['isNegated']}")
    print(f"  total isFamily: {a['isFamily']}")
    print(f"  eligible entities with no assertion: {a['eligible_with_no_assertion']}")

    print("\nSpan quality checks:")
    sq = summary["span_quality"]
    print(f"  text does not equal original_text[start:end]: {sq['text_mismatch']}")
    print(f"  invalid start/end: {sq['invalid_start_end']}")
    print(f"  zero-length spans: {sq['zero_length']}")
    print(f"  duplicate exact spans: {sq['duplicate_exact_spans']}")
    print(f"  overlapping spans: {sq['overlapping_spans']}")
    print(f"  nested spans: {sq['nested_spans']}")

    print(f"\nWrote {summary_path}")
    print(f"Wrote {tsv_path}")


def main() -> None:
    args = parse_args()
    if not args.output_dir.exists():
        raise FileNotFoundError(f"Output directory not found: {args.output_dir}")
    run_name = args.run_name or args.output_dir.name
    analyze_run(args.input_dir, args.output_dir, args.analysis_dir, run_name)


if __name__ == "__main__":
    main()
