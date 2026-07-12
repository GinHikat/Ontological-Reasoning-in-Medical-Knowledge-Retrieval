"""Deterministic schema-format gates after judge adjudication."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ALLOWED_TYPES = {
    "TRIỆU_CHỨNG",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
    "CHẨN_ĐOÁN",
    "THUỐC",
}
ASSERTION_ELIGIBLE = {"TRIỆU_CHỨNG", "CHẨN_ĐOÁN", "THUỐC"}
ALLOWED_ASSERTIONS = {"isNegated", "isFamily", "isHistorical"}


@dataclass
class GateReport:
    kept: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    overlaps: list[dict[str, Any]] = field(default_factory=list)


def apply_schema_gates(document: str, entities: list[dict[str, Any]]) -> GateReport:
    report = GateReport()
    seen: set[tuple[str, int, int, str]] = set()
    cleaned: list[dict[str, Any]] = []

    for ent in entities:
        text = str(ent.get("text") or "")
        start = ent.get("start")
        end = ent.get("end")
        etype = str(ent.get("type") or "")
        assertions = list(ent.get("assertions") or [])
        reasons: list[str] = []

        if not isinstance(start, int) or not isinstance(end, int):
            reasons.append("invalid_position")
        elif not (0 <= start < end <= len(document)):
            reasons.append("invalid_position")
        elif document[start:end] != text:
            reasons.append("not_exact_source_substring")

        if etype not in ALLOWED_TYPES:
            reasons.append("invalid_type")

        bad_assert = [a for a in assertions if a not in ALLOWED_ASSERTIONS]
        if bad_assert:
            reasons.append("invalid_assertions")
        if assertions and etype not in ASSERTION_ELIGIBLE:
            reasons.append("assertions_on_ineligible_type")
            assertions = []

        # no candidates yet at this stage
        if ent.get("candidates"):
            reasons.append("candidates_not_allowed_yet")

        key = (text, int(start) if isinstance(start, int) else -1, int(end) if isinstance(end, int) else -1, etype)
        if key in seen:
            reasons.append("exact_duplicate")
        else:
            seen.add(key)

        if reasons:
            report.rejected.append({**ent, "gate_reasons": reasons})
            continue

        out = {
            "text": document[start:end],
            "type": etype,
            "assertions": sorted(set(assertions)),
            "position": [start, end],
            "start": start,
            "end": end,
        }
        # preserve diagnostic provenance when present
        for k in ("source", "judge_action", "recovery"):
            if k in ent:
                out[k] = ent[k]
        cleaned.append(out)

    cleaned.sort(key=lambda e: (e["start"], e["end"], e["type"]))

    # record overlaps; do not auto-reject
    for i, a in enumerate(cleaned):
        for b in cleaned[i + 1 :]:
            if b["start"] >= a["end"]:
                break
            if min(a["end"], b["end"]) > max(a["start"], b["start"]):
                report.overlaps.append(
                    {
                        "a": {
                            "text": a["text"],
                            "start": a["start"],
                            "end": a["end"],
                            "type": a["type"],
                        },
                        "b": {
                            "text": b["text"],
                            "start": b["start"],
                            "end": b["end"],
                            "type": b["type"],
                        },
                    }
                )

    report.kept = cleaned
    return report


def to_competition_entity(ent: dict[str, Any], candidates: list[str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "text": ent["text"],
        "type": ent["type"],
        "assertions": list(ent.get("assertions") or []),
        "position": list(ent.get("position") or [ent["start"], ent["end"]]),
    }
    if candidates is not None:
        out["candidates"] = list(candidates)
    elif "candidates" in ent:
        out["candidates"] = list(ent["candidates"])
    return out
