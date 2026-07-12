"""Compare openrouter_schema_teacher diagnostic pseudo-gold vs frozen v7/v10.

EXTERNAL_API_DIAGNOSTIC_ONLY — analysis only.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from modules.core.config import ProjectPaths

ROOT = ProjectPaths().root
NEGATION_CUES = re.compile(
    r"\b(không|ko|chẳng|chả|never|no|without|phủ định)\b", re.I
)
PROCEDURE_CUES = re.compile(
    r"(phẫu thuật|đặt stent|đặt shunt|đặt catheter|can thiệp|dẫn lưu|truyền dịch|"
    r"truyền máu|tiêm|cắt bỏ|ghép|chọc|stent)",
    re.I,
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


def span_key(e: dict[str, Any]) -> tuple[int, int, str]:
    return (e["start"], e["end"], e["type"])


def exact_match_set(ents: list[dict[str, Any]]) -> set[tuple[int, int, str, str]]:
    return {(e["start"], e["end"], e["type"], e["text"]) for e in ents}


def overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return min(a["end"], b["end"]) > max(a["start"], b["start"])


def compare_pair(
    teacher: list[dict[str, Any]], other: list[dict[str, Any]], label: str
) -> dict[str, Any]:
    t_exact = exact_match_set(teacher)
    o_exact = exact_match_set(other)
    exact_agree = len(t_exact & o_exact)
    # overlap agreement: teacher ents that overlap same-type other
    overlap_n = 0
    for te in teacher:
        if any(overlap(te, oe) and te["type"] == oe["type"] for oe in other):
            overlap_n += 1
    additions = len(t_exact - o_exact)
    removals = len(o_exact - t_exact)
    # type/boundary/assertion/candidate changes on overlapping spans
    type_changes = 0
    boundary_changes = 0
    assertion_changes = 0
    candidate_changes = 0
    used = set()
    for te in teacher:
        matches = [
            oe
            for oe in other
            if overlap(te, oe) and id(oe) not in used
        ]
        if not matches:
            continue
        oe = matches[0]
        used.add(id(oe))
        if te["type"] != oe["type"]:
            type_changes += 1
        if (te["start"], te["end"]) != (oe["start"], oe["end"]):
            boundary_changes += 1
        if sorted(te["assertions"]) != sorted(oe["assertions"]):
            assertion_changes += 1
        if sorted(map(str, te["candidates"])) != sorted(map(str, oe["candidates"])):
            candidate_changes += 1
    return {
        "label": label,
        "teacher_n": len(teacher),
        "other_n": len(other),
        "exact_agreement": exact_agree,
        "overlap_agreement": overlap_n,
        "additions": additions,
        "removals": removals,
        "type_changes": type_changes,
        "boundary_changes": boundary_changes,
        "assertion_changes": assertion_changes,
        "candidate_changes": candidate_changes,
        "teacher_by_type": dict(Counter(e["type"] for e in teacher)),
        "other_by_type": dict(Counter(e["type"] for e in other)),
    }


def schema_metrics(
    teacher_dir: Path,
    v7_dir: Path,
    procedure_audit: Path,
) -> dict[str, Any]:
    procedure_spans: dict[str, set[tuple[int, int]]] = defaultdict(set)
    if procedure_audit.exists():
        with procedure_audit.open(encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                if row.get("risk_status") != "LIKELY_PROCEDURE_NOT_TEST":
                    continue
                fid = str(row["file"]).replace(".json", "")
                start, end = map(int, row["position"].split("-"))
                procedure_spans[fid].add((start, end))

    files = sorted(p.stem for p in teacher_dir.glob("*.json"))
    total_teacher = 0
    by_type: Counter[str] = Counter()
    proc_rejected = 0
    proc_total = sum(len(v) for v in procedure_spans.values())
    test_names = 0
    paired_lab = 0
    overlong_split_proxy = 0
    sym_dx_collisions = 0
    negation_inside = 0
    maximal_drug_proxy = 0
    multi_icd = 0
    family_n = 0
    dx_cand_dist: Counter[int] = Counter()
    drug_cand_dist: Counter[int] = Counter()

    for fid in files:
        teacher = load_entities(teacher_dir / f"{fid}.json")
        total_teacher += len(teacher)
        by_type.update(e["type"] for e in teacher)
        # procedure rejection: procedure span from v7 audit not present as TÊN_XÉT_NGHIỆM
        for s, e in procedure_spans.get(fid, set()):
            still = any(
                t["type"] == "TÊN_XÉT_NGHIỆM" and t["start"] == s and t["end"] == e
                for t in teacher
            )
            if not still:
                proc_rejected += 1
        names = [t for t in teacher if t["type"] == "TÊN_XÉT_NGHIỆM"]
        results = [t for t in teacher if t["type"] == "KẾT_QUẢ_XÉT_NGHIỆM"]
        test_names += len(names)
        for n in names:
            if any(
                abs(((n["start"] + n["end"]) / 2) - ((r["start"] + r["end"]) / 2)) < 80
                for r in results
            ):
                paired_lab += 1
        # overlong result proxy: results with length > 40 that look clause-like
        for r in results:
            if len(r["text"]) > 60:
                overlong_split_proxy += 1
        symptoms = [t for t in teacher if t["type"] == "TRIỆU_CHỨNG"]
        diagnoses = [t for t in teacher if t["type"] == "CHẨN_ĐOÁN"]
        for s in symptoms:
            for d in diagnoses:
                if overlap(s, d):
                    sym_dx_collisions += 1
            if NEGATION_CUES.search(s["text"]):
                negation_inside += 1
        for drug in [t for t in teacher if t["type"] == "THUỐC"]:
            # maximal proxy: contains digit or dose-like token
            if re.search(r"\d|mg|ml|viên|ống|lần|ngày", drug["text"], re.I):
                maximal_drug_proxy += 1
        for d in diagnoses:
            n = len(d.get("candidates") or [])
            dx_cand_dist[n] += 1
            if n > 1:
                multi_icd += 1
        for drug in [t for t in teacher if t["type"] == "THUỐC"]:
            drug_cand_dist[len(drug.get("candidates") or [])] += 1
        for t in teacher:
            if "isFamily" in (t.get("assertions") or []):
                family_n += 1

    v7_total = 0
    for fid in files:
        v7_total += len(load_entities(v7_dir / f"{fid}.json"))

    return {
        "n_files": len(files),
        "teacher_total_entities": total_teacher,
        "v7_total_entities": v7_total,
        "density_ratio_vs_v7": (total_teacher / v7_total) if v7_total else None,
        "by_type": dict(by_type),
        "procedure_as_test_total_audit": proc_total,
        "procedure_as_test_rejected": proc_rejected,
        "test_name_count": test_names,
        "paired_test_name_result": paired_lab,
        "overlong_result_spans": overlong_split_proxy,
        "symptom_diagnosis_collisions": sym_dx_collisions,
        "symptoms_with_negation_cue_inside": negation_inside,
        "drugs_maximal_proxy": maximal_drug_proxy,
        "diagnoses_multi_icd": multi_icd,
        "isFamily_count": family_n,
        "diagnosis_candidate_count_distribution": {
            str(k): v for k, v in sorted(dx_cand_dist.items())
        },
        "drug_candidate_count_distribution": {
            str(k): v for k, v in sorted(drug_cand_dist.items())
        },
    }


def write_comparison_tsv(
    rows: list[dict[str, Any]], path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, delimiter="\t")
        w.writeheader()
        for row in rows:
            flat = {}
            for k, v in row.items():
                flat[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
            w.writerow(flat)


def run_comparison(
    teacher_dir: Path | None = None,
    v7_dir: Path | None = None,
    v10_dir: Path | None = None,
    analysis_dir: Path | None = None,
) -> dict[str, Any]:
    teacher_dir = teacher_dir or (
        ROOT / "output" / "openrouter_schema_teacher" / "diagnostic_pseudo_gold"
    )
    v7_dir = v7_dir or (
        ROOT / "output" / "v10_llm_conflict_resolution" / "base_v7_snapshot"
    )
    v10_dir = v10_dir or (
        ROOT / "output" / "v10_llm_conflict_resolution" / "submission"
    )
    analysis_dir = analysis_dir or (ROOT / "analysis" / "openrouter_teacher")
    analysis_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        set(p.stem for p in teacher_dir.glob("*.json"))
        & set(p.stem for p in v7_dir.glob("*.json"))
    )
    rows = []
    agg_v7 = []
    agg_v10 = []
    for fid in files:
        teacher = load_entities(teacher_dir / f"{fid}.json")
        v7 = load_entities(v7_dir / f"{fid}.json")
        v10 = load_entities(v10_dir / f"{fid}.json")
        c7 = compare_pair(teacher, v7, "v7")
        c10 = compare_pair(teacher, v10, "v10")
        rows.append({"file": fid, **{f"v7_{k}": v for k, v in c7.items()}, **{f"v10_{k}": v for k, v in c10.items()}})
        agg_v7.append(c7)
        agg_v10.append(c10)

    write_comparison_tsv(rows, analysis_dir / "comparison_v7_v10.tsv")
    metrics = schema_metrics(
        teacher_dir,
        v7_dir,
        ROOT / "analysis" / "schema_audit" / "test_name_audit.tsv",
    )
    metrics["pairwise_summary_v7"] = {
        "exact_agreement_sum": sum(x["exact_agreement"] for x in agg_v7),
        "overlap_agreement_sum": sum(x["overlap_agreement"] for x in agg_v7),
        "additions_sum": sum(x["additions"] for x in agg_v7),
        "removals_sum": sum(x["removals"] for x in agg_v7),
    }
    metrics["pairwise_summary_v10"] = {
        "exact_agreement_sum": sum(x["exact_agreement"] for x in agg_v10),
        "overlap_agreement_sum": sum(x["overlap_agreement"] for x in agg_v10),
        "additions_sum": sum(x["additions"] for x in agg_v10),
        "removals_sum": sum(x["removals"] for x in agg_v10),
    }
    (analysis_dir / "schema_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md = [
        "# Schema metrics — openrouter_schema_teacher",
        "",
        "**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`",
        "",
        "```json",
        json.dumps(metrics, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    (analysis_dir / "schema_metrics.md").write_text("\n".join(md), encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--teacher-dir", type=Path, default=None)
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=None,
        help="Write comparison artifacts here (default: analysis/openrouter_teacher)",
    )
    args = parser.parse_args()
    metrics = run_comparison(
        teacher_dir=args.teacher_dir,
        analysis_dir=args.analysis_dir,
    )
    print(json.dumps({k: metrics[k] for k in ("n_files", "teacher_total_entities", "by_type") if k in metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
