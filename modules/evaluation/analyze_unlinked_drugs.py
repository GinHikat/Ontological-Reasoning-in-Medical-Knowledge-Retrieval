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

from modules.components.postprocessing.drug_ontology_provenance import (  # noqa: E402
    MAX_PREFIX_EXTRA,
    MAX_RECIPIENT_LENGTH,
    MAX_SUFFIX_EXTRA,
    MAX_TOTAL_EXTRA,
    _extension_looks_like_medication,
    _has_sentence_marker_outside_donor,
    _is_eligible_donor,
    _safe_containment,
    _valid_unique_rxcuis,
)
from modules.components.postprocessing.ontology_drug_recall import (  # noqa: E402
    OntologyDrugRecallPostProcessor,
)
from modules.core.constants import TARGET_LABEL_DRUG  # noqa: E402
from modules.core.ids import normalize_rxcui  # noqa: E402
from modules.core.schemas import Document, EntityMention, Span  # noqa: E402
from modules.evaluation.analyze_outputs import resolve_submission_dir  # noqa: E402
from modules.evaluation.compare_pipeline_outputs import _ctx, _write_tsv  # noqa: E402

HEADERS = [
    "file",
    "start",
    "end",
    "text",
    "source",
    "confidence",
    "left_context",
    "right_context",
    "has_any_ontology_overlap",
    "ontology_overlap_count",
    "containing_ontology_donors",
    "contained_ontology_donors",
    "donor_texts",
    "donor_spans",
    "donor_match_types",
    "donor_aliases",
    "donor_preset_rxcuis",
    "recoverable_by_safe_containment",
    "reason_not_recoverable",
]


