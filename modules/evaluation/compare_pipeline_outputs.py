from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.evaluation.analyze_outputs import resolve_submission_dir  # noqa: E402

CONTEXT = 60
OFFICIAL_TYPES = {
    "CHẨN_ĐOÁN",
    "THUỐC",
    "TÊN_XÉT_NGHIỆM",
    "TRIỆU_CHỨNG",
    "KẾT_QUẢ_XÉT_NGHIỆM",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Strict pipeline output comparison with hard invariants."
    )
    p.add_argument("--baseline-dir", type=Path, required=True)
    p.add_argument("--candidate-dir", type=Path, required=True)
    p.add_argument("--input-dir", type=Path, default=PROJECT_ROOT / "data" / "var" / "test")
    p.add_argument("--baseline-name", type=str, default="v7")
    p.add_argument("--candidate-name", type=str, default="v8")
    p.add_argument(
        "--mode",
        choices=["strict_identity", "candidate_integrity"],
        default="candidate_integrity",
        help=(
            "strict_identity: every field must match. "
            "candidate_integrity: only THUỐC candidates may differ."
        ),
    )
    p.add_argument("--analysis-dir", type=Path, default=PROJECT_ROOT / "analysis")
    p.add_argument("--export-prefix", type=str, default="v8")
    return p.parse_args()


