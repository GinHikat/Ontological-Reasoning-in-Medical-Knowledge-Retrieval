from __future__ import annotations

"""Diagnostics for v9_llm_recall vs same-environment v7_structured."""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.components.postprocessing.llm_recall import document_sha256  # noqa: E402
from modules.evaluation.analyze_outputs import resolve_submission_dir  # noqa: E402

CONTEXT = 60
ALLOWED = {"TRIỆU_CHỨNG", "CHẨN_ĐOÁN", "THUỐC"}
GENERIC_STATUS = [
    "bệnh nhân tỉnh",
    "tiếp xúc tốt",
    "da niêm mạc hồng",
    "ổn định",
    "chưa phát hiện bất thường",
    "các cơ quan khác bình thường",
]
NEGATION_PREFIXES = ("không có ", "không ", "chưa ")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze v9_llm_recall experiment.")
    p.add_argument("--v7-dir", type=Path, required=True)
    p.add_argument("--v9-dir", type=Path, required=True)
    p.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "v_dataset" / "var" / "test",
    )
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=PROJECT_ROOT / "cache" / "v9_llm_recall",
    )
    p.add_argument(
        "--analysis-dir",
        type=Path,
        default=PROJECT_ROOT / "analysis",
    )
    p.add_argument("--v9-trace-dir", type=Path, default=None)
    return p.parse_args()