def _load_map(output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    submission_dir = resolve_submission_dir(output_dir)
    if not submission_dir.exists():
        raise FileNotFoundError(f"Submission dir not found: {submission_dir}")
    for path in sorted(submission_dir.glob("*.json")):
        result[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _parse_candidates(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    text = str(raw).strip()
    if not text or text in {"[]", "None", "nan"}:
        return []
    # TSV may store a bare ID
    if text.isdigit():
        return [text]
    try:
        parsed = json.loads(text.replace("'", '"'))
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except Exception:
        pass
    return [text]


def build_ontology_mentions(
    input_dir: Path,
) -> dict[str, list[EntityMention]]:
    """Re-run ontology drug recall (track_rxcui_sets) for diagnostic overlap."""
    proc = OntologyDrugRecallPostProcessor(track_rxcui_sets=True)
    by_file: dict[str, list[EntityMention]] = {}
    for path in sorted(input_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        doc = Document(doc_id=path.stem, text=text)
        mentions = proc.apply(doc, [])
        by_file[path.stem] = [
            m
            for m in mentions
            if m.label == TARGET_LABEL_DRUG
            and m.span.start is not None
            and m.span.end is not None
        ]
    return by_file


def classify_unlinked(
    stem: str,
    entity: dict[str, Any],
    ontology_mentions: list[EntityMention],
    text: str,
) -> dict[str, Any]:
    pos = entity.get("position") or [0, 0]
    start, end = int(pos[0] or 0), int(pos[1] or 0)
    etext = entity.get("text", "")
    left, right = _ctx(text, start, end)

    overlaps: list[EntityMention] = []
    containing: list[EntityMention] = []  # ontology contains final
    contained: list[EntityMention] = []  # final contains ontology
    exact: list[EntityMention] = []

    for m in ontology_mentions:
        ms, me = int(m.span.start), int(m.span.end)
        if me <= start or ms >= end:
            continue
        overlaps.append(m)
        if ms == start and me == end:
            exact.append(m)
        elif ms <= start and end <= me:
            containing.append(m)
        elif start <= ms and me <= end:
            contained.append(m)

    donor_texts = [m.text for m in overlaps]
    donor_spans = [f"{m.span.start}-{m.span.end}" for m in overlaps]
    donor_match_types = [str((m.metadata or {}).get("match", "")) for m in overlaps]
    donor_aliases = [str((m.metadata or {}).get("alias", "")) for m in overlaps]
    donor_presets: list[str] = []
    for m in overlaps:
        valid = _valid_unique_rxcuis((m.metadata or {}).get("preset_rxcui_candidates"))
        donor_presets.append("|".join(valid) if valid else "")

    reason = "NO_ONTOLOGY_EVIDENCE"
    recoverable = False

    if not overlaps:
        reason = "NO_ONTOLOGY_EVIDENCE"
    elif exact:
        # Exact same span had ontology evidence — check ambiguity / validity
        eligible_rxcuis: list[str] = []
        ambiguous = False
        invalid = False
        for m in exact:
            ok, rxcuis, rej = _is_eligible_donor(m)
            if ok:
                eligible_rxcuis.extend(rxcuis)
            elif rej == "ambiguous_rxcui":
                ambiguous = True
            elif rej == "invalid_rxcui":
                invalid = True
        unique = sorted(set(eligible_rxcuis))
        if ambiguous or (len(unique) > 1):
            reason = "AMBIGUOUS_RXCUI" if ambiguous or len(unique) > 1 else reason
            if len(unique) > 1:
                reason = "MULTIPLE_CONFLICTING_DONORS"
            else:
                reason = "AMBIGUOUS_RXCUI"
        elif invalid and not unique:
            reason = "INVALID_RXCUI"
        elif len(unique) == 1:
            reason = "EXACT_SAME_SPAN_EVIDENCE_LOST"
            recoverable = True
        else:
            reason = "EXACT_SAME_SPAN_EVIDENCE_LOST"
    elif contained and not containing:
        # Final span contains ontology donor(s) — main rescue target
        recipient = EntityMention(
            text=etext,
            label=TARGET_LABEL_DRUG,
            span=Span(start, end),
            confidence=float(entity.get("confidence") or 0.0),
            source=str(entity.get("source") or ""),
            metadata={},
        )
        safe_donors: list[tuple[EntityMention, list[str]]] = []
        reject_reasons: list[str] = []
        for m in contained:
            ok, rxcuis, rej = _is_eligible_donor(m)
            if not ok:
                reject_reasons.append(rej or "ineligible_donor")
                continue
            safe, sreason = _safe_containment(recipient, m)
            if not safe:
                reject_reasons.append(sreason)
                continue
            safe_donors.append((m, rxcuis))
        rxcui_set = {r for _, rx in safe_donors for r in rx}
        if len(rxcui_set) > 1:
            reason = "MULTIPLE_CONFLICTING_DONORS"
        elif len(rxcui_set) == 1:
            reason = "FINAL_SPAN_CONTAINS_ONTOLOGY_DONOR"
            recoverable = True
        elif any(r == "ambiguous_rxcui" for r in reject_reasons):
            reason = "AMBIGUOUS_RXCUI"
        elif any(r == "invalid_rxcui" for r in reject_reasons):
            reason = "INVALID_RXCUI"
        elif contained:
            reason = "FINAL_SPAN_CONTAINS_ONTOLOGY_DONOR"
            # not recoverable due to safeguards
            recoverable = False
            if reject_reasons:
                # keep primary taxonomy label but note unsafe in reason field via suffix
                pass
        else:
            reason = "PARTIAL_OVERLAP_ONLY"
    elif containing and not contained:
        reason = "ONTOLOGY_DONOR_CONTAINS_FINAL_SPAN"
    elif containing and contained:
        reason = "PARTIAL_OVERLAP_ONLY"
    else:
        reason = "PARTIAL_OVERLAP_ONLY"

    # Refine non-recoverable containment with more specific labels when useful
    if reason == "FINAL_SPAN_CONTAINS_ONTOLOGY_DONOR" and not recoverable:
        # Check if ambiguity was the blocker among contained donors
        amb = False
        inv = False
        for m in contained:
            ok, rxcuis, rej = _is_eligible_donor(m)
            if rej == "ambiguous_rxcui":
                amb = True
            if rej == "invalid_rxcui":
                inv = True
        if amb:
            reason = "AMBIGUOUS_RXCUI"
        elif inv and not any(_is_eligible_donor(m)[0] for m in contained):
            reason = "INVALID_RXCUI"

    return {
        "file": stem,
        "start": start,
        "end": end,
        "text": etext,
        "source": entity.get("source", ""),
        "confidence": entity.get("confidence", ""),
        "left_context": left,
        "right_context": right,
        "has_any_ontology_overlap": bool(overlaps),
        "ontology_overlap_count": len(overlaps),
        "containing_ontology_donors": len(containing),
        "contained_ontology_donors": len(contained),
        "donor_texts": " | ".join(donor_texts),
        "donor_spans": " | ".join(donor_spans),
        "donor_match_types": " | ".join(donor_match_types),
        "donor_aliases": " | ".join(donor_aliases),
        "donor_preset_rxcuis": " | ".join(donor_presets),
        "recoverable_by_safe_containment": recoverable,
        "reason_not_recoverable": "" if recoverable else reason,
        "_reason": reason,
        "_recoverable": recoverable,
    }


def analyze_dir(
    output_dir: Path,
    input_dir: Path,
    tsv_path: Path,
    ontology_by_file: dict[str, list[EntityMention]] | None = None,
) -> dict[str, Any]:
    data = _load_map(output_dir)
    if ontology_by_file is None:
        print("Building ontology drug recall index...")
        ontology_by_file = build_ontology_mentions(input_dir)

    rows: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    recoverable_n = 0

    for stem in sorted(data):
        text_path = input_dir / f"{stem}.txt"
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        onto = ontology_by_file.get(stem, [])
        for ent in data[stem]:
            if ent.get("type") != TARGET_LABEL_DRUG:
                continue
            cands = _parse_candidates(ent.get("candidates"))
            if cands:
                continue
            row = classify_unlinked(stem, ent, onto, text)
            reason_counts[row["_reason"]] += 1
            if row["_recoverable"]:
                recoverable_n += 1
            rows.append(row)

    tsv_path.parent.mkdir(parents=True, exist_ok=True)
    _write_tsv(tsv_path, rows, HEADERS)
    return {
        "output_dir": str(output_dir),
        "n_unlinked": len(rows),
        "recoverable": recoverable_n,
        "reason_counts": dict(reason_counts),
        "rows": rows,
    }


def write_root_cause_md(
    path: Path,
    canonical: dict[str, Any] | None,
    same_env: dict[str, Any] | None,
    notes: list[str],
) -> None:
    lines = [
        "# V7 Unlinked Drug Root-Cause Audit",
        "",
        "Diagnostic only. No hard-coded predictions.",
        "",
        "## Safeguard parameters used for recoverable_by_safe_containment",
        "",
        f"- prefix_extra <= {MAX_PREFIX_EXTRA}",
        f"- suffix_extra <= {MAX_SUFFIX_EXTRA}",
        f"- total_extra <= {MAX_TOTAL_EXTRA}",
        f"- recipient length <= {MAX_RECIPIENT_LENGTH}",
        "",
    ]
    for note in notes:
        lines.append(f"- {note}")
    lines.append("")

    def _section(title: str, result: dict[str, Any] | None) -> None:
        lines.append(f"## {title}")
        lines.append("")
        if result is None:
            lines.append("Artifact unavailable.")
            lines.append("")
            return
        lines.append(f"- output: `{result['output_dir']}`")
        lines.append(f"- unlinked drugs: **{result['n_unlinked']}**")
        lines.append(f"- recoverable_by_safe_containment: **{result['recoverable']}**")
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|---|---:|")
        for reason, n in sorted(
            result["reason_counts"].items(), key=lambda x: (-x[1], x[0])
        ):
            lines.append(f"| {reason} | {n} |")
        lines.append("")
        lines.append("### Examples")
        lines.append("")
        for row in result["rows"][:20]:
            lines.append(
                f"- `{row['file']}` [{row['start']},{row['end']}] "
                f"`{row['text']}` → {row['_reason']} "
                f"(recoverable={row['_recoverable']})"
            )
        lines.append("")

    _section("Canonical scored v7 artifact", canonical)
    _section("Fresh same-environment v7 run", same_env)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit final unlinked THUỐC entities.")
    p.add_argument(
        "--canonical-dir",
        type=Path,
        default=PROJECT_ROOT / "output" / "v7_structured" / "run1" / "submission",
    )
    p.add_argument(
        "--same-env-dir",
        type=Path,
        default=PROJECT_ROOT / "output" / "v7_same_env" / "run1" / "submission",
    )
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
    return p.parse_args()


def main() -> None:
    args = parse_args()
    analysis_dir = args.analysis_dir
    analysis_dir.mkdir(parents=True, exist_ok=True)

    print("Building shared ontology drug recall index...")
    ontology_by_file = build_ontology_mentions(args.input_dir)

    notes: list[str] = []
    canonical = None
    same_env = None

    if args.canonical_dir.exists():
        canonical = analyze_dir(
            args.canonical_dir,
            args.input_dir,
            analysis_dir / "v7_canonical_unlinked_drugs.tsv",
            ontology_by_file=ontology_by_file,
        )
        print(
            f"Canonical unlinked: {canonical['n_unlinked']} "
            f"(recoverable={canonical['recoverable']})"
        )
    else:
        notes.append(
            f"Canonical artifact missing at `{args.canonical_dir}` "
            "(output/ is gitignored; observational audit skipped or deferred)."
        )
        print(f"WARNING: canonical dir not found: {args.canonical_dir}")

    if args.same_env_dir.exists():
        same_env = analyze_dir(
            args.same_env_dir,
            args.input_dir,
            analysis_dir / "v7_same_env_unlinked_drugs.tsv",
            ontology_by_file=ontology_by_file,
        )
        print(
            f"Same-env unlinked: {same_env['n_unlinked']} "
            f"(recoverable={same_env['recoverable']})"
        )
    else:
        notes.append(f"Same-env artifact missing at `{args.same_env_dir}`.")
        print(f"WARNING: same-env dir not found: {args.same_env_dir}")

    write_root_cause_md(
        analysis_dir / "v7_unlinked_drug_root_causes.md",
        canonical,
        same_env,
        notes,
    )
    print(f"Wrote {analysis_dir / 'v7_unlinked_drug_root_causes.md'}")


if __name__ == "__main__":
    main()
