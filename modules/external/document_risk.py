"""Deterministic document risk scoring for conditional largest-model review."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from statistics import median
from typing import Any

NEGATION_CUES = re.compile(
    r"(không|ko|chẳng|chả|\bno\b|\bwithout\b|phủ định)", re.I
)
PROCEDURE_CUES = re.compile(
    r"(phẫu thuật|đặt stent|đặt shunt|đặt catheter|can thiệp|dẫn lưu|truyền dịch|"
    r"truyền máu|tiêm|cắt bỏ|ghép|chọc|stent|shunt)",
    re.I,
)


@dataclass
class RiskResult:
    document_id: str
    entity_count: int
    risk_score: int
    risk_reasons: list[str] = field(default_factory=list)
    requires_judge: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "entity_count": self.entity_count,
            "risk_score": self.risk_score,
            "risk_reasons": ";".join(self.risk_reasons),
            "requires_judge": self.requires_judge,
        }


def risk_threshold() -> int:
    raw = os.environ.get("OPENROUTER_REDUCED_RISK_THRESHOLD", "3").strip()
    return int(raw) if raw else 3


def score_document_risk(
    doc_id: str,
    document: str,
    entities: list[dict[str, Any]],
    *,
    alignment_stats: dict[str, int] | None = None,
    parse_status: str | None = None,
    retried: bool = False,
    unresolved_candidates: int = 0,
    corpus_entity_counts: list[int] | None = None,
) -> RiskResult:
    reasons: list[str] = []
    score = 0
    n = len(entities)
    stats = alignment_stats or {}

    if parse_status and parse_status not in {"ok", "healed_json_extract", "cached"}:
        score += 3
        reasons.append("+3_invalid_or_repaired_structured_output")

    ambiguous = int(stats.get("rejected_ambiguous") or 0)
    not_found = int(stats.get("rejected_not_found") or 0)
    if ambiguous + not_found > 0:
        score += 3
        reasons.append("+3_unresolved_span_alignment")

    proc_as_test = 0
    for e in entities:
        if e.get("type") == "TÊN_XÉT_NGHIỆM" and PROCEDURE_CUES.search(e.get("text") or ""):
            proc_as_test += 1
    if proc_as_test:
        score += 3
        reasons.append(f"+3_procedure_like_as_test:{proc_as_test}")

    # entity count anomalies vs corpus median when available
    if corpus_entity_counts:
        med = median(corpus_entity_counts) or 1
        if n < max(1, 0.35 * med):
            score += 3
            reasons.append("+3_abnormally_low_entity_count")
        elif n > 2.5 * med:
            score += 3
            reasons.append("+3_abnormally_high_entity_count")
    else:
        # absolute fallbacks for short/long clinical notes
        doc_len = len(document)
        expected = max(3, doc_len // 80)
        if n < max(1, expected // 4):
            score += 3
            reasons.append("+3_abnormally_low_entity_count")
        elif n > expected * 3 and n > 40:
            score += 3
            reasons.append("+3_abnormally_high_entity_count")

    # overlapping incompatible types
    sorted_ents = sorted(
        entities, key=lambda e: (e["position"][0], e["position"][1], e["type"])
    )
    incompat = 0
    for i, a in enumerate(sorted_ents):
        for b in sorted_ents[i + 1 :]:
            if b["position"][0] >= a["position"][1]:
                break
            if a["type"] != b["type"] and min(a["position"][1], b["position"][1]) > max(
                a["position"][0], b["position"][0]
            ):
                pair = {a["type"], b["type"]}
                if pair == {"TRIỆU_CHỨNG", "CHẨN_ĐOÁN"} or pair == {
                    "TÊN_XÉT_NGHIỆM",
                    "KẾT_QUẢ_XÉT_NGHIỆM",
                }:
                    # lab name/result overlap can be OK if nested; still count soft
                    if pair == {"TRIỆU_CHỨNG", "CHẨN_ĐOÁN"}:
                        incompat += 1
                elif a["type"] != b["type"]:
                    incompat += 1
    if incompat:
        score += 2
        reasons.append(f"+2_overlapping_incompatible_types:{incompat}")

    neg_in_span = 0
    for e in entities:
        if e.get("type") in {"TRIỆU_CHỨNG", "CHẨN_ĐOÁN"} and NEGATION_CUES.search(
            e.get("text") or ""
        ):
            neg_in_span += 1
    if neg_in_span:
        score += 2
        reasons.append(f"+2_negation_cue_inside_span:{neg_in_span}")

    low_conf = sum(
        1
        for e in entities
        if isinstance(e.get("confidence"), (int, float)) and float(e["confidence"]) < 0.55
    )
    if low_conf >= 3:
        score += 2
        reasons.append(f"+2_many_low_confidence:{low_conf}")

    if unresolved_candidates > 0:
        score += 2
        reasons.append(f"+2_unresolved_candidates:{unresolved_candidates}")

    long_sym = sum(
        1
        for e in entities
        if e.get("type") == "TRIỆU_CHỨNG" and (e["position"][1] - e["position"][0]) > 40
    )
    if long_sym:
        score += 2
        reasons.append(f"+2_unusually_long_symptom:{long_sym}")

    long_result = sum(
        1
        for e in entities
        if e.get("type") == "KẾT_QUẢ_XÉT_NGHIỆM"
        and (e["position"][1] - e["position"][0]) > 60
    )
    if long_result:
        score += 2
        reasons.append(f"+2_overlong_test_result:{long_result}")

    if len(document) > 2500:
        score += 1
        reasons.append("+1_very_long_document")

    if retried:
        score += 1
        reasons.append("+1_extractor_retry")

    thr = risk_threshold()
    return RiskResult(
        document_id=doc_id,
        entity_count=n,
        risk_score=score,
        risk_reasons=reasons,
        requires_judge=score >= thr,
    )
