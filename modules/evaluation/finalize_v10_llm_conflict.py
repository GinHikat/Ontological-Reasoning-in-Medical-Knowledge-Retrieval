#!/usr/bin/env python3
"""Finalize v10_llm_conflict_resolution: validate, audit, annotation packet, report, ZIPs.

Phases 3–16 of the v10 full-run checklist. Does not re-run the pipeline or Qwen.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.components.postprocessing.llm_conflict_resolution import (  # noqa: E402
    OverlapHit,
    classify_one_to_one,
    find_overlapping_v7,
    load_diagnosis_name_index,
    load_drug_terms_by_rxcui,
)
from modules.components.postprocessing.llm_recall import (  # noqa: E402
    document_sha256,
    load_cache_record,
    spans_overlap,
)
from modules.core.schemas import FinalEntity, Span  # noqa: E402

VALID_TYPES = {
    "TRIỆU_CHỨNG",
    "CHẨN_ĐOÁN",
    "THUỐC",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
}
CONTEXT = 80


def _full_key(e: dict[str, Any]) -> tuple:
    pos = e.get("position") or [None, None]
    return (
        e.get("text", ""),
        int(pos[0]),
        int(pos[1]),
        e.get("type", ""),
        tuple(e.get("candidates") or []),
        tuple(e.get("assertions") or []),
    )


def _span_key(e: dict[str, Any]) -> tuple:
    pos = e.get("position") or [None, None]
    return (int(pos[0]), int(pos[1]), e.get("text", ""), e.get("type", ""))


def _ctx(text: str, start: int, end: int, n: int = CONTEXT) -> tuple[str, str]:
    left = text[max(0, start - n) : start].replace("\n", " ")
    right = text[end : min(len(text), end + n)].replace("\n", " ")
    return left, right


def _line_ctx(text: str, start: int, end: int) -> str:
    ls = text.rfind("\n", 0, start)
    ls = 0 if ls < 0 else ls + 1
    le = text.find("\n", end)
    le = len(text) if le < 0 else le
    return text[ls:le].strip()


def _load_entities(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_final(entities: list[dict[str, Any]]) -> list[FinalEntity]:
    out: list[FinalEntity] = []
    for e in entities:
        s, ed = e["position"]
        out.append(
            FinalEntity(
                text=e["text"],
                type=e["type"],
                span=Span(int(s), int(ed)),
                candidates=list(e.get("candidates") or []),
                assertions=list(e.get("assertions") or []),
            )
        )
    return out


def _write_tsv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh, fieldnames=headers, delimiter="\t", extrasaction="ignore", lineterminator="\n"
        )
        w.writeheader()
        for row in rows:
            clean = {
                h: str(row.get(h, "")).replace("\t", " ").replace("\n", " ") for h in headers
            }
            w.writerow(clean)


def _write_csv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({h: row.get(h, "") for h in headers})


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _cand_change(old: list[str], new: list[str]) -> str:
    o, n = list(old or []), list(new or [])
    if o == n:
        return "preserved"
    if not n and o:
        return "lost"
    if not o and n:
        return "gained"
    # Heuristic improved/worsened for drugs/diagnoses: nonempty both, different
    return "changed"


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[A-Za-zÀ-ỹà-ỹ0-9]+", text.lower()) if len(t) > 1}


def _lexical_overlap(span: str, terms: list[str]) -> float:
    st = _tokenize(span)
    if not st or not terms:
        return 0.0
    best = 0.0
    for term in terms:
        tt = _tokenize(term)
        if not tt:
            continue
        inter = len(st & tt)
        union = len(st | tt)
        best = max(best, inter / union if union else 0.0)
        if _norm(span) in _norm(term) or _norm(term) in _norm(span):
            best = max(best, 1.0)
    return best


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def structural_validate(
    input_dir: Path, base_dir: Path, sub_dir: Path, trace_dir: Path
) -> dict[str, Any]:
    stats = {
        "invalid_offsets": 0,
        "missing_documents": 0,
        "malformed_json": 0,
        "empty_traces": 0,
        "type_errors": 0,
        "details": [],
    }
    txts = {p.stem: p for p in input_dir.glob("*.txt")}
    for stem in sorted(txts, key=lambda x: int(x) if x.isdigit() else x):
        for label, d in (("base", base_dir), ("submission", sub_dir)):
            path = d / f"{stem}.json"
            if not path.exists():
                stats["missing_documents"] += 1
                stats["details"].append(f"missing {label} {stem}")
                continue
            try:
                entities = _load_entities(path)
            except Exception as exc:  # noqa: BLE001
                stats["malformed_json"] += 1
                stats["details"].append(f"malformed {label} {stem}: {exc}")
                continue
            if not isinstance(entities, list):
                stats["malformed_json"] += 1
                stats["details"].append(f"root not list {label} {stem}")
                continue
            text = txts[stem].read_text(encoding="utf-8")
            for e in entities:
                pos = e.get("position")
                t = e.get("text", "")
                typ = e.get("type", "")
                if not isinstance(pos, list) or len(pos) != 2:
                    stats["invalid_offsets"] += 1
                    continue
                s, ed = int(pos[0]), int(pos[1])
                if not t or s >= ed or s < 0 or ed > len(text) or text[s:ed] != t:
                    stats["invalid_offsets"] += 1
                    stats["details"].append(
                        f"offset {label} {stem} {pos} {t!r}"
                    )
                if typ not in VALID_TYPES:
                    stats["type_errors"] += 1
                if "candidates" in e and not isinstance(e["candidates"], list):
                    stats["malformed_json"] += 1
                if not isinstance(e.get("assertions", []), list):
                    stats["malformed_json"] += 1
        tr = trace_dir / f"{stem}_trace.txt"
        if not tr.exists():
            stats["missing_documents"] += 1
            stats["details"].append(f"missing trace {stem}")
        elif not tr.read_text(encoding="utf-8").strip():
            stats["empty_traces"] += 1
            stats["details"].append(f"empty trace {stem}")
    return stats


def compare_docs(
    base: list[dict[str, Any]], sub: list[dict[str, Any]]
) -> dict[str, Any]:
    base_by_full = {_full_key(e): e for e in base}
    sub_by_full = {_full_key(e): e for e in sub}
    identical = set(base_by_full) & set(sub_by_full)
    base_only = [base_by_full[k] for k in base_by_full if k not in identical]
    sub_only = [sub_by_full[k] for k in sub_by_full if k not in identical]

    replacements: list[tuple[dict[str, Any], dict[str, Any]]] = []
    used_new: set[int] = set()
    unpaired_old: list[dict[str, Any]] = []
    for old in base_only:
        os, oe = old["position"]
        matched = None
        for i, new in enumerate(sub_only):
            if i in used_new:
                continue
            ns, ne = new["position"]
            if spans_overlap(int(os), int(oe), int(ns), int(ne)):
                matched = i
                break
        if matched is None:
            unpaired_old.append(old)
        else:
            used_new.add(matched)
            replacements.append((old, sub_only[matched]))

    unpaired_new = [e for i, e in enumerate(sub_only) if i not in used_new]

    # Unexpected modification: same span key but different cand/assert/type/text
    # (already captured as base_only/sub_only if full key differs)
    unexpected = 0
    base_span = {_span_key(e): e for e in base}
    sub_span = {_span_key(e): e for e in sub}
    for k, be in base_span.items():
        if k in sub_span and _full_key(be) != _full_key(sub_span[k]):
            # identical span identity but different fields — should not happen
            # if text/type/pos form the span key; if cand/assert differ, span key same
            pass
    # Detect field-only changes with same text/pos/type
    soft_base = {(e["text"], e["position"][0], e["position"][1], e["type"]): e for e in base}
    soft_sub = {(e["text"], e["position"][0], e["position"][1], e["type"]): e for e in sub}
    for k, be in soft_base.items():
        if k in soft_sub and _full_key(be) != _full_key(soft_sub[k]):
            unexpected += 1

    return {
        "replacements": replacements,
        "additions": unpaired_new,
        "removals": unpaired_old,
        "unexpected_modifications": unexpected,
        "preserved": len(identical),
    }


def parse_trace_replacements(trace_text: str) -> list[dict[str, Any]]:
    """Parse accepted replacements block from v10 trace footer."""
    rows: list[dict[str, Any]] = []
    if "Accepted replacements:" not in trace_text:
        return rows
    block = trace_text.split("Accepted replacements:", 1)[1]
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        # [1849:1857] THUỐC | 'atenolol' | cat=A | cands=[...] | asserts=[...] | replaced='...'
        m = re.match(
            r"\[(\d+):(\d+)\]\s+(\S+)\s+\|\s+'(.*)'\s+\|\s+cat=(\w+)\s+\|",
            line,
        )
        if not m:
            # try with double quotes unlikely; texts may contain \'
            m2 = re.match(
                r"\[(\d+):(\d+)\]\s+(\S+)\s+\|\s+(.*?)\s+\|\s+cat=(\w+)\s+\|",
                line,
            )
            if not m2:
                continue
            start, end, typ, text_repr, cat = m2.groups()
            text = text_repr.strip()
            if text.startswith("'") and text.endswith("'"):
                text = text[1:-1]
        else:
            start, end, typ, text, cat = m.groups()
        rm = re.search(r"replaced=(.*)$", line)
        replaced = ""
        if rm:
            replaced = rm.group(1).strip()
            if replaced.startswith("'") and replaced.endswith("'"):
                replaced = replaced[1:-1]
        cm = re.search(r"cands=(\[[^\]]*\])", line)
        am = re.search(r"asserts=(\[[^\]]*\])", line)
        cands: list[str] = []
        asserts: list[str] = []
        if cm:
            try:
                cands = ast_literal_list(cm.group(1))
            except Exception:  # noqa: BLE001
                cands = []
        if am:
            try:
                asserts = ast_literal_list(am.group(1))
            except Exception:  # noqa: BLE001
                asserts = []
        rows.append(
            {
                "start": int(start),
                "end": int(end),
                "type": typ,
                "text": text,
                "category": cat,
                "replaced": replaced,
                "candidates": cands,
                "assertions": asserts,
            }
        )
    return rows


def ast_literal_list(s: str) -> list[str]:
    import ast

    val = ast.literal_eval(s)
    return [str(x) for x in val]


def collect_all_conflicts(
    file_stem: str,
    text: str,
    base: list[dict[str, Any]],
    cache_dir: Path,
    accepted: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sha = document_sha256(text)
    record = load_cache_record(cache_dir, sha)
    rows: list[dict[str, Any]] = []
    if record is None:
        return rows
    frozen = _to_final(base)
    accepted_spans = {(r["new_start"], r["new_end"], r["new_text"]) for r in accepted}

    for cand in record.get("final_accepted_candidates") or []:
        lt = str(cand.get("text", ""))
        ltype = str(cand.get("type", ""))
        ls, le = cand.get("start"), cand.get("end")
        if not isinstance(ls, int) or not isinstance(le, int):
            continue
        if text[ls:le] != lt:
            continue
        overlaps = find_overlapping_v7(ls, le, frozen)
        left, right = _ctx(text, ls, le)
        if not overlaps:
            rows.append(
                {
                    "file": file_stem,
                    "v7_text": "",
                    "v7_position": "",
                    "v7_type": "",
                    "v7_candidates": "",
                    "v7_assertions": "",
                    "llm_text": lt,
                    "llm_position": f"[{ls},{le}]",
                    "llm_type": ltype,
                    "overlap_relation": "NONE",
                    "proposed_category": "",
                    "accepted_by_v10": "no",
                    "rejection_reason": "NO_OVERLAP_SKIPPED_ADDITIVE",
                    "left_context": left,
                    "right_context": right,
                }
            )
            continue
        if len(overlaps) != 1:
            for idx, ent in overlaps:
                rows.append(
                    {
                        "file": file_stem,
                        "v7_text": ent.text,
                        "v7_position": f"[{ent.span.start},{ent.span.end}]",
                        "v7_type": ent.type,
                        "v7_candidates": "",
                        "v7_assertions": "",
                        "llm_text": lt,
                        "llm_position": f"[{ls},{le}]",
                        "llm_type": ltype,
                        "overlap_relation": "MULTI",
                        "proposed_category": "",
                        "accepted_by_v10": "no",
                        "rejection_reason": "MULTI_V7_OVERLAP",
                        "left_context": left,
                        "right_context": right,
                    }
                )
            continue
        idx, ent = overlaps[0]
        hit = OverlapHit(
            llm_text=lt,
            llm_type=ltype,
            llm_start=ls,
            llm_end=le,
            v7_index=idx,
            v7_text=ent.text,
            v7_type=ent.type,
            v7_start=int(ent.span.start),
            v7_end=int(ent.span.end),
        )
        decision = classify_one_to_one(hit)
        # find matching base entity fields
        v7_cands = ""
        v7_asserts = ""
        for be in base:
            if be["position"] == [ent.span.start, ent.span.end] and be["text"] == ent.text:
                v7_cands = json.dumps(be.get("candidates") or [], ensure_ascii=False)
                v7_asserts = json.dumps(be.get("assertions") or [], ensure_ascii=False)
                break
        accepted_flag = "yes" if (ls, le, lt) in accepted_spans else "no"
        if decision is None:
            reason = "NO_HIGH_CONFIDENCE_RULE"
            cat = ""
            rel = "OVERLAP"
        else:
            cat = decision.category
            reason = "" if accepted_flag == "yes" else "POST_LINK_OR_CLAIM_REJECT"
            rel = "OVERLAP"
            if int(ent.span.start) == ls and int(ent.span.end) == le:
                rel = "EXACT"
            elif ls >= int(ent.span.start) and le <= int(ent.span.end):
                rel = "LLM_INSIDE_V7"
            elif int(ent.span.start) >= ls and int(ent.span.end) <= le:
                rel = "V7_INSIDE_LLM"
        rows.append(
            {
                "file": file_stem,
                "v7_text": ent.text,
                "v7_position": f"[{ent.span.start},{ent.span.end}]",
                "v7_type": ent.type,
                "v7_candidates": v7_cands,
                "v7_assertions": v7_asserts,
                "llm_text": lt,
                "llm_position": f"[{ls},{le}]",
                "llm_type": ltype,
                "overlap_relation": rel,
                "proposed_category": cat,
                "accepted_by_v10": accepted_flag,
                "rejection_reason": reason if accepted_flag == "no" else "",
                "left_context": left,
                "right_context": right,
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output" / "v10_llm_conflict_resolution",
    )
    ap.add_argument("--input-dir", type=Path, default=ROOT / "v_dataset" / "var" / "test")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "cache" / "v9_llm_recall")
    ap.add_argument("--analysis-dir", type=Path, default=ROOT / "analysis")
    args = ap.parse_args()

    out = args.output_dir
    base_dir = out / "base_v7_snapshot"
    sub_dir = out / "submission"
    trace_dir = out / "trace"
    analysis = args.analysis_dir
    analysis.mkdir(parents=True, exist_ok=True)

    diag_names = load_diagnosis_name_index(
        ROOT / "v_dataset" / "viettel" / "base" / "short_diagnosis.csv"
    )
    drug_terms = load_drug_terms_by_rxcui(
        ROOT / "v_dataset" / "viettel" / "base" / "short_drug.csv"
    )

    # --- Phase 3 ---
    struct = structural_validate(args.input_dir, base_dir, sub_dir, trace_dir)
    n_base = len(list(base_dir.glob("*.json")))
    n_sub = len(list(sub_dir.glob("*.json")))
    n_tr = len(list(trace_dir.glob("*_trace.txt")))

    replacement_rows: list[dict[str, Any]] = []
    cand_rows: list[dict[str, Any]] = []
    assert_rows: list[dict[str, Any]] = []
    all_conflict_rows: list[dict[str, Any]] = []
    per_doc = Counter()
    cat_accepted = Counter()
    totals = Counter()
    hard = {
        "invalid_spans": struct["invalid_offsets"],
        "missing_documents": struct["missing_documents"],
        "malformed_json": struct["malformed_json"],
        "empty_traces": struct["empty_traces"],
        "pure_additions": 0,
        "unpaired_removals": 0,
        "unexpected_modifications": 0,
        "type_errors": struct["type_errors"],
    }

    stems = sorted(
        [p.stem for p in args.input_dir.glob("*.txt")],
        key=lambda x: int(x) if x.isdigit() else x,
    )

    for stem in stems:
        text = (args.input_dir / f"{stem}.txt").read_text(encoding="utf-8")
        base = _load_entities(base_dir / f"{stem}.json")
        sub = _load_entities(sub_dir / f"{stem}.json")
        trace = (trace_dir / f"{stem}_trace.txt").read_text(encoding="utf-8")
        cmp = compare_docs(base, sub)
        hard["pure_additions"] += len(cmp["additions"])
        hard["unpaired_removals"] += len(cmp["removals"])
        hard["unexpected_modifications"] += cmp["unexpected_modifications"]
        totals["conflicts_considered"] += len(
            (load_cache_record(args.cache_dir, document_sha256(text)) or {}).get(
                "final_accepted_candidates"
            )
            or []
        )

        # Prefer pairing from compare; enrich category from trace
        trace_reps = parse_trace_replacements(trace)
        trace_by_span = {(r["start"], r["end"], r["text"]): r for r in trace_reps}

        doc_reps: list[dict[str, Any]] = []
        for old, new in cmp["replacements"]:
            os, oe = int(old["position"][0]), int(old["position"][1])
            ns, ne = int(new["position"][0]), int(new["position"][1])
            tr = trace_by_span.get((ns, ne, new["text"]))
            category = (tr or {}).get("category", "")
            if not category:
                # recompute
                hit = OverlapHit(
                    llm_text=new["text"],
                    llm_type=new["type"],
                    llm_start=ns,
                    llm_end=ne,
                    v7_index=0,
                    v7_text=old["text"],
                    v7_type=old["type"],
                    v7_start=os,
                    v7_end=oe,
                )
                d = classify_one_to_one(hit)
                category = d.category if d else "?"
                reason = d.reason if d else "unknown"
            else:
                reason = {
                    "A": "drug_junk_boundary",
                    "B": "leading_negation_trim",
                    "C": "diagnosis_span_expand",
                    "D": "type_boundary_cleanup",
                }.get(category, "")

            left, right = _ctx(text, ns, ne)
            old_c = list(old.get("candidates") or [])
            new_c = list(new.get("candidates") or [])
            old_a = list(old.get("assertions") or [])
            new_a = list(new.get("assertions") or [])
            cand_chg = _cand_change(old_c, new_c)

            # Category-specific evidence strings
            det = reason
            linker = f"old={old_c} new={new_c} change={cand_chg}"
            asertev = f"old={old_a} new={new_a}"
            if category == "B" and "isNegated" not in new_a:
                asertev += " | FLAG: missing isNegated"

            row = {
                "file": stem,
                "category": category,
                "old_start": os,
                "old_end": oe,
                "old_text": old["text"],
                "old_type": old["type"],
                "old_candidates": json.dumps(old_c, ensure_ascii=False),
                "old_assertions": json.dumps(old_a, ensure_ascii=False),
                "new_start": ns,
                "new_end": ne,
                "new_text": new["text"],
                "new_type": new["type"],
                "new_candidates": json.dumps(new_c, ensure_ascii=False),
                "new_assertions": json.dumps(new_a, ensure_ascii=False),
                "left_context": left,
                "right_context": right,
                "llm_text": new["text"],
                "llm_type": new["type"],
                "replacement_reason": reason,
                "deterministic_evidence": det,
                "linker_evidence": linker,
                "assertion_evidence": asertev,
                "review_status": "PENDING",
                "review_notes": "",
                "candidate_change": cand_chg,
                "line_context": _line_ctx(text, ns, ne),
            }
            # A flags
            if category == "A":
                if not (ns >= os and ne <= oe and (ns > os or ne < oe)):
                    row["review_notes"] += "FLAG:A_not_contained; "
                if cand_chg == "lost":
                    row["review_notes"] += "FLAG:A_candidate_lost; "
                leftover = old["text"][: ns - os] + old["text"][ne - os :]
                if re.search(r"(?i)(\d+\s*(mg|ml)|viên|uống|tiêm)", leftover):
                    row["review_notes"] += "FLAG:A_possible_dose_route; "
            if category == "B":
                if "isNegated" not in new_a:
                    row["review_notes"] += "FLAG:B_missing_isNegated; "
                if not old["text"].lower().lstrip().startswith(("không", "chưa")):
                    row["review_notes"] += "FLAG:B_cue_unclear; "
            if category == "C":
                if not (os >= ns and oe <= ne):
                    row["review_notes"] += "FLAG:C_old_not_inside_new; "
                low = new["text"].lower()
                for bad in (" vì ", " do ", " nên ", ":", "("):
                    if bad in low or bad in new["text"]:
                        row["review_notes"] += f"FLAG:C_risky({bad.strip()}); "
                        break
            if category == "D":
                if old["type"] == new["type"]:
                    row["review_notes"] += "FLAG:D_type_unchanged; "

            replacement_rows.append(row)
            doc_reps.append(row)
            cat_accepted[category] += 1
            per_doc[stem] += 1

            # candidate consistency
            status = "UNRESOLVED"
            reason_c = ""
            terms: list[str] = []
            cid = ""
            if new["type"] == "CHẨN_ĐOÁN":
                if not new_c:
                    status, reason_c = "INCONSISTENT", "empty_icd"
                else:
                    cid = str(new_c[0])
                    name = diag_names.get(cid, "")
                    terms = [name] if name else []
                    ov = _lexical_overlap(new["text"], terms) if terms else 0.0
                    if not name:
                        status, reason_c = "UNRESOLVED", "icd_name_missing"
                    elif ov >= 0.2 or _norm(new["text"]) in _norm(name):
                        status, reason_c = "CONSISTENT", f"overlap={ov:.2f}"
                    elif ov > 0:
                        status, reason_c = "QUESTIONABLE", f"overlap={ov:.2f}"
                    else:
                        status, reason_c = "INCONSISTENT", f"overlap={ov:.2f}"
            elif new["type"] == "THUỐC":
                if not new_c:
                    status, reason_c = "INCONSISTENT", "empty_rxnorm"
                else:
                    cid = str(new_c[0])
                    terms = list(drug_terms.get(cid) or [])[:20]
                    ov = _lexical_overlap(new["text"], terms)
                    if not terms:
                        status, reason_c = "UNRESOLVED", "rx_terms_missing"
                    elif ov >= 0.2:
                        status, reason_c = "CONSISTENT", f"overlap={ov:.2f}"
                    elif ov > 0:
                        status, reason_c = "QUESTIONABLE", f"overlap={ov:.2f}"
                    else:
                        status, reason_c = "INCONSISTENT", f"overlap={ov:.2f}"
            else:
                status, reason_c = "CONSISTENT", "symptom_no_ontology"

            cand_rows.append(
                {
                    "file": stem,
                    "category": category,
                    "new_text": new["text"],
                    "new_type": new["type"],
                    "candidate_id": cid,
                    "candidate_terms": " | ".join(terms[:5]),
                    "candidate_ttys_or_icd_information": cid,
                    "lexical_overlap": f"{_lexical_overlap(new['text'], terms):.3f}" if terms else "",
                    "consistency_status": status,
                    "consistency_reason": reason_c,
                }
            )
            row["consistency_status"] = status

            # assertion consistency
            a_change = "unchanged" if old_a == new_a else f"{old_a}→{new_a}"
            a_status = "CONSISTENT"
            a_reason = "ok"
            if category == "B":
                if "isNegated" in new_a:
                    a_status, a_reason = "CONSISTENT", "isNegated_present"
                else:
                    a_status, a_reason = "INCONSISTENT", "missing_isNegated"
            if "isHistorical" in new_a and "isHistorical" not in old_a:
                a_reason += "; historical_added"
            assert_rows.append(
                {
                    "file": stem,
                    "category": category,
                    "old_text": old["text"],
                    "new_text": new["text"],
                    "old_assertions": json.dumps(old_a, ensure_ascii=False),
                    "new_assertions": json.dumps(new_a, ensure_ascii=False),
                    "section": "",
                    "local_context": row["line_context"],
                    "assertion_change": a_change,
                    "consistency_status": a_status,
                    "reason": a_reason,
                }
            )

        all_conflict_rows.extend(
            collect_all_conflicts(stem, text, base, args.cache_dir, doc_reps)
        )
        # Fix accepted markers using new_* fields
        for r in all_conflict_rows:
            if r["file"] != stem:
                continue
            for dr in doc_reps:
                if (
                    r["llm_text"] == dr["new_text"]
                    and r["llm_position"] == f"[{dr['new_start']},{dr['new_end']}]"
                ):
                    r["accepted_by_v10"] = "yes"
                    r["rejection_reason"] = ""
                    r["proposed_category"] = dr["category"]

    # Write TSVs
    rep_headers = [
        "file",
        "category",
        "old_start",
        "old_end",
        "old_text",
        "old_type",
        "old_candidates",
        "old_assertions",
        "new_start",
        "new_end",
        "new_text",
        "new_type",
        "new_candidates",
        "new_assertions",
        "left_context",
        "right_context",
        "llm_text",
        "llm_type",
        "replacement_reason",
        "deterministic_evidence",
        "linker_evidence",
        "assertion_evidence",
        "review_status",
        "review_notes",
    ]
    _write_tsv(analysis / "v10_replacements.tsv", replacement_rows, rep_headers)
    _write_tsv(
        analysis / "v10_candidate_consistency.tsv",
        cand_rows,
        [
            "file",
            "category",
            "new_text",
            "new_type",
            "candidate_id",
            "candidate_terms",
            "candidate_ttys_or_icd_information",
            "lexical_overlap",
            "consistency_status",
            "consistency_reason",
        ],
    )
    _write_tsv(
        analysis / "v10_assertion_consistency.tsv",
        assert_rows,
        [
            "file",
            "category",
            "old_text",
            "new_text",
            "old_assertions",
            "new_assertions",
            "section",
            "local_context",
            "assertion_change",
            "consistency_status",
            "reason",
        ],
    )
    _write_tsv(
        analysis / "v10_all_conflicts.tsv",
        all_conflict_rows,
        [
            "file",
            "v7_text",
            "v7_position",
            "v7_type",
            "v7_candidates",
            "v7_assertions",
            "llm_text",
            "llm_position",
            "llm_type",
            "overlap_relation",
            "proposed_category",
            "accepted_by_v10",
            "rejection_reason",
            "left_context",
            "right_context",
        ],
    )

    # Annotation review md + csv
    ann_csv_headers = [
        "file",
        "category",
        "line_context",
        "old_text",
        "old_position",
        "old_type",
        "old_candidates",
        "old_assertions",
        "new_text",
        "new_position",
        "new_type",
        "new_candidates",
        "new_assertions",
        "why_changed",
        "candidate_terms",
        "human_decision",
        "human_corrected_text",
        "human_corrected_type",
        "human_corrected_assertions",
        "human_corrected_candidates",
        "notes",
    ]
    ann_csv_rows = []
    md_lines = [
        "# v10 annotation review",
        "",
        "Human reviewers: fill **Human decision** only. Do not treat code gates as correctness.",
        "",
        f"Total replacements: **{len(replacement_rows)}**",
        "",
    ]
    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in replacement_rows:
        by_cat[r["category"]].append(r)

    for cat in ("A", "B", "C", "D"):
        md_lines.append(f"## Category {cat}")
        md_lines.append("")
        for r in by_cat.get(cat, []):
            terms = ""
            for cr in cand_rows:
                if (
                    cr["file"] == r["file"]
                    and cr["new_text"] == r["new_text"]
                    and cr["category"] == r["category"]
                ):
                    terms = cr["candidate_terms"]
                    break
            md_lines.extend(
                [
                    f"### Doc {r['file']} — `{r['old_text']}` → `{r['new_text']}`",
                    "",
                    f"**Full line:** {r.get('line_context', '')}",
                    "",
                    "**Previous entity:**",
                    f"- text: `{r['old_text']}`",
                    f"- position: `[{r['old_start']}, {r['old_end']}]`",
                    f"- type: `{r['old_type']}`",
                    f"- candidates: `{r['old_candidates']}`",
                    f"- assertions: `{r['old_assertions']}`",
                    "",
                    "**Proposed entity:**",
                    f"- text: `{r['new_text']}`",
                    f"- position: `[{r['new_start']}, {r['new_end']}]`",
                    f"- type: `{r['new_type']}`",
                    f"- candidates: `{r['new_candidates']}`",
                    f"- assertions: `{r['new_assertions']}`",
                    "",
                    f"**Why v10 changed it:** category {cat} / {r['replacement_reason']}",
                    f"**Candidate terms:** {terms}",
                    f"**Auto flags:** {r.get('review_notes') or '(none)'}",
                    "",
                    "Suggested human decision: ACCEPT / REJECT / MODIFY / UNSURE",
                    "",
                    "Human decision:",
                    "Human corrected text:",
                    "Human corrected type:",
                    "Human corrected assertions:",
                    "Human corrected candidates:",
                    "Notes:",
                    "",
                    "---",
                    "",
                ]
            )
            ann_csv_rows.append(
                {
                    "file": r["file"],
                    "category": cat,
                    "line_context": r.get("line_context", ""),
                    "old_text": r["old_text"],
                    "old_position": f"[{r['old_start']}, {r['old_end']}]",
                    "old_type": r["old_type"],
                    "old_candidates": r["old_candidates"],
                    "old_assertions": r["old_assertions"],
                    "new_text": r["new_text"],
                    "new_position": f"[{r['new_start']}, {r['new_end']}]",
                    "new_type": r["new_type"],
                    "new_candidates": r["new_candidates"],
                    "new_assertions": r["new_assertions"],
                    "why_changed": f"{cat}/{r['replacement_reason']}",
                    "candidate_terms": terms,
                    "human_decision": "",
                    "human_corrected_text": "",
                    "human_corrected_type": "",
                    "human_corrected_assertions": "",
                    "human_corrected_candidates": "",
                    "notes": "",
                }
            )

    (analysis / "v10_annotation_review.md").write_text("\n".join(md_lines), encoding="utf-8")
    _write_csv(analysis / "v10_annotation_review.csv", ann_csv_rows, ann_csv_headers)

    # Counts for report
    cand_status = Counter(r["consistency_status"] for r in cand_rows)
    # Preview proposed counts from offline TSV if present
    preview_path = analysis / "v10_replacement_preview.tsv"
    proposed = Counter()
    if preview_path.exists():
        with preview_path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                proposed[row.get("category", "")] += 1

    hot_docs = [f for f, n in per_doc.items() if n > 10]

    # Decision
    inconsistent_accepted = cand_status.get("INCONSISTENT", 0)
    decision = "READY FOR MANUAL REVIEW"
    fail_reasons = []
    if hard["invalid_spans"]:
        fail_reasons.append("invalid_spans")
    if hard["missing_documents"]:
        fail_reasons.append("missing_documents")
    if hard["empty_traces"]:
        fail_reasons.append("empty_traces")
    if hard["pure_additions"]:
        fail_reasons.append("pure_additions")
    if hard["unpaired_removals"]:
        fail_reasons.append("unpaired_removals")
    if hard["unexpected_modifications"]:
        fail_reasons.append("unexpected_modifications")
    if hard["malformed_json"]:
        fail_reasons.append("malformed_json")
    if inconsistent_accepted:
        fail_reasons.append("candidate_inconsistent_accepted")
    if n_base != 100 or n_sub != 100 or n_tr != 100:
        fail_reasons.append("file_count")
    if fail_reasons:
        decision = "NOT READY"

    report = [
        "# v10_llm_conflict_resolution report",
        "",
        f"documents: {n_sub}",
        f"base_v7_snapshot files: {n_base}",
        f"trace files: {n_tr}",
        "",
        "## Funnel",
        f"- conflicts considered (cache accepts scanned): {totals['conflicts_considered']}",
        f"- Category A proposed (preview): {proposed.get('A', '?')} / accepted: {cat_accepted['A']}",
        f"- Category B proposed (preview): {proposed.get('B', '?')} / accepted: {cat_accepted['B']}",
        f"- Category C proposed (preview): {proposed.get('C', '?')} / accepted: {cat_accepted['C']}",
        f"- Category D proposed (preview): {proposed.get('D', '?')} / accepted: {cat_accepted['D']}",
        f"- total replacements: {len(replacement_rows)}",
        "",
        "## Candidate consistency",
        f"- CONSISTENT: {cand_status.get('CONSISTENT', 0)}",
        f"- QUESTIONABLE: {cand_status.get('QUESTIONABLE', 0)}",
        f"- INCONSISTENT: {cand_status.get('INCONSISTENT', 0)}",
        f"- UNRESOLVED: {cand_status.get('UNRESOLVED', 0)}",
        "",
        "## Hard invariants",
        f"- invalid spans: {hard['invalid_spans']}",
        f"- missing documents: {hard['missing_documents']}",
        f"- malformed JSON: {hard['malformed_json']}",
        f"- empty traces: {hard['empty_traces']}",
        f"- pure additions: {hard['pure_additions']}",
        f"- unpaired removals: {hard['unpaired_removals']}",
        f"- unexpected modifications: {hard['unexpected_modifications']}",
        "",
        "## Replacements per document",
    ]
    for stem, n in sorted(per_doc.items(), key=lambda x: -x[1]):
        report.append(f"- file {stem}: {n}")
    if hot_docs:
        report.append("")
        report.append(f"**FLAG:** docs with >10 replacements: {', '.join(hot_docs)}")
    else:
        report.append("")
        report.append("No document exceeds 10 replacements.")
    report.extend(
        [
            "",
            "## Decision",
            "",
            decision,
            "",
        ]
    )
    if fail_reasons:
        report.append("Failure reasons: " + ", ".join(fail_reasons))
    (analysis / "v10_llm_conflict_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    # --- Phase 16 ZIPs ---
    diag_zip = ROOT / "output" / "v10_llm_conflict_resolution_full.zip"
    sub_zip = ROOT / "output" / "v10_llm_conflict_resolution_submission.zip"
    if diag_zip.exists():
        diag_zip.unlink()
    if sub_zip.exists():
        sub_zip.unlink()

    with zipfile.ZipFile(diag_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for folder in (base_dir, sub_dir, trace_dir):
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=f"{folder.name}/{path.name}")
        for name in (
            "v10_llm_conflict_report.md",
            "v10_replacements.tsv",
            "v10_candidate_consistency.tsv",
            "v10_assertion_consistency.tsv",
            "v10_annotation_review.md",
            "v10_annotation_review.csv",
            "v10_all_conflicts.tsv",
            "v10_smoke_validation.md",
            "v10_full_run_starting_state.md",
        ):
            p = analysis / name
            if p.exists():
                zf.write(p, arcname=f"analysis/{name}")

    with zipfile.ZipFile(sub_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(sub_dir.glob("*.json")):
            zf.write(path, arcname=f"output/{path.name}")

    # Validate ZIPs
    def validate_comp_zip(path: Path) -> dict[str, Any]:
        bad = {"json": 0, "offset": 0, "type": 0, "malformed": 0}
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            jsons = [n for n in names if n.endswith(".json")]
            bad["json"] = len(jsons)
            for name in jsons:
                raw = zf.read(name)
                try:
                    ents = json.loads(raw.decode("utf-8"))
                except Exception:  # noqa: BLE001
                    bad["malformed"] += 1
                    continue
                stem = Path(name).stem
                text = (args.input_dir / f"{stem}.txt").read_text(encoding="utf-8")
                for e in ents:
                    s, ed = e["position"]
                    if text[s:ed] != e["text"]:
                        bad["offset"] += 1
                    if e["type"] not in VALID_TYPES:
                        bad["type"] += 1
        return bad

    diag_names_zip = []
    with zipfile.ZipFile(diag_zip) as zf:
        diag_names_zip = zf.namelist()
    comp_val = validate_comp_zip(sub_zip)

    zip_report = {
        "diagnostic": {
            "path": str(diag_zip),
            "size": diag_zip.stat().st_size,
            "sha256": _sha256_file(diag_zip),
            "entries": len(diag_names_zip),
            "has_base": any(n.startswith("base_v7_snapshot/") for n in diag_names_zip),
            "has_sub": any(n.startswith("submission/") for n in diag_names_zip),
            "has_trace": any(n.startswith("trace/") for n in diag_names_zip),
        },
        "competition": {
            "path": str(sub_zip),
            "size": sub_zip.stat().st_size,
            "sha256": _sha256_file(sub_zip),
            "json_files": comp_val["json"],
            "offset_mismatches": comp_val["offset"],
            "invalid_types": comp_val["type"],
            "malformed_files": comp_val["malformed"],
        },
        "decision": decision,
        "replacements": len(replacement_rows),
        "category_counts": dict(cat_accepted),
        "hard": hard,
        "file_counts": {"base": n_base, "submission": n_sub, "trace": n_tr},
    }
    (analysis / "v10_finalize_summary.json").write_text(
        json.dumps(zip_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(zip_report, ensure_ascii=False, indent=2))
    print(f"\nDecision: {decision}")
    return 0 if decision == "READY FOR MANUAL REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