def _load_map(output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    submission_dir = resolve_submission_dir(output_dir)
    for path in sorted(submission_dir.glob("*.json")):
        result[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _entity_key(e: dict[str, Any]) -> tuple:
    pos = e.get("position") or [None, None]
    return (pos[0], pos[1], e.get("text", ""), e.get("type", ""))


def _full_key(e: dict[str, Any]) -> tuple:
    pos = e.get("position") or [None, None]
    return (
        e.get("text", ""),
        pos[0],
        pos[1],
        e.get("type", ""),
        tuple(e.get("candidates") or []),
        tuple(e.get("assertions") or []),
    )


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


def _load_cache_index(cache_dir: Path) -> dict[str, dict[str, Any]]:
    by_sha: dict[str, dict[str, Any]] = {}
    if not cache_dir.exists():
        return by_sha
    for path in cache_dir.glob("*.json"):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        by_sha[str(data.get("document_sha256"))] = data
    return by_sha


def _section_guess(text: str, start: int) -> str:
    # Lightweight: last non-empty header-like line before start.
    prefix = text[:start]
    lines = prefix.split("\n")
    for line in reversed(lines):
        s = line.strip()
        if not s:
            continue
        if re.match(r"^\d+\.\s+", s) or s.endswith(":") or len(s) <= 80:
            return s[:120]
    return ""


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    analysis_dir = args.analysis_dir
    analysis_dir.mkdir(parents=True, exist_ok=True)

    v7 = _load_map(args.v7_dir)
    v9 = _load_map(args.v9_dir)
    cache_by_sha = _load_cache_index(args.cache_dir)

    texts: dict[str, str] = {}
    for path in sorted(args.input_dir.glob("*.txt")):
        texts[path.stem] = path.read_text(encoding="utf-8")

    funnel = Counter()
    type_additions = Counter()
    diag_with_icd = 0
    diag_without_icd = 0
    drug_with_rx = 0
    drug_without_rx = 0
    assertion_counts = Counter()

    additions_rows: list[dict[str, Any]] = []
    overlap_rows: list[dict[str, Any]] = []
    type_disagree_rows: list[dict[str, Any]] = []
    align_fail_rows: list[dict[str, Any]] = []
    suspicious_rows: list[dict[str, Any]] = []

    removed = 0
    changed_types = 0
    changed_candidates = 0
    changed_assertions = 0
    invalid_spans = 0
    missing_cache = 0
    parse_failures_unresolved = 0

    files = sorted(set(v7) | set(v9), key=lambda x: int(x) if x.isdigit() else x)
    per_doc_additions: dict[str, int] = {}

    for doc_id in files:
        text = texts.get(doc_id, "")
        sha = document_sha256(text) if text else ""
        cache = cache_by_sha.get(sha)
        if cache is None:
            missing_cache += 1
        else:
            funnel["raw_proposals"] += len(cache.get("parsed_proposals") or [])
            for a in cache.get("alignment_results") or []:
                status = a.get("status")
                if status == "aligned":
                    funnel["aligned"] += 1
                elif status == "zero_match":
                    funnel["zero_match_rejected"] += 1
                    align_fail_rows.append(
                        {
                            "file": doc_id,
                            "line_id": a.get("line_id"),
                            "text": a.get("text"),
                            "type": a.get("type"),
                            "status": status,
                            "detail": a.get("detail"),
                        }
                    )
                elif status == "multiple_match":
                    funnel["multiple_match_rejected"] += 1
                    align_fail_rows.append(
                        {
                            "file": doc_id,
                            "line_id": a.get("line_id"),
                            "text": a.get("text"),
                            "type": a.get("type"),
                            "status": status,
                            "detail": a.get("detail"),
                        }
                    )
                else:
                    funnel["bad_line_rejected"] += 1
                    align_fail_rows.append(
                        {
                            "file": doc_id,
                            "line_id": a.get("line_id"),
                            "text": a.get("text"),
                            "type": a.get("type"),
                            "status": status,
                            "detail": a.get("detail"),
                        }
                    )
            for d in cache.get("verifier_decisions") or []:
                if d.get("accept"):
                    funnel["verifier_accept_raw"] += 1
                else:
                    funnel["verifier_rejected"] += 1
            for item in (cache.get("diagnostics") or {}).get("type_disagreements") or []:
                funnel["type_disagreements"] += 1
                type_disagree_rows.append(
                    {
                        "file": doc_id,
                        "text": item.get("text"),
                        "start": item.get("start"),
                        "end": item.get("end"),
                        "proposer_type": item.get("proposer_type") or item.get("type"),
                        "verifier_type": item.get("verifier_type"),
                        "line_id": item.get("line_id"),
                    }
                )
            if cache.get("parse_failures") and not cache.get("final_accepted_candidates"):
                # unresolved if proposer failed entirely
                if (cache.get("diagnostics") or {}).get("status") == "proposer_failed":
                    parse_failures_unresolved += 1
            funnel["json_parse_failures"] += len(cache.get("parse_failures") or [])
            funnel["repair_retries"] += 1 if cache.get("repair_used") else 0

        b_list = v7.get(doc_id, [])
        c_list = v9.get(doc_id, [])
        b_by_span = {_entity_key(e): e for e in b_list}
        c_by_span = {_entity_key(e): e for e in c_list}
        b_full = {_full_key(e) for e in b_list}

        for key, be in b_by_span.items():
            ce = c_by_span.get(key)
            if ce is None:
                # try match by span only
                span_matches = [
                    e
                    for e in c_list
                    if (e.get("position") or [None, None])[:2]
                    == (be.get("position") or [None, None])[:2]
                ]
                if not span_matches:
                    removed += 1
                    continue
                ce = span_matches[0]
            if ce.get("type") != be.get("type"):
                changed_types += 1
            if list(ce.get("candidates") or []) != list(be.get("candidates") or []):
                changed_candidates += 1
            if list(ce.get("assertions") or []) != list(be.get("assertions") or []):
                changed_assertions += 1

        # New entities in v9
        new_entities = []
        for e in c_list:
            if _full_key(e) in b_full:
                continue
            # also skip if identical span+text+type+cands+assertions already counted
            b_span_key = _entity_key(e)
            if b_span_key in b_by_span and _full_key(b_by_span[b_span_key]) == _full_key(e):
                continue
            if b_span_key not in b_by_span:
                new_entities.append(e)
            else:
                # same span exists in v7 — should not happen under additive rule
                pass

        per_doc_additions[doc_id] = len(new_entities)
        funnel["final_additions"] += len(new_entities)

        # Overlap rejections from cache are pre-pipeline; also check pipeline can't know.
        # We reconstruct overlap rejects by comparing cache accepted vs final new.
        cache_accepted = []
        if cache:
            cache_accepted = list(cache.get("final_accepted_candidates") or [])

        final_span_set = {
            (
                (e.get("position") or [None, None])[0],
                (e.get("position") or [None, None])[1],
                e.get("text"),
                e.get("type"),
            )
            for e in new_entities
        }

        v7_spans = [
            (
                (e.get("position") or [None, None])[0],
                (e.get("position") or [None, None])[1],
                e.get("text"),
                e.get("type"),
            )
            for e in b_list
        ]

        for cand in cache_accepted:
            start, end = cand.get("start"), cand.get("end")
            text_c, typ = cand.get("text"), cand.get("type")
            key = (start, end, text_c, typ)
            # exact duplicate vs v7
            exact = any(s == start and e == end for s, e, _, _ in v7_spans)
            if exact:
                funnel["exact_span_duplicates_skipped"] += 1
                continue
            overlaps = False
            for s, e, et, el in v7_spans:
                if s is None or e is None or start is None or end is None:
                    continue
                if max(int(s), int(start)) < min(int(e), int(end)):
                    overlaps = True
                    funnel["overlap_rejected"] += 1
                    left, right = _ctx(text, int(start), int(end))
                    overlap_rows.append(
                        {
                            "file": doc_id,
                            "start": start,
                            "end": end,
                            "text": text_c,
                            "type": typ,
                            "existing_start": s,
                            "existing_end": e,
                            "existing_text": et,
                            "existing_type": el,
                            "left_context": left,
                            "right_context": right,
                        }
                    )
                    break
            if overlaps:
                continue
            if key not in final_span_set:
                # accepted by LLM path but dropped later by merge/filter/dedup
                funnel["dropped_after_merge_or_filter"] += 1

        for e in new_entities:
            pos = e.get("position") or [None, None]
            start, end = pos[0], pos[1]
            etext = e.get("text", "")
            etype = e.get("type", "")
            if not isinstance(start, int) or not isinstance(end, int):
                invalid_spans += 1
                continue
            if text[start:end] != etext:
                invalid_spans += 1
            type_additions[etype] += 1
            cands = list(e.get("candidates") or [])
            assertions = list(e.get("assertions") or [])
            if etype == "CHẨN_ĐOÁN":
                if cands:
                    diag_with_icd += 1
                else:
                    diag_without_icd += 1
            if etype == "THUỐC":
                if cands:
                    drug_with_rx += 1
                else:
                    drug_without_rx += 1
            if etype in ALLOWED:
                if not assertions:
                    assertion_counts["no_assertion"] += 1
                for a in assertions:
                    assertion_counts[a] += 1

            # find proposer/verifier types from cache
            proposer_type = etype
            verifier_type = etype
            if cache:
                for cand in cache.get("final_accepted_candidates") or []:
                    if (
                        cand.get("start") == start
                        and cand.get("end") == end
                        and cand.get("text") == etext
                    ):
                        proposer_type = cand.get("proposer_type", etype)
                        verifier_type = cand.get("verifier_type", etype)
                        break

            left, right = _ctx(text, start, end)
            additions_rows.append(
                {
                    "file": doc_id,
                    "start": start,
                    "end": end,
                    "text": etext,
                    "type": etype,
                    "left_context": left,
                    "right_context": right,
                    "proposer_type": proposer_type,
                    "verifier_type": verifier_type,
                    "candidates": "|".join(cands),
                    "assertions": "|".join(assertions),
                    "section": _section_guess(text, start),
                }
            )

            flags = []
            if len(etext) > 80:
                flags.append("long_gt_80")
            if "\n" in etext:
                flags.append("contains_newline")
            low = etext.lower().strip()
            for pref in NEGATION_PREFIXES:
                if low.startswith(pref):
                    flags.append(f"starts_with_{pref.strip().replace(' ', '_')}")
                    break
            if len(etext.strip()) <= 1:
                flags.append("single_char")
            for phrase in GENERIC_STATUS:
                if phrase in low:
                    flags.append("generic_status_phrase")
                    break
            if etype == "THUỐC" and not cands:
                flags.append("drug_no_candidate")
            if etype == "CHẨN_ĐOÁN" and not cands:
                flags.append("diagnosis_no_candidate")
            if flags:
                suspicious_rows.append(
                    {
                        **additions_rows[-1],
                        "flags": "|".join(flags),
                    }
                )

    # Count verified from cache finals that are non-overlapping conceptually
    funnel["verifier_accepted_final_cache"] = sum(
        len(c.get("final_accepted_candidates") or []) for c in cache_by_sha.values()
    )

    decision = "READY FOR MANUAL REVIEW"
    hard_fail_reasons = []
    if removed:
        hard_fail_reasons.append(f"existing v7 entities removed: {removed}")
    if changed_types:
        hard_fail_reasons.append(f"existing v7 types changed: {changed_types}")
    if changed_candidates:
        hard_fail_reasons.append(f"existing v7 candidates changed: {changed_candidates}")
    if changed_assertions:
        hard_fail_reasons.append(f"existing v7 assertions changed: {changed_assertions}")
    if invalid_spans:
        hard_fail_reasons.append(f"invalid spans: {invalid_spans}")
    if missing_cache:
        hard_fail_reasons.append(f"LLM cache missing for documents: {missing_cache}")
    if funnel["final_additions"] == 0:
        hard_fail_reasons.append("0 final LLM additions")
    if parse_failures_unresolved:
        hard_fail_reasons.append(
            f"unresolved LLM parser failures: {parse_failures_unresolved}"
        )
    if hard_fail_reasons:
        decision = "NOT READY"

    high_risk = []
    if funnel["final_additions"] > 500:
        high_risk.append(f">500 additions ({funnel['final_additions']})")
    max_doc_add = max(per_doc_additions.values()) if per_doc_additions else 0
    if max_doc_add > 20:
        high_risk.append(f">20 additions in one document (max={max_doc_add})")
    diag_total = diag_with_icd + diag_without_icd
    if diag_total and diag_without_icd / diag_total > 0.30:
        high_risk.append(
            f">30% new diagnoses lack ICD ({diag_without_icd}/{diag_total})"
        )
    drug_total = drug_with_rx + drug_without_rx
    if drug_total and drug_without_rx / drug_total > 0.30:
        high_risk.append(
            f">30% new drugs lack RxNorm ({drug_without_rx}/{drug_total})"
        )

    # Trace validation
    trace_dir = args.v9_trace_dir
    if trace_dir is None:
        # try sibling
        cand = args.v9_dir / "trace"
        if not cand.exists():
            cand = args.v9_dir.parent / f"{args.v9_dir.name}_traces"
        trace_dir = cand if cand.exists() else None

    trace_stats = {"trace_files": 0, "non_empty": 0, "empty": 0, "trace_dir": str(trace_dir)}
    if trace_dir and trace_dir.exists():
        traces = sorted(trace_dir.glob("*_trace.txt"))
        trace_stats["trace_files"] = len(traces)
        for t in traces:
            content = t.read_text(encoding="utf-8")
            if content.strip():
                trace_stats["non_empty"] += 1
            else:
                trace_stats["empty"] += 1

    _write_tsv(
        analysis_dir / "v9_llm_additions.tsv",
        additions_rows,
        [
            "file",
            "start",
            "end",
            "text",
            "type",
            "left_context",
            "right_context",
            "proposer_type",
            "verifier_type",
            "candidates",
            "assertions",
            "section",
        ],
    )
    _write_tsv(
        analysis_dir / "v9_overlap_rejections.tsv",
        overlap_rows,
        [
            "file",
            "start",
            "end",
            "text",
            "type",
            "existing_start",
            "existing_end",
            "existing_text",
            "existing_type",
            "left_context",
            "right_context",
        ],
    )
    _write_tsv(
        analysis_dir / "v9_type_disagreements.tsv",
        type_disagree_rows,
        [
            "file",
            "text",
            "start",
            "end",
            "proposer_type",
            "verifier_type",
            "line_id",
        ],
    )
    _write_tsv(
        analysis_dir / "v9_alignment_failures.tsv",
        align_fail_rows,
        ["file", "line_id", "text", "type", "status", "detail"],
    )
    _write_tsv(
        analysis_dir / "v9_suspicious_additions.tsv",
        suspicious_rows,
        [
            "file",
            "start",
            "end",
            "text",
            "type",
            "left_context",
            "right_context",
            "proposer_type",
            "verifier_type",
            "candidates",
            "assertions",
            "section",
            "flags",
        ],
    )

    # Best/worst samples for report
    def score_addition(row: dict[str, Any]) -> int:
        s = 0
        t = row["text"]
        if 3 <= len(t) <= 40:
            s += 2
        if row["type"] in ALLOWED:
            s += 1
        if row.get("candidates"):
            s += 2
        if not any(
            row["text"].lower().startswith(p) for p in ("không", "chưa", "bệnh nhân")
        ):
            s += 1
        return s

    ranked = sorted(additions_rows, key=score_addition, reverse=True)
    best30 = ranked[:30]
    worst = suspicious_rows[:40] if suspicious_rows else ranked[-20:]

    report_lines = [
        "# v9_llm_recall report",
        "",
        f"documents: {len(files)}",
        "",
        "## Funnel",
        f"- raw LLM proposals: {funnel['raw_proposals']}",
        f"- JSON parse failure events: {funnel['json_parse_failures']}",
        f"- repair retries used: {funnel['repair_retries']}",
        f"- exactly aligned: {funnel['aligned']}",
        f"- zero-match rejected: {funnel['zero_match_rejected']}",
        f"- multiple-match rejected: {funnel['multiple_match_rejected']}",
        f"- verifier accept decisions (raw): {funnel['verifier_accept_raw']}",
        f"- verifier rejected: {funnel['verifier_rejected']}",
        f"- type disagreements: {funnel['type_disagreements']}",
        f"- exact-span duplicates skipped: {funnel['exact_span_duplicates_skipped']}",
        f"- overlap rejected: {funnel['overlap_rejected']}",
        f"- cache-accepted candidates: {funnel['verifier_accepted_final_cache']}",
        f"- dropped after merge/filter: {funnel['dropped_after_merge_or_filter']}",
        f"- final LLM additions: {funnel['final_additions']}",
        "",
        "## Final additions by type",
        f"- TRIỆU_CHỨNG: {type_additions['TRIỆU_CHỨNG']}",
        f"- CHẨN_ĐOÁN: {type_additions['CHẨN_ĐOÁN']}",
        f"- THUỐC: {type_additions['THUỐC']}",
        "",
        "## New diagnosis candidate coverage",
        f"- with ICD candidate: {diag_with_icd}",
        f"- without ICD candidate: {diag_without_icd}",
        "",
        "## New drug candidate coverage",
        f"- with RxNorm candidate: {drug_with_rx}",
        f"- without RxNorm candidate: {drug_without_rx}",
        "",
        "## New assertion-eligible entities",
        f"- isHistorical: {assertion_counts['isHistorical']}",
        f"- isNegated: {assertion_counts['isNegated']}",
        f"- isFamily: {assertion_counts['isFamily']}",
        f"- no assertion: {assertion_counts['no_assertion']}",
        "",
        "## Existing-v7 invariants",
        f"- removed: {removed}",
        f"- changed types: {changed_types}",
        f"- changed candidates: {changed_candidates}",
        f"- changed assertions: {changed_assertions}",
        f"- invalid spans: {invalid_spans}",
        f"- missing cache docs: {missing_cache}",
        f"- unresolved parse failures: {parse_failures_unresolved}",
        "",
        "## Trace validation",
        f"- trace_dir: {trace_stats['trace_dir']}",
        f"- trace files: {trace_stats['trace_files']}",
        f"- non-empty: {trace_stats['non_empty']}",
        f"- empty: {trace_stats['empty']}",
        "",
        "## High risk flags",
    ]
    if high_risk:
        report_lines.extend(f"- {x}" for x in high_risk)
    else:
        report_lines.append("- none")

    report_lines += ["", "## Decision", decision, ""]
    if hard_fail_reasons:
        report_lines.append("Hard NOT READY reasons:")
        report_lines.extend(f"- {x}" for x in hard_fail_reasons)
        report_lines.append("")

    report_lines.append("## Best 30 additions (heuristic)")
    for row in best30:
        report_lines.append(
            f"- file {row['file']} [{row['start']}:{row['end']}] "
            f"{row['type']}: `{row['text']}` | L:`{row['left_context']}` R:`{row['right_context']}`"
        )

    report_lines.append("")
    report_lines.append("## Suspicious / worst additions")
    for row in worst[:30]:
        flags = row.get("flags", "")
        report_lines.append(
            f"- file {row['file']} [{row['start']}:{row['end']}] "
            f"{row['type']}: `{row['text']}` flags={flags}"
        )

    report_lines.append("")
    report_lines.append("## Overlap rejection examples")
    for row in overlap_rows[:20]:
        report_lines.append(
            f"- file {row['file']}: LLM `{row['text']}` "
            f"overlapped existing `{row['existing_text']}` ({row['existing_type']})"
        )

    report_path = analysis_dir / "v9_llm_recall_report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    summary = {
        "documents": len(files),
        "funnel": dict(funnel),
        "type_additions": dict(type_additions),
        "diag_with_icd": diag_with_icd,
        "diag_without_icd": diag_without_icd,
        "drug_with_rx": drug_with_rx,
        "drug_without_rx": drug_without_rx,
        "assertion_counts": dict(assertion_counts),
        "invariants": {
            "removed": removed,
            "changed_types": changed_types,
            "changed_candidates": changed_candidates,
            "changed_assertions": changed_assertions,
            "invalid_spans": invalid_spans,
            "missing_cache": missing_cache,
            "parse_failures_unresolved": parse_failures_unresolved,
        },
        "trace_stats": trace_stats,
        "high_risk": high_risk,
        "decision": decision,
        "hard_fail_reasons": hard_fail_reasons,
        "max_additions_one_doc": max_doc_add,
    }
    (analysis_dir / "v9_llm_recall_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Report: {report_path}")
    return summary


def main() -> None:
    analyze(parse_args())


if __name__ == "__main__":
    main()
