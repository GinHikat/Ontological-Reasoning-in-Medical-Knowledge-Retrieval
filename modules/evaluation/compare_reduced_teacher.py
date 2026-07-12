"""Compare openrouter_schema_teacher_reduced vs archived frontier gold.

EXTERNAL_API_DIAGNOSTIC_ONLY — analysis only.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from modules.core.config import ProjectPaths

ROOT = ProjectPaths().root
ARCHIVE_GOLD = (
    ROOT
    / "archives"
    / "openrouter_schema_teacher_free_2026-07-12"
    / "diagnostic_pseudo_gold"
)
DEFAULT_REDUCED = ROOT / "output" / "openrouter_schema_teacher_reduced" / "final"
ANALYSIS = ROOT / "analysis" / "openrouter_reduced"

PROCEDURE_CUES = (
    "phẫu thuật",
    "đặt stent",
    "đặt shunt",
    "đặt catheter",
    "can thiệp",
    "dẫn lưu",
    "truyền dịch",
    "truyền máu",
    "tiêm",
    "cắt bỏ",
    "ghép",
    "stent",
    "shunt",
)


def load_entities(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    out = []
    for e in data:
        pos = e.get("position") or [e.get("start"), e.get("end")]
        out.append(
            {
                "text": e.get("text") or "",
                "type": e.get("type") or "",
                "assertions": list(e.get("assertions") or []),
                "candidates": list(e.get("candidates") or []),
                "start": int(pos[0]),
                "end": int(pos[1]),
            }
        )
    return out


def exact_key(e: dict[str, Any]) -> tuple:
    return (e["start"], e["end"], e["type"], e["text"])


def overlaps(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return min(a["end"], b["end"]) > max(a["start"], b["start"])


def compare_doc(
    reduced: list[dict[str, Any]], gold: list[dict[str, Any]]
) -> dict[str, Any]:
    r_exact = {exact_key(e) for e in reduced}
    g_exact = {exact_key(e) for e in gold}
    exact_agree = len(r_exact & g_exact)
    g_used: set[int] = set()
    overlap_agree = 0
    type_agree = 0
    assert_agree = 0
    cand_agree = 0
    cand_pairs = 0
    type_changes = 0
    assert_changes = 0
    cand_changes = 0

    # exact first
    g_by = {exact_key(g): i for i, g in enumerate(gold)}
    matched_r: set[int] = set()
    for i, r in enumerate(reduced):
        k = exact_key(r)
        if k in g_by:
            gi = g_by[k]
            g_used.add(gi)
            matched_r.add(i)
            overlap_agree += 1
            type_agree += 1
            g = gold[gi]
            if set(r["assertions"]) == set(g["assertions"]):
                assert_agree += 1
            else:
                assert_changes += 1
            if r["type"] in {"CHẨN_ĐOÁN", "THUỐC"}:
                cand_pairs += 1
                if list(r["candidates"]) == list(g["candidates"]):
                    cand_agree += 1
                else:
                    cand_changes += 1

    for i, r in enumerate(reduced):
        if i in matched_r:
            continue
        best = None
        for gi, g in enumerate(gold):
            if gi in g_used:
                continue
            if overlaps(r, g):
                score = 1.0 if r["type"] == g["type"] else 0.0
                score += min(r["end"], g["end"]) - max(r["start"], g["start"])
                if best is None or score > best[0]:
                    best = (score, gi, g)
        if best is None:
            continue
        _, gi, g = best
        g_used.add(gi)
        overlap_agree += 1
        if r["type"] == g["type"]:
            type_agree += 1
            if set(r["assertions"]) == set(g["assertions"]):
                assert_agree += 1
            else:
                assert_changes += 1
            if r["type"] in {"CHẨN_ĐOÁN", "THUỐC"}:
                cand_pairs += 1
                if list(r["candidates"]) == list(g["candidates"]):
                    cand_agree += 1
                else:
                    cand_changes += 1
        else:
            type_changes += 1

    additions = len(r_exact - g_exact)
    removals = len(g_exact - r_exact)
    return {
        "reduced_n": len(reduced),
        "gold_n": len(gold),
        "exact_agree": exact_agree,
        "overlap_agree": overlap_agree,
        "type_agree": type_agree,
        "assert_agree": assert_agree,
        "cand_agree": cand_agree,
        "cand_pairs": cand_pairs,
        "additions": additions,
        "removals": removals,
        "type_changes": type_changes,
        "assert_changes": assert_changes,
        "cand_changes": cand_changes,
        "gold_covered_overlap": len(g_used),
    }


def procedure_as_test_count(ents: list[dict[str, Any]]) -> int:
    n = 0
    for e in ents:
        if e["type"] != "TÊN_XÉT_NGHIỆM":
            continue
        t = (e["text"] or "").lower()
        if any(c in t for c in PROCEDURE_CUES):
            n += 1
    return n


def lab_split_ok(reduced: list[dict[str, Any]], gold: list[dict[str, Any]]) -> tuple[int, int]:
    lab = {"TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM"}
    gold_lab = [g for g in gold if g["type"] in lab]
    ok = 0
    for g in gold_lab:
        if any(
            r["type"] == g["type"] and overlaps(r, g) for r in reduced
        ):
            ok += 1
    return ok, len(gold_lab)


def compare_dirs(
    reduced_dir: Path,
    gold_dir: Path,
    doc_ids: list[str] | None = None,
) -> dict[str, Any]:
    if doc_ids is None:
        doc_ids = sorted(
            {p.stem for p in gold_dir.glob("*.json")}
            & {p.stem for p in reduced_dir.glob("*.json")},
            key=lambda x: int(x),
        )
    rows = []
    totals: Counter = Counter()
    type_red: Counter = Counter()
    type_gold: Counter = Counter()
    proc_red = 0
    proc_gold = 0
    lab_ok = lab_n = 0
    for doc in doc_ids:
        red = load_entities(reduced_dir / f"{doc}.json")
        gold = load_entities(gold_dir / f"{doc}.json")
        m = compare_doc(red, gold)
        m["document_id"] = doc
        rows.append(m)
        for k, v in m.items():
            if k == "document_id":
                continue
            totals[k] += v
        type_red.update(e["type"] for e in red)
        type_gold.update(e["type"] for e in gold)
        proc_red += procedure_as_test_count(red)
        proc_gold += procedure_as_test_count(gold)
        a, b = lab_split_ok(red, gold)
        lab_ok += a
        lab_n += b

    gold_n = totals["gold_n"] or 1
    overlap_pairs = totals["overlap_agree"] or 1
    cand_pairs = totals["cand_pairs"] or 1
    summary = {
        "n_docs": len(doc_ids),
        "total_entities_reduced": totals["reduced_n"],
        "total_entities_gold": totals["gold_n"],
        "exact_span_agreement": totals["exact_agree"] / gold_n,
        "overlap_agreement": totals["gold_covered_overlap"] / gold_n,
        "type_agreement_on_overlap": totals["type_agree"] / overlap_pairs,
        "assertion_agreement_on_overlap": totals["assert_agree"] / overlap_pairs,
        "candidate_agreement": totals["cand_agree"] / cand_pairs,
        "additions": totals["additions"],
        "removals": totals["removals"],
        "type_changes": totals["type_changes"],
        "assertion_changes": totals["assert_changes"],
        "candidate_changes": totals["cand_changes"],
        "procedure_as_test_reduced": proc_red,
        "procedure_as_test_gold": proc_gold,
        "lab_split_agreement": (lab_ok / lab_n) if lab_n else 1.0,
        "type_distribution_reduced": dict(type_red),
        "type_distribution_gold": dict(type_gold),
        "doc_ids": doc_ids,
    }
    return {"summary": summary, "rows": rows, "totals": dict(totals)}


def write_reports(result: dict[str, Any], stem: str) -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    tsv = ANALYSIS / f"{stem}.tsv"
    fields = [
        "document_id",
        "reduced_n",
        "gold_n",
        "exact_agree",
        "overlap_agree",
        "type_agree",
        "assert_agree",
        "cand_agree",
        "cand_pairs",
        "additions",
        "removals",
        "type_changes",
        "assert_changes",
        "cand_changes",
        "gold_covered_overlap",
    ]
    with tsv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        for row in result["rows"]:
            w.writerow({k: row.get(k, "") for k in fields})

    s = result["summary"]
    md = [
        f"# Comparison — `{stem}`",
        "",
        "**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`",
        "",
        f"- Docs compared: **{s['n_docs']}**",
        f"- Reduced entities: **{s['total_entities_reduced']}**",
        f"- Archived frontier entities: **{s['total_entities_gold']}**",
        f"- Exact-span agreement (recall vs gold): **{s['exact_span_agreement']:.4f}**",
        f"- Overlap agreement (recall vs gold): **{s['overlap_agreement']:.4f}**",
        f"- Type agreement on overlaps: **{s['type_agreement_on_overlap']:.4f}**",
        f"- Assertion agreement on overlaps: **{s['assertion_agreement_on_overlap']:.4f}**",
        f"- Candidate agreement: **{s['candidate_agreement']:.4f}**",
        f"- Additions / removals: **{s['additions']} / {s['removals']}**",
        f"- Procedure-as-test (reduced / gold): **{s['procedure_as_test_reduced']} / {s['procedure_as_test_gold']}**",
        f"- Lab split agreement: **{s['lab_split_agreement']:.4f}**",
        "",
        "## Type distribution",
        "",
        "| Type | Reduced | Gold |",
        "|------|--------:|-----:|",
    ]
    types = sorted(
        set(s["type_distribution_reduced"]) | set(s["type_distribution_gold"])
    )
    for t in types:
        md.append(
            f"| {t} | {s['type_distribution_reduced'].get(t, 0)} | "
            f"{s['type_distribution_gold'].get(t, 0)} |"
        )
    md.append("")
    (ANALYSIS / f"{stem}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reduced-dir", type=Path, default=DEFAULT_REDUCED)
    parser.add_argument("--gold-dir", type=Path, default=ARCHIVE_GOLD)
    parser.add_argument("--docs", nargs="*", default=None)
    parser.add_argument("--stem", default="comparison_full")
    args = parser.parse_args()
    result = compare_dirs(args.reduced_dir, args.gold_dir, args.docs)
    write_reports(result, args.stem)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