def _load_map(output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    submission_dir = resolve_submission_dir(output_dir)
    for path in sorted(submission_dir.glob("*.json")):
        result[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _ctx(text: str, start: int, end: int, n: int = CONTEXT) -> tuple[str, str]:
    left = text[max(0, start - n) : start].replace("\n", " ")
    right = text[end : min(len(text), end + n)].replace("\n", " ")
    return left, right


def _write_tsv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write("\t".join(headers) + "\n")
        for row in rows:
            f.write(
                "\t".join(
                    str(row.get(h, "")).replace("\t", " ").replace("\n", " ")
                    for h in headers
                )
                + "\n"
            )


def _entity_identity(e: dict[str, Any]) -> tuple:
    pos = e.get("position") or [None, None]
    return (
        e.get("text", ""),
        pos[0],
        pos[1],
        e.get("type", ""),
        tuple(e.get("assertions") or []),
    )


def compare(args: argparse.Namespace) -> int:
    analysis_dir = args.analysis_dir
    analysis_dir.mkdir(parents=True, exist_ok=True)

    baseline = _load_map(args.baseline_dir)
    candidate = _load_map(args.candidate_dir)

    failures: list[str] = []
    stats = {
        "baseline_files": len(baseline),
        "candidate_files": len(candidate),
        "baseline_entities": 0,
        "candidate_entities": 0,
        "changed_files": 0,
        "changed_entities": 0,
        "changed_text": 0,
        "changed_positions": 0,
        "changed_types": 0,
        "changed_assertions": 0,
        "changed_candidates": 0,
        "changed_diagnosis_candidates": 0,
        "changed_drug_candidates": 0,
        "unchanged_drug_candidates": 0,
        "newly_linked_drugs": 0,
        "newly_unlinked_drugs": 0,
        "changed_linked_drugs": 0,
    }

    type_counts_b: Counter[str] = Counter()
    type_counts_c: Counter[str] = Counter()
    assertion_counts_b: Counter[str] = Counter()
    assertion_counts_c: Counter[str] = Counter()

    changed_drug_rows: list[dict[str, Any]] = []
    newly_linked_rows: list[dict[str, Any]] = []
    changed_linked_rows: list[dict[str, Any]] = []

    all_stems = sorted(set(baseline) | set(candidate))
    if set(baseline.keys()) != set(candidate.keys()):
        only_b = sorted(set(baseline) - set(candidate))
        only_c = sorted(set(candidate) - set(baseline))
        failures.append(
            f"file set mismatch: only_in_baseline={only_b[:10]} "
            f"only_in_candidate={only_c[:10]}"
        )

    for stem in all_stems:
        b_ents = baseline.get(stem, [])
        c_ents = candidate.get(stem, [])
        stats["baseline_entities"] += len(b_ents)
        stats["candidate_entities"] += len(c_ents)

        for e in b_ents:
            type_counts_b[e.get("type", "")] += 1
            for a in e.get("assertions") or []:
                assertion_counts_b[a] += 1
        for e in c_ents:
            type_counts_c[e.get("type", "")] += 1
            for a in e.get("assertions") or []:
                assertion_counts_c[a] += 1

        if len(b_ents) != len(c_ents):
            failures.append(
                f"{stem}: entity count {len(b_ents)} -> {len(c_ents)}"
            )
            stats["changed_files"] += 1
            continue

        text_path = args.input_dir / f"{stem}.txt"
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        file_changed = False

        for idx, (b, c) in enumerate(zip(b_ents, c_ents)):
            b_id = _entity_identity(b)
            c_id = _entity_identity(c)
            b_cand = list(b.get("candidates") or [])
            c_cand = list(c.get("candidates") or [])
            b_type = b.get("type", "")
            c_type = c.get("type", "")

            if b_id != c_id:
                stats["changed_entities"] += 1
                file_changed = True
                if b_id[0] != c_id[0]:
                    stats["changed_text"] += 1
                    failures.append(
                        f"{stem}[{idx}]: text '{b_id[0]}' -> '{c_id[0]}'"
                    )
                if b_id[1] != c_id[1] or b_id[2] != c_id[2]:
                    stats["changed_positions"] += 1
                    failures.append(
                        f"{stem}[{idx}]: position {[b_id[1], b_id[2]]} -> "
                        f"{[c_id[1], c_id[2]]}"
                    )
                if b_id[3] != c_id[3]:
                    stats["changed_types"] += 1
                    failures.append(
                        f"{stem}[{idx}]: type '{b_id[3]}' -> '{c_id[3]}'"
                    )
                if b_id[4] != c_id[4]:
                    stats["changed_assertions"] += 1
                    failures.append(
                        f"{stem}[{idx}]: assertions {list(b_id[4])} -> {list(c_id[4])}"
                    )

            if b_cand != c_cand:
                stats["changed_candidates"] += 1
                file_changed = True
                if b_type == "CHẨN_ĐOÁN" or c_type == "CHẨN_ĐOÁN":
                    stats["changed_diagnosis_candidates"] += 1
                    failures.append(
                        f"{stem}[{idx}]: diagnosis candidates {b_cand} -> {c_cand}"
                    )
                elif b_type == "THUỐC" and c_type == "THUỐC":
                    stats["changed_drug_candidates"] += 1
                    if args.mode == "strict_identity":
                        failures.append(
                            f"{stem}[{idx}]: drug candidates {b_cand} -> {c_cand}"
                        )
                    pos = b.get("position") or [0, 0]
                    start, end = int(pos[0] or 0), int(pos[1] or 0)
                    left, right = _ctx(text, start, end)
                    row = {
                        "file": stem,
                        "start": start,
                        "end": end,
                        "text": b.get("text", ""),
                        "source": "",
                        "match_type": "",
                        "matched_alias": "",
                        "preset_rxcui_count": "",
                        "preset_rxcui_candidates": "",
                        "v7_candidate": "|".join(b_cand),
                        "v8_candidate": "|".join(c_cand),
                        "v7_had_candidate": bool(b_cand),
                        "v8_has_candidate": bool(c_cand),
                        "left_context": left,
                        "right_context": right,
                    }
                    changed_drug_rows.append(row)
                    if not b_cand and c_cand:
                        stats["newly_linked_drugs"] += 1
                        newly_linked_rows.append(row)
                    elif b_cand and c_cand and b_cand != c_cand:
                        stats["changed_linked_drugs"] += 1
                        changed_linked_rows.append(row)
                    elif b_cand and not c_cand:
                        stats["newly_unlinked_drugs"] += 1
                else:
                    failures.append(
                        f"{stem}[{idx}]: non-drug candidates changed for type "
                        f"{b_type}: {b_cand} -> {c_cand}"
                    )
            elif b_type == "THUỐC":
                stats["unchanged_drug_candidates"] += 1

        if file_changed:
            stats["changed_files"] += 1

    # Hard invariants: baseline and candidate must match each other on
    # file/entity/type/assertion totals. Canonical expected counts are reported
    # as warnings when SapBERT numerics shift disease/symptom borderline ties.
    expected_types = {
        "TRIỆU_CHỨNG": 1899,
        "CHẨN_ĐOÁN": 194,
        "THUỐC": 276,
        "TÊN_XÉT_NGHIỆM": 655,
        "KẾT_QUẢ_XÉT_NGHIỆM": 136,
    }
    if stats["baseline_files"] != 100:
        failures.append(f"baseline file count {stats['baseline_files']} != 100")
    if stats["candidate_files"] != 100:
        failures.append(f"candidate file count {stats['candidate_files']} != 100")
    if stats["baseline_entities"] != stats["candidate_entities"]:
        failures.append(
            f"entity count mismatch baseline={stats['baseline_entities']} "
            f"candidate={stats['candidate_entities']}"
        )
    if stats["baseline_entities"] != 3160:
        failures.append(
            f"baseline entity count {stats['baseline_entities']} != 3160"
        )
    if stats["candidate_entities"] != 3160:
        failures.append(
            f"candidate entity count {stats['candidate_entities']} != 3160"
        )
    for t in sorted(set(type_counts_b) | set(type_counts_c) | set(expected_types)):
        if type_counts_b.get(t, 0) != type_counts_c.get(t, 0):
            failures.append(
                f"type count drift {t}: baseline={type_counts_b.get(t, 0)} "
                f"candidate={type_counts_c.get(t, 0)}"
            )
    for a in sorted(set(assertion_counts_b) | set(assertion_counts_c)):
        if assertion_counts_b.get(a, 0) != assertion_counts_c.get(a, 0):
            failures.append(
                f"assertion count drift {a}: baseline={assertion_counts_b.get(a, 0)} "
                f"candidate={assertion_counts_c.get(a, 0)}"
            )
    # Soft canonical reference checks (do not fail same-env integrity runs).
    summary_warnings: list[str] = []
    for t, n in expected_types.items():
        if type_counts_c.get(t, 0) != n:
            summary_warnings.append(
                f"canonical type reference {t}: got {type_counts_c.get(t, 0)}, "
                f"canonical scored run had {n}"
            )
    if assertion_counts_c.get("isHistorical", 0) != 675:
        summary_warnings.append(
            f"canonical isHistorical reference: got "
            f"{assertion_counts_c.get('isHistorical', 0)}, expected 675"
        )
    if assertion_counts_c.get("isNegated", 0) != 227:
        summary_warnings.append(
            f"canonical isNegated reference: got "
            f"{assertion_counts_c.get('isNegated', 0)}, expected 227"
        )

    prefix = args.export_prefix
    if changed_drug_rows:
        _write_tsv(
            analysis_dir / f"{prefix}_changed_drug_candidates.tsv",
            changed_drug_rows,
            [
                "file",
                "start",
                "end",
                "text",
                "source",
                "match_type",
                "matched_alias",
                "preset_rxcui_count",
                "preset_rxcui_candidates",
                "v7_candidate",
                "v8_candidate",
                "v7_had_candidate",
                "v8_has_candidate",
                "left_context",
                "right_context",
            ],
        )
    if newly_linked_rows:
        _write_tsv(
            analysis_dir / f"{prefix}_newly_linked_drugs.tsv",
            newly_linked_rows,
            [
                "file",
                "start",
                "end",
                "text",
                "v7_candidate",
                "v8_candidate",
                "left_context",
                "right_context",
            ],
        )
    if changed_linked_rows:
        _write_tsv(
            analysis_dir / f"{prefix}_changed_linked_drugs.tsv",
            changed_linked_rows,
            [
                "file",
                "start",
                "end",
                "text",
                "v7_candidate",
                "v8_candidate",
                "left_context",
                "right_context",
            ],
        )

    summary = {
        "mode": args.mode,
        "baseline_dir": str(args.baseline_dir),
        "candidate_dir": str(args.candidate_dir),
        "stats": stats,
        "baseline_type_counts": dict(type_counts_b),
        "candidate_type_counts": dict(type_counts_c),
        "baseline_assertion_counts": dict(assertion_counts_b),
        "candidate_assertion_counts": dict(assertion_counts_c),
        "failure_count": len(failures),
        "failures_sample": failures[:50],
        "warnings": summary_warnings,
        "passed": len(failures) == 0,
    }
    out_json = analysis_dir / f"{prefix}_compare_summary.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        print(f"\nFAILED with {len(failures)} invariant violations")
        for f in failures[:30]:
            print(f"  - {f}")
        return 1

    print("\nPASSED: all hard invariants satisfied")
    return 0


def main() -> None:
    raise SystemExit(compare(parse_args()))


if __name__ == "__main__":
    main()
