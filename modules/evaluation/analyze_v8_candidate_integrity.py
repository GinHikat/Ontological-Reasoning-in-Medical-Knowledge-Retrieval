from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.components.postprocessing.ontology_drug_recall import (  # noqa: E402
    OntologyDrugRecallPostProcessor,
    normalize_with_map,
)
from modules.core.constants import TARGET_LABEL_DRUG  # noqa: E402
from modules.core.ids import normalize_rxcui  # noqa: E402
from modules.core.schemas import Document  # noqa: E402
from modules.evaluation.analyze_outputs import resolve_submission_dir  # noqa: E402
from modules.evaluation.compare_pipeline_outputs import _ctx, _write_tsv  # noqa: E402

OFFICIAL_TYPES = {
    "CHẨN_ĐOÁN",
    "THUỐC",
    "TÊN_XÉT_NGHIỆM",
    "TRIỆU_CHỨNG",
    "KẾT_QUẢ_XÉT_NGHIỆM",
}

NOISY_PATTERNS = [
    "Dùngmethadonekéo dài",
    "lasixđã dừng",
    "Đã sử dụngvancozosyn",
    "vancozosynbactrim",
]


def _load_map(output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    submission_dir = resolve_submission_dir(output_dir)
    for path in sorted(submission_dir.glob("*.json")):
        result[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _drug_key(e: dict[str, Any]) -> tuple:
    pos = e.get("position") or [None, None]
    return (pos[0], pos[1], e.get("text", ""))


def build_ontology_drug_index(
    input_dir: Path,
) -> dict[tuple[str, int, int, str], dict[str, Any]]:
    """Re-run ontology drug recall (v8 mode) to recover preset metadata for analysis."""
    proc = OntologyDrugRecallPostProcessor(track_rxcui_sets=True)
    index: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    for path in sorted(input_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        doc = Document(doc_id=path.stem, text=text)
        mentions = proc.apply(doc, [])
        for m in mentions:
            if m.label != TARGET_LABEL_DRUG:
                continue
            if m.span.start is None or m.span.end is None:
                continue
            key = (path.stem, int(m.span.start), int(m.span.end), m.text)
            index[key] = {
                "source": m.source,
                "match_type": m.metadata.get("match", ""),
                "matched_alias": m.metadata.get("alias", ""),
                "preset_rxcui_candidates": list(
                    m.metadata.get("preset_rxcui_candidates") or []
                ),
                "preset_rxcui_count": m.metadata.get("preset_rxcui_count", ""),
                "preset_rxcui_unambiguous": m.metadata.get(
                    "preset_rxcui_unambiguous", False
                ),
                "matched_alias_norm": m.metadata.get("matched_alias_norm", ""),
                "matched_alias_compact": m.metadata.get("matched_alias_compact", ""),
            }
    return index


def analyze_v8(
    v7_dir: Path,
    v8_dir: Path,
    input_dir: Path,
    analysis_dir: Path,
) -> dict[str, Any]:
    analysis_dir.mkdir(parents=True, exist_ok=True)
    v7 = _load_map(v7_dir)
    v8 = _load_map(v8_dir)

    print("Building ontology drug recall index for diagnostics...")
    onto_index = build_ontology_drug_index(input_dir)

    total_drugs = 0
    v7_with = v7_without = 0
    ontology_origin = 0
    with_preset_meta = 0
    unambiguous = ambiguous = invalid_missing = 0
    preset_used = sapbert_fallback = 0
    unchanged = changed = newly_linked = newly_unlinked = 0

    changed_rows: list[dict[str, Any]] = []
    newly_linked_rows: list[dict[str, Any]] = []
    changed_linked_rows: list[dict[str, Any]] = []
    ambiguous_fallback_rows: list[dict[str, Any]] = []
    noisy_cases: list[dict[str, Any]] = []

    for stem in sorted(set(v7) | set(v8)):
        text_path = input_dir / f"{stem}.txt"
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        b_ents = [e for e in v7.get(stem, []) if e.get("type") == "THUỐC"]
        c_ents = [e for e in v8.get(stem, []) if e.get("type") == "THUỐC"]
        # Pair by position order (invariants guarantee same entity set/order overall)
        # Use full entity lists for pairing by identity
        all_b = v7.get(stem, [])
        all_c = v8.get(stem, [])
        for b, c in zip(all_b, all_c):
            if b.get("type") != "THUỐC":
                continue
            total_drugs += 1
            b_cand = list(b.get("candidates") or [])
            c_cand = list(c.get("candidates") or [])
            if b_cand:
                v7_with += 1
            else:
                v7_without += 1

            pos = b.get("position") or [0, 0]
            start, end = int(pos[0] or 0), int(pos[1] or 0)
            key = (stem, start, end, b.get("text", ""))
            meta = onto_index.get(key)
            if meta is None:
                # Try fuzzy: same start/end
                for k, v in onto_index.items():
                    if k[0] == stem and k[1] == start and k[2] == end:
                        meta = v
                        break

            is_onto = meta is not None
            if is_onto:
                ontology_origin += 1
            presets = list((meta or {}).get("preset_rxcui_candidates") or [])
            valid = sorted(
                {rid for rid in (normalize_rxcui(x) for x in presets) if rid}
            )
            if is_onto:
                with_preset_meta += 1
                if len(valid) == 1:
                    unambiguous += 1
                elif len(valid) > 1:
                    ambiguous += 1
                else:
                    invalid_missing += 1

            used_preset = bool(
                is_onto
                and len(valid) == 1
                and c_cand == valid
            )
            # Heuristic: if ontology unambiguous and v8 candidate equals preset
            if used_preset:
                preset_used += 1
                link_path = "preset_unambiguous_rxcui"
            else:
                sapbert_fallback += 1
                if is_onto and len(valid) > 1:
                    link_path = "sapbert_fallback:ambiguous_alias"
                elif is_onto and len(valid) == 0:
                    link_path = "sapbert_fallback:invalid_preset"
                elif is_onto:
                    # unambiguous but candidate differs or empty — still may be preset
                    # if c_cand matches; else fallback (threshold miss etc.)
                    if len(valid) == 1 and c_cand == valid:
                        link_path = "preset_unambiguous_rxcui"
                    else:
                        link_path = "sapbert_fallback"
                else:
                    link_path = "sapbert_fallback:not_ontology_recall"

            if b_cand == c_cand:
                unchanged += 1
            else:
                changed += 1
                left, right = _ctx(text, start, end)
                row = {
                    "file": stem,
                    "start": start,
                    "end": end,
                    "text": b.get("text", ""),
                    "source": (meta or {}).get("source", ""),
                    "match_type": (meta or {}).get("match_type", ""),
                    "matched_alias": (meta or {}).get("matched_alias", ""),
                    "preset_rxcui_count": len(valid),
                    "preset_rxcui_candidates": "|".join(valid),
                    "v7_candidate": "|".join(b_cand),
                    "v8_candidate": "|".join(c_cand),
                    "v7_had_candidate": bool(b_cand),
                    "v8_has_candidate": bool(c_cand),
                    "left_context": left,
                    "right_context": right,
                    "link_path": link_path,
                }
                changed_rows.append(row)
                if not b_cand and c_cand:
                    newly_linked += 1
                    newly_linked_rows.append(row)
                elif b_cand and c_cand:
                    newly_unlinked  # noqa: B018 — keep counter below
                    changed_linked_rows.append(row)
                elif b_cand and not c_cand:
                    newly_unlinked += 1

                if is_onto and len(valid) > 1:
                    ambiguous_fallback_rows.append(row)

            # Noisy pattern diagnostics
            window = text[max(0, start - 40) : min(len(text), end + 40)]
            for pat in NOISY_PATTERNS:
                if pat.lower().replace(" ", "") in window.lower().replace(" ", "") or (
                    b.get("text", "").lower() in pat.lower()
                ):
                    noisy_cases.append(
                        {
                            "pattern": pat,
                            "file": stem,
                            "original_context": window.replace("\n", " "),
                            "final_text": b.get("text", ""),
                            "position": [start, end],
                            "match_type": (meta or {}).get("match_type", ""),
                            "matched_alias": (meta or {}).get("matched_alias", ""),
                            "all_rxcuis": valid,
                            "unambiguous": len(valid) == 1,
                            "v7_candidate": b_cand,
                            "v8_candidate": c_cand,
                            "link_path": link_path,
                        }
                    )
                    break

    # Recount newly_unlinked / changed_linked properly
    newly_linked = sum(1 for r in changed_rows if not r["v7_had_candidate"] and r["v8_has_candidate"])
    newly_unlinked = sum(1 for r in changed_rows if r["v7_had_candidate"] and not r["v8_has_candidate"])
    changed_linked = sum(
        1 for r in changed_rows if r["v7_had_candidate"] and r["v8_has_candidate"]
    )

    # Recompute preset_used more carefully from changed+unchanged ontology drugs
    # Prefer: among ontology drugs with unambiguous preset, how many v8 cands == preset
    preset_used = 0
    sapbert_fallback = 0
    for stem in sorted(set(v7) | set(v8)):
        for b, c in zip(v7.get(stem, []), v8.get(stem, [])):
            if b.get("type") != "THUỐC":
                continue
            pos = b.get("position") or [0, 0]
            start, end = int(pos[0] or 0), int(pos[1] or 0)
            key = (stem, start, end, b.get("text", ""))
            meta = onto_index.get(key)
            if meta is None:
                for k, v in onto_index.items():
                    if k[0] == stem and k[1] == start and k[2] == end:
                        meta = v
                        break
            c_cand = list(c.get("candidates") or [])
            if meta is None:
                sapbert_fallback += 1
                continue
            valid = sorted(
                {
                    rid
                    for rid in (
                        normalize_rxcui(x)
                        for x in (meta.get("preset_rxcui_candidates") or [])
                    )
                    if rid
                }
            )
            if len(valid) == 1 and c_cand == valid:
                preset_used += 1
            else:
                sapbert_fallback += 1

    headers_changed = [
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
    ]
    _write_tsv(
        analysis_dir / "v8_changed_drug_candidates.tsv", changed_rows, headers_changed
    )
    _write_tsv(
        analysis_dir / "v8_newly_linked_drugs.tsv",
        newly_linked_rows,
        headers_changed,
    )
    _write_tsv(
        analysis_dir / "v8_changed_linked_drugs.tsv",
        changed_linked_rows,
        headers_changed,
    )
    _write_tsv(
        analysis_dir / "v8_ambiguous_alias_fallbacks.tsv",
        ambiguous_fallback_rows,
        headers_changed,
    )

    of_17 = newly_linked  # how many of the 17 unlinked got linked
    of_259_changed = changed_linked

    report_lines = [
        "# v7 vs v8 candidate integrity\n",
        "## Scope\n",
        "Isolated THUỐC candidate-linking experiment. Entity spans/types/assertions must match canonical v7.\n",
        "## Drug totals\n",
        f"- Total final drugs: {total_drugs}",
        f"- V7 drugs with candidates: {v7_with}",
        f"- V7 drugs without candidates: {v7_without}",
        f"- Final drugs originating from ontology drug recall: {ontology_origin}",
        f"- Final drugs with preset metadata: {with_preset_meta}",
        "",
        "### Preset aliases",
        f"- unambiguous: {unambiguous}",
        f"- ambiguous: {ambiguous}",
        f"- invalid/missing: {invalid_missing}",
        "",
        "### Linking path (heuristic from output + recall re-run)",
        f"- V8 direct preset path used: {preset_used}",
        f"- V8 SapBERT fallback used: {sapbert_fallback}",
        "",
        "## Candidate changes\n",
        f"- unchanged candidate arrays: {unchanged}",
        f"- changed candidate arrays: {changed}",
        f"- newly linked drugs: {newly_linked}",
        f"- newly unlinked drugs: {newly_unlinked}",
        f"- previously linked drugs that changed ID: {changed_linked}",
        "",
        f"**How many of the 17 previously unlinked v7 drugs received a candidate in v8?** {of_17}",
        "",
        f"**How many of the 259 previously linked v7 drugs changed to a different candidate?** {of_259_changed}",
        "",
        "## Noisy case inspection\n",
    ]
    for case in noisy_cases:
        report_lines.append(f"### Pattern `{case['pattern']}` / file {case['file']}")
        report_lines.append(f"- context: `{case['original_context']}`")
        report_lines.append(f"- final text: `{case['final_text']}` @ {case['position']}")
        report_lines.append(f"- match: {case['match_type']} alias=`{case['matched_alias']}`")
        report_lines.append(f"- RxCUIs: {case['all_rxcuis']} unambiguous={case['unambiguous']}")
        report_lines.append(f"- v7: {case['v7_candidate']} → v8: {case['v8_candidate']}")
        report_lines.append(f"- path: {case['link_path']}")
        report_lines.append("")

    (analysis_dir / "v7_vs_v8_candidate_integrity.md").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )
    (analysis_dir / "v8_noisy_cases.json").write_text(
        json.dumps(noisy_cases, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = {
        "total_drugs": total_drugs,
        "v7_with_candidates": v7_with,
        "v7_without_candidates": v7_without,
        "ontology_origin": ontology_origin,
        "with_preset_meta": with_preset_meta,
        "unambiguous": unambiguous,
        "ambiguous": ambiguous,
        "invalid_missing": invalid_missing,
        "preset_used": preset_used,
        "sapbert_fallback": sapbert_fallback,
        "unchanged": unchanged,
        "changed": changed,
        "newly_linked": newly_linked,
        "newly_unlinked": newly_unlinked,
        "changed_linked": changed_linked,
        "of_17_newly_linked": of_17,
        "of_259_changed": of_259_changed,
        "noisy_cases": len(noisy_cases),
    }
    (analysis_dir / "v8_drug_stats.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def validate_submission_dir(submission_dir: Path, input_dir: Path) -> list[str]:
    errors: list[str] = []
    files = sorted(submission_dir.glob("*.json"))
    if len(files) != 100:
        errors.append(f"expected 100 JSON files, found {len(files)}")
    for i in range(1, 101):
        p = submission_dir / f"{i}.json"
        if not p.exists():
            errors.append(f"missing {i}.json")
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{i}.json: invalid JSON ({exc})")
            continue
        if not isinstance(data, list):
            errors.append(f"{i}.json: root is not a list")
            continue
        text_path = input_dir / f"{i}.txt"
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        for idx, ent in enumerate(data):
            if not isinstance(ent, dict):
                errors.append(f"{i}.json[{idx}]: not an object")
                continue
            start_end = ent.get("position")
            if not (
                isinstance(start_end, list)
                and len(start_end) == 2
                and isinstance(start_end[0], int)
                and isinstance(start_end[1], int)
            ):
                errors.append(f"{i}.json[{idx}]: bad position")
                continue
            start, end = start_end
            if start < 0 or end <= start or end > len(text):
                errors.append(
                    f"{i}.json[{idx}]: invalid offsets {start_end} vs len={len(text)}"
                )
            elif ent.get("text") != text[start:end]:
                errors.append(
                    f"{i}.json[{idx}]: text mismatch "
                    f"{ent.get('text')!r} != {text[start:end]!r}"
                )
            if ent.get("type") not in OFFICIAL_TYPES:
                errors.append(f"{i}.json[{idx}]: bad type {ent.get('type')}")
            # candidates is required for diagnosis/drug; optional elsewhere
            if "candidates" in ent and not isinstance(ent.get("candidates"), list):
                errors.append(f"{i}.json[{idx}]: candidates not a list")
            if ent.get("type") in {"CHẨN_ĐOÁN", "THUỐC"}:
                if not isinstance(ent.get("candidates"), list):
                    errors.append(
                        f"{i}.json[{idx}]: linkable type missing candidates list"
                    )
            if not isinstance(ent.get("assertions"), list):
                errors.append(f"{i}.json[{idx}]: assertions not a list")
    return errors


def package_submission(
    submission_dir: Path,
    input_dir: Path,
    zip_path: Path,
    mirror_zip: Path | None = None,
) -> dict[str, Any]:
    """Create submission ZIP mirroring canonical v7 structure.

    Competition format (from round1 docs):
        output.zip
          output/1.json
          ...
          output/100.json
    """
    errors = validate_submission_dir(submission_dir, input_dir)
    if errors:
        return {"ok": False, "errors": errors[:50], "error_count": len(errors)}

    # Default competition layout: output/<n>.json inside the zip.
    arc_prefix = "output/"
    if mirror_zip and mirror_zip.exists():
        with zipfile.ZipFile(mirror_zip, "r") as zf:
            names = [n for n in zf.namelist() if n.endswith(".json")]
            if names:
                sample = names[0]
                if "/" in sample:
                    arc_prefix = sample.rsplit("/", 1)[0] + "/"
                else:
                    arc_prefix = ""

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i in range(1, 101):
            src = submission_dir / f"{i}.json"
            zf.write(src, arcname=f"{arc_prefix}{i}.json")

    # Re-open and validate archived content
    reopen_errors: list[str] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = sorted(n for n in zf.namelist() if n.endswith(".json"))
        if len(names) != 100:
            reopen_errors.append(f"zip has {len(names)} json files, expected 100")
        for i in range(1, 101):
            target = f"{arc_prefix}{i}.json"
            if target not in zf.namelist():
                reopen_errors.append(f"zip missing {target}")
                continue
            raw = zf.read(target)
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, list):
                reopen_errors.append(f"{target}: root not list")
                continue
            text = (input_dir / f"{i}.txt").read_text(encoding="utf-8")
            for idx, ent in enumerate(data):
                start, end = ent["position"]
                if start < 0 or end <= start or end > len(text):
                    reopen_errors.append(f"{target}[{idx}]: bad offsets")
                elif ent["text"] != text[start:end]:
                    reopen_errors.append(f"{target}[{idx}]: text mismatch")
                if ent.get("type") in {"CHẨN_ĐOÁN", "THUỐC"}:
                    if not isinstance(ent.get("candidates"), list):
                        reopen_errors.append(
                            f"{target}[{idx}]: missing candidates list"
                        )

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    size = zip_path.stat().st_size
    ok = not reopen_errors
    result = {
        "ok": ok,
        "zip_path": str(zip_path),
        "zip_size": size,
        "sha256": digest,
        "json_files": 100,
        "offset_mismatches": sum(
            1 for e in reopen_errors if "offset" in e or "text mismatch" in e
        ),
        "reopen_errors": reopen_errors,
        "arc_prefix": arc_prefix,
    }
    if ok:
        print("SUBMISSION ZIP VALID")
        print("JSON files: 100")
        print("Offset mismatches: 0")
        print(f"ZIP path: {zip_path}")
        print(f"ZIP size: {size}")
        print(f"SHA256: {digest}")
    else:
        print("SUBMISSION ZIP INVALID")
        for e in reopen_errors[:20]:
            print(f"  - {e}")
    return result


def write_decision_report(
    analysis_dir: Path,
    v7_regression_ok: bool,
    invariants_ok: bool,
    stats: dict[str, Any],
    zip_info: dict[str, Any] | None,
) -> str:
    hard_fail_reasons: list[str] = []
    if not v7_regression_ok:
        hard_fail_reasons.append("v7 regression failure")
    if not invariants_ok:
        hard_fail_reasons.append("v7→v8 hard invariant failure")

    changed = int(stats.get("changed", 0))
    total = int(stats.get("total_drugs", 276) or 276)
    frac = (changed / total) if total else 0.0
    review_flags: list[str] = []
    if frac > 0.5:
        review_flags.append(
            f"more than 50% of drug candidates changed ({changed}/{total} = {frac:.1%})"
        )

    ready = not hard_fail_reasons
    status = "READY TO SUBMIT" if ready else "NOT READY TO SUBMIT"

    lines = [
        "# v8 submission decision\n",
        f"## Decision: **{status}**\n",
        "## Hard gates\n",
    ]
    if hard_fail_reasons:
        for r in hard_fail_reasons:
            lines.append(f"- FAIL: {r}")
    else:
        lines.append("- v7 regression: PASS")
        lines.append("- entity/text/position/type/assertion invariants: PASS")
        lines.append("- diagnosis candidates unchanged: PASS")
    lines.append("\n## Candidate-change risk\n")
    lines.append(f"- total drugs: {total}")
    lines.append(f"- changed drug candidates: {changed} ({frac:.1%})")
    lines.append(f"- newly linked: {stats.get('newly_linked')}")
    lines.append(f"- newly unlinked: {stats.get('newly_unlinked')}")
    lines.append(f"- previously linked ID changes: {stats.get('changed_linked')}")
    if review_flags:
        lines.append("\n## Manual review flags\n")
        for f in review_flags:
            lines.append(f"- {f}")
        lines.append(
            "\nThese flags do not automatically reject submission, but risk is explicit."
        )
    if zip_info:
        lines.append("\n## Submission ZIP\n")
        lines.append(f"- path: `{zip_info.get('zip_path')}`")
        lines.append(f"- size: {zip_info.get('zip_size')}")
        lines.append(f"- SHA256: `{zip_info.get('sha256')}`")
        lines.append(f"- valid: {zip_info.get('ok')}")

    path = analysis_dir / "v8_submission_decision.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(path.read_text(encoding="utf-8"))
    return status


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--v7-dir", type=Path, required=True)
    p.add_argument("--v8-dir", type=Path, required=True)
    p.add_argument("--input-dir", type=Path, default=PROJECT_ROOT / "data" / "var" / "test")
    p.add_argument("--analysis-dir", type=Path, default=PROJECT_ROOT / "analysis")
    p.add_argument("--v7-regression-ok", action="store_true")
    p.add_argument("--invariants-ok", action="store_true")
    p.add_argument("--package", action="store_true")
    p.add_argument(
        "--zip-path",
        type=Path,
        default=PROJECT_ROOT / "output" / "v8_candidate_integrity_submission.zip",
    )
    args = p.parse_args()

    stats = analyze_v8(args.v7_dir, args.v8_dir, args.input_dir, args.analysis_dir)
    zip_info = None
    if args.package and args.v7_regression_ok and args.invariants_ok:
        zip_info = package_submission(
            resolve_submission_dir(args.v8_dir),
            args.input_dir,
            args.zip_path,
        )
    write_decision_report(
        args.analysis_dir,
        args.v7_regression_ok,
        args.invariants_ok,
        stats,
        zip_info,
    )


if __name__ == "__main__":
    main()
