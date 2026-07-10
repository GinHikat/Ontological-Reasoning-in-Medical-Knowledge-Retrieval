from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.components.postprocessing.ontology_drug_recall import (  # noqa: E402
    OntologyDrugRecallPostProcessor,
)
from modules.core.constants import TARGET_LABEL_DRUG  # noqa: E402
from modules.core.ids import normalize_rxcui  # noqa: E402
from modules.core.schemas import Document  # noqa: E402
from modules.evaluation.analyze_outputs import resolve_submission_dir  # noqa: E402
from modules.evaluation.compare_pipeline_outputs import (  # noqa: E402
    _ctx,
    _write_tsv,
)

OFFICIAL_TYPES = {
    "CHẨN_ĐOÁN",
    "THUỐC",
    "TÊN_XÉT_NGHIỆM",
    "TRIỆU_CHỨNG",
    "KẾT_QUẢ_XÉT_NGHIỆM",
}


def _load_map(output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    submission_dir = resolve_submission_dir(output_dir)
    for path in sorted(submission_dir.glob("*.json")):
        result[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_ontology_index(input_dir: Path) -> dict[tuple[str, int, int], dict[str, Any]]:
    proc = OntologyDrugRecallPostProcessor(track_rxcui_sets=True)
    index: dict[tuple[str, int, int], dict[str, Any]] = {}
    for path in sorted(input_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        doc = Document(doc_id=path.stem, text=text)
        for m in proc.apply(doc, []):
            if m.label != TARGET_LABEL_DRUG:
                continue
            if m.span.start is None or m.span.end is None:
                continue
            index[(path.stem, int(m.span.start), int(m.span.end))] = {
                "text": m.text,
                "alias": (m.metadata or {}).get("alias", ""),
                "match": (m.metadata or {}).get("match", ""),
                "preset": list((m.metadata or {}).get("preset_rxcui_candidates") or []),
            }
    return index


def compare_same_env(
    v7_dir: Path,
    v8_dir: Path,
    input_dir: Path,
    analysis_dir: Path,
    onto_index: dict[tuple[str, int, int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    analysis_dir.mkdir(parents=True, exist_ok=True)
    v7 = _load_map(v7_dir)
    v8 = _load_map(v8_dir)
    if onto_index is None:
        print("Building ontology index...")
        onto_index = build_ontology_index(input_dir)

    failures: list[str] = []
    if set(v7) != set(v8):
        failures.append(f"file set mismatch: {sorted(set(v7) ^ set(v8))[:10]}")

    stats = Counter()
    rescued_rows: list[dict[str, Any]] = []
    unrescued_rows: list[dict[str, Any]] = []
    changed_existing_rows: list[dict[str, Any]] = []

    for stem in sorted(set(v7) | set(v8)):
        text_path = input_dir / f"{stem}.txt"
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        b_ents = v7.get(stem, [])
        c_ents = v8.get(stem, [])
        if len(b_ents) != len(c_ents):
            failures.append(f"{stem}: entity count {len(b_ents)} vs {len(c_ents)}")
            continue
        for idx, (b, c) in enumerate(zip(b_ents, c_ents)):
            b_pos = b.get("position") or [None, None]
            c_pos = c.get("position") or [None, None]
            if (
                b.get("text") != c.get("text")
                or b_pos != c_pos
                or b.get("type") != c.get("type")
                or list(b.get("assertions") or []) != list(c.get("assertions") or [])
            ):
                failures.append(f"{stem}[{idx}]: identity/assertion mismatch")
                stats["identity_failures"] += 1
                continue

            b_cand = [str(x) for x in (b.get("candidates") or [])]
            c_cand = [str(x) for x in (c.get("candidates") or [])]

            if b.get("type") == "CHẨN_ĐOÁN" and b_cand != c_cand:
                failures.append(
                    f"{stem}[{idx}]: diagnosis candidates {b_cand} -> {c_cand}"
                )
                stats["diagnosis_candidate_changes"] += 1

            if b.get("type") != "THUỐC":
                if b_cand != c_cand:
                    failures.append(
                        f"{stem}[{idx}]: non-drug candidates {b_cand} -> {c_cand}"
                    )
                continue

            stats["total_drugs"] += 1
            if b_cand:
                stats["v7_linked"] += 1
            else:
                stats["v7_unlinked"] += 1
            if c_cand:
                stats["v8_linked"] += 1
            else:
                stats["v8_unlinked"] += 1

            start, end = int(b_pos[0] or 0), int(b_pos[1] or 0)
            left, right = _ctx(text, start, end)
            onto = onto_index.get((stem, start, end), {})

            if b_cand and c_cand == b_cand:
                stats["existing_preserved"] += 1
            elif b_cand and c_cand != b_cand:
                stats["existing_changed"] += 1
                if not c_cand:
                    stats["existing_removed"] += 1
                changed_existing_rows.append(
                    {
                        "file": stem,
                        "start": start,
                        "end": end,
                        "text": b.get("text", ""),
                        "v7_candidate": "|".join(b_cand),
                        "v8_candidate": "|".join(c_cand),
                        "left_context": left,
                        "right_context": right,
                    }
                )
                failures.append(
                    f"{stem}[{idx}]: existing drug candidate changed "
                    f"{b_cand} -> {c_cand}"
                )
            elif (not b_cand) and c_cand:
                stats["newly_rescued"] += 1
                kind = "unknown"
                if len(c_cand) == 1:
                    # Heuristic provenance classification from ontology index / span
                    if onto and len(
                        {
                            normalize_rxcui(x)
                            for x in onto.get("preset", [])
                            if normalize_rxcui(x)
                        }
                    ) == 1:
                        kind = "direct_preset_rescue"
                    else:
                        kind = "transferred_or_other_rescue"
                rescued_rows.append(
                    {
                        "file": stem,
                        "start": start,
                        "end": end,
                        "text": b.get("text", ""),
                        "v7_candidate": "",
                        "v8_candidate": "|".join(c_cand),
                        "rescue_kind": kind,
                        "onto_alias": onto.get("alias", ""),
                        "onto_match": onto.get("match", ""),
                        "onto_preset": "|".join(
                            str(x) for x in (onto.get("preset") or [])
                        ),
                        "left_context": left,
                        "right_context": right,
                    }
                )
            elif (not b_cand) and (not c_cand):
                stats["still_unlinked"] += 1
                unrescued_rows.append(
                    {
                        "file": stem,
                        "start": start,
                        "end": end,
                        "text": b.get("text", ""),
                        "onto_alias": onto.get("alias", ""),
                        "onto_match": onto.get("match", ""),
                        "onto_preset": "|".join(
                            str(x) for x in (onto.get("preset") or [])
                        ),
                        "left_context": left,
                        "right_context": right,
                    }
                )

    _write_tsv(
        analysis_dir / "v8_rescued_drugs.tsv",
        rescued_rows,
        [
            "file",
            "start",
            "end",
            "text",
            "v7_candidate",
            "v8_candidate",
            "rescue_kind",
            "onto_alias",
            "onto_match",
            "onto_preset",
            "left_context",
            "right_context",
        ],
    )
    _write_tsv(
        analysis_dir / "v8_unrescued_drugs.tsv",
        unrescued_rows,
        [
            "file",
            "start",
            "end",
            "text",
            "onto_alias",
            "onto_match",
            "onto_preset",
            "left_context",
            "right_context",
        ],
    )
    if changed_existing_rows:
        _write_tsv(
            analysis_dir / "v8_rescue_illegal_candidate_changes.tsv",
            changed_existing_rows,
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

    hard_ok = (
        not failures
        and stats["existing_changed"] == 0
        and stats["existing_removed"] == 0
    )
    summary = {
        "v7_dir": str(v7_dir),
        "v8_dir": str(v8_dir),
        "hard_invariants_pass": hard_ok,
        "failures": failures[:50],
        "failure_count": len(failures),
        "stats": dict(stats),
        "rescued_rows": rescued_rows,
        "unrescued_rows": unrescued_rows,
    }
    (analysis_dir / "v8_candidate_rescue_compare_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def write_report(summary: dict[str, Any], analysis_dir: Path) -> None:
    s = summary["stats"]
    lines = [
        "# V8 Candidate Rescue Report",
        "",
        "## Same-environment causal comparison",
        "",
        f"- v7: `{summary['v7_dir']}`",
        f"- v8: `{summary['v8_dir']}`",
        f"- hard invariants pass: **{summary['hard_invariants_pass']}**",
        f"- failure_count: {summary['failure_count']}",
        "",
        "## Drug linking",
        "",
        f"- Total drugs: {s.get('total_drugs', 0)}",
        f"- Same-env v7 linked: {s.get('v7_linked', 0)}",
        f"- Same-env v7 unlinked: {s.get('v7_unlinked', 0)}",
        f"- V8 linked: {s.get('v8_linked', 0)}",
        f"- V8 unlinked: {s.get('v8_unlinked', 0)}",
        f"- Newly rescued drugs: **{s.get('newly_rescued', 0)}**",
        f"- Existing candidates preserved: {s.get('existing_preserved', 0)}",
        f"- Existing candidates changed: **{s.get('existing_changed', 0)}** (MUST BE 0)",
        f"- Existing candidates removed: **{s.get('existing_removed', 0)}** (MUST BE 0)",
        f"- Still unlinked: {s.get('still_unlinked', 0)}",
        "",
        "## Rescued examples",
        "",
    ]
    for row in summary.get("rescued_rows") or []:
        lines.append(
            f"- `{row['file']}` [{row['start']},{row['end']}] `{row['text']}` "
            f"-> [{row['v8_candidate']}] ({row['rescue_kind']}; "
            f"alias={row.get('onto_alias','')})"
        )
    if not summary.get("rescued_rows"):
        lines.append("- (none)")
    lines.append("")
    lines.append("## Unrescued examples")
    lines.append("")
    for row in (summary.get("unrescued_rows") or [])[:20]:
        lines.append(
            f"- `{row['file']}` [{row['start']},{row['end']}] `{row['text']}` "
            f"(onto_alias={row.get('onto_alias','')}; preset={row.get('onto_preset','')})"
        )
    if not summary.get("unrescued_rows"):
        lines.append("- (none)")
    lines.append("")
    (analysis_dir / "v8_candidate_rescue_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def write_decision(summary: dict[str, Any], analysis_dir: Path) -> str:
    s = summary["stats"]
    hard_ok = summary["hard_invariants_pass"]
    rescued = int(s.get("newly_rescued", 0))
    reasons: list[str] = []
    if not hard_ok:
        reasons.append("hard same-env invariants failed")
    if int(s.get("existing_changed", 0)) > 0:
        reasons.append("existing non-empty drug candidates changed")
    if int(s.get("existing_removed", 0)) > 0:
        reasons.append("existing non-empty drug candidates removed")
    if rescued == 0:
        reasons.append("0 newly rescued drugs (no-op ablation)")

    if hard_ok and rescued >= 1:
        decision = "READY FOR REVIEW"
    else:
        decision = "NOT READY TO SUBMIT"

    lines = [
        "# V8 Candidate Rescue — Submission Decision",
        "",
        f"## Decision: **{decision}**",
        "",
        "### Hard checks",
        "",
        f"- hard invariants pass: {hard_ok}",
        f"- newly rescued drugs: {rescued}",
        f"- existing candidates changed: {s.get('existing_changed', 0)}",
        f"- existing candidates removed: {s.get('existing_removed', 0)}",
        "",
    ]
    if reasons:
        lines.append("### Blocking reasons")
        lines.append("")
        for r in reasons:
            lines.append(f"- {r}")
        lines.append("")
    lines.append(
        "Do not auto-declare READY TO SUBMIT; ZIP inspection is still required."
    )
    lines.append("")
    (analysis_dir / "v8_candidate_rescue_submission_decision.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return decision


def parse_trace_provenance(trace_dir: Path) -> tuple[list[dict], list[dict], Counter]:
    """Extract rescue/provenance diagnostics from linker-stage trace text."""
    transfers: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    counts: Counter = Counter()
    if not trace_dir.exists():
        return transfers, rejections, counts

    for path in sorted(trace_dir.glob("*_trace.txt")):
        stem = path.name.replace("_trace.txt", "")
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Count rescue kinds from linker diagnostics blocks
        for kind in (
            "direct_preset_rescue",
            "transferred_preset_rescue",
            "v7_candidate_preserved",
            "unlinked_after_v7_and_rescue",
        ):
            counts[kind] += text.count(f"drug_link_rescue_kind: {kind}") + (
                text.count(f"drug_link: {kind}") if kind.startswith("v7_") or kind.startswith("unlinked") else 0
            )
        counts["preset_rescue"] += text.count("drug_link: preset_rescue")
        counts["conflict"] += text.count("ontology_drug_evidence_conflict: True")
        counts["transferred_meta"] += text.count(
            "ontology_drug_evidence_transferred: True"
        )

        # Pull transferred donor lines near THUỐC entities when present
        # Lightweight line scan for transferred evidence blocks
        lines = text.splitlines()
        current_ent: dict[str, Any] = {}
        for i, line in enumerate(lines):
            if ' - "' in line and "(" in line and ")" in line:
                # e.g. - "coumadin 3mg" [10, 22] (THUỐC)
                current_ent = {"file": stem, "raw": line.strip()}
            if "drug_link_rescue_kind: transferred_preset_rescue" in line:
                row = {
                    "file": stem,
                    "entity_line": current_ent.get("raw", ""),
                    "rescue_kind": "transferred_preset_rescue",
                }
                # look ahead for donor fields
                for j in range(i, min(i + 20, len(lines))):
                    if "ontology_drug_donor_text:" in lines[j]:
                        row["donor_text"] = lines[j].split(":", 1)[-1].strip()
                    if "ontology_drug_donor_alias:" in lines[j]:
                        row["donor_alias"] = lines[j].split(":", 1)[-1].strip()
                    if "transferred_preset_rxcui_candidates:" in lines[j]:
                        row["rxcui"] = lines[j].split(":", 1)[-1].strip()
                    if "final_candidates:" in lines[j]:
                        row["final_candidates"] = lines[j].split(":", 1)[-1].strip()
                transfers.append(row)
            if "drug_link_rescue_kind: direct_preset_rescue" in line:
                row = {
                    "file": stem,
                    "entity_line": current_ent.get("raw", ""),
                    "rescue_kind": "direct_preset_rescue",
                }
                for j in range(i, min(i + 15, len(lines))):
                    if "alias:" in lines[j] and "donor" not in lines[j]:
                        row["alias"] = lines[j].split(":", 1)[-1].strip()
                    if "preset_rxcui_candidates:" in lines[j]:
                        row["rxcui"] = lines[j].split(":", 1)[-1].strip()
                    if "final_candidates:" in lines[j]:
                        row["final_candidates"] = lines[j].split(":", 1)[-1].strip()
                transfers.append(row)
            if "ontology_drug_evidence_conflict: True" in line:
                rejections.append(
                    {
                        "file": stem,
                        "entity_line": current_ent.get("raw", ""),
                        "reason": "conflicting_donors",
                    }
                )
    return transfers, rejections, counts


def validate_traces(trace_dir: Path) -> dict[str, Any]:
    files = sorted(trace_dir.glob("*_trace.txt"))
    if not files:
        files = sorted(trace_dir.glob("*.txt"))
    empty = [p.name for p in files if p.stat().st_size == 0]
    return {
        "trace_dir": str(trace_dir),
        "trace_files": len(files),
        "non_empty": len(files) - len(empty),
        "empty": len(empty),
        "empty_names": empty[:20],
        "ok": len(files) == 100 and len(empty) == 0,
    }


def package_submission(
    submission_dir: Path,
    input_dir: Path,
    zip_path: Path,
) -> dict[str, Any]:
    submission_dir = resolve_submission_dir(submission_dir)
    entities_map = _load_map(submission_dir)
    offset_mismatches = 0
    type_errors = 0
    for stem, ents in entities_map.items():
        text = (input_dir / f"{stem}.txt").read_text(encoding="utf-8")
        if not isinstance(ents, list):
            raise ValueError(f"{stem}.json root is not a list")
        for e in ents:
            pos = e.get("position") or [None, None]
            start, end = int(pos[0]), int(pos[1])
            if text[start:end] != e.get("text", ""):
                offset_mismatches += 1
            if e.get("type") not in OFFICIAL_TYPES:
                type_errors += 1
            if not isinstance(e.get("candidates", []), list):
                type_errors += 1
            if not isinstance(e.get("assertions", []), list):
                type_errors += 1

    if len(entities_map) != 100:
        raise ValueError(f"Expected 100 JSON files, got {len(entities_map)}")
    if offset_mismatches or type_errors:
        raise ValueError(
            f"Validation failed: offset_mismatches={offset_mismatches}, "
            f"type_errors={type_errors}"
        )

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i in range(1, 101):
            src = submission_dir / f"{i}.json"
            # Mirror canonical v7 structure: output/N.json inside the zip
            zf.write(src, arcname=f"output/{i}.json")

    # Re-open and validate archived files
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = sorted(n for n in zf.namelist() if n.endswith(".json"))
        if len(names) != 100:
            raise ValueError(f"ZIP has {len(names)} json files")
        for name in names:
            data = json.loads(zf.read(name))
            if not isinstance(data, list):
                raise ValueError(f"ZIP entry {name} root not list")

    sha = _sha256_file(zip_path)
    print("SUBMISSION ZIP VALID")
    print("JSON files: 100")
    print("Offset mismatches: 0")
    print(f"path: {zip_path}")
    print(f"size: {zip_path.stat().st_size}")
    print(f"SHA256: {sha}")
    return {
        "path": str(zip_path),
        "size": zip_path.stat().st_size,
        "sha256": sha,
        "json_files": 100,
        "offset_mismatches": 0,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze v8_candidate_rescue outputs.")
    p.add_argument("--v7-dir", type=Path, required=True)
    p.add_argument("--v8-dir", type=Path, required=True)
    p.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "v_dataset" / "var" / "test",
    )
    p.add_argument(
        "--analysis-dir",
        type=Path,
        default=PROJECT_ROOT / "analysis",
    )
    p.add_argument("--trace-dir", type=Path, default=None)
    p.add_argument("--package-zip", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    summary = compare_same_env(
        args.v7_dir, args.v8_dir, args.input_dir, args.analysis_dir
    )
    write_report(summary, args.analysis_dir)
    decision = write_decision(summary, args.analysis_dir)
    print(json.dumps(summary["stats"], ensure_ascii=False, indent=2))
    print(f"Decision: {decision}")

    if args.trace_dir is not None:
        tv = validate_traces(args.trace_dir)
        (args.analysis_dir / "v8_candidate_rescue_trace_validation.json").write_text(
            json.dumps(tv, indent=2), encoding="utf-8"
        )
        print(json.dumps(tv, indent=2))
        if not tv["ok"]:
            raise SystemExit("Trace validation failed")

        transfers, rejections, prov_counts = parse_trace_provenance(args.trace_dir)
        _write_tsv(
            args.analysis_dir / "v8_provenance_transfers.tsv",
            transfers,
            [
                "file",
                "entity_line",
                "rescue_kind",
                "donor_text",
                "donor_alias",
                "alias",
                "rxcui",
                "final_candidates",
            ],
        )
        _write_tsv(
            args.analysis_dir / "v8_provenance_rejections.tsv",
            rejections,
            ["file", "entity_line", "reason"],
        )
        (args.analysis_dir / "v8_provenance_counts.json").write_text(
            json.dumps(dict(prov_counts), indent=2), encoding="utf-8"
        )
        # Append provenance section to report
        report_path = args.analysis_dir / "v8_candidate_rescue_report.md"
        extra = [
            "",
            "## Provenance (from traces)",
            "",
            f"- direct_preset_rescue count: {prov_counts.get('direct_preset_rescue', 0)}",
            f"- transferred_preset_rescue count: {prov_counts.get('transferred_preset_rescue', 0)}",
            f"- v7_candidate_preserved count: {prov_counts.get('v7_candidate_preserved', 0)}",
            f"- unlinked_after_v7_and_rescue count: {prov_counts.get('unlinked_after_v7_and_rescue', 0)}",
            f"- conflicting donor markers: {prov_counts.get('conflict', 0)}",
            f"- transferred metadata markers: {prov_counts.get('transferred_meta', 0)}",
            "",
        ]
        report_path.write_text(
            report_path.read_text(encoding="utf-8") + "\n".join(extra),
            encoding="utf-8",
        )

    if args.package_zip is not None:
        if decision != "READY FOR REVIEW":
            print("Skipping ZIP packaging: not READY FOR REVIEW")
        else:
            package_submission(args.v8_dir, args.input_dir, args.package_zip)


if __name__ == "__main__":
    main()
