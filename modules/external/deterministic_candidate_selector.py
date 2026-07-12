"""Deterministic ICD/RxNorm acceptance without an LLM when evidence is strong."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    return float(raw) if raw else default


@dataclass
class CandidateThresholds:
    diagnosis_top: float = 0.85
    diagnosis_margin: float = 0.08
    drug_top: float = 0.95
    drug_margin: float = 0.08
    exact_lexical: float = 0.999

    @classmethod
    def from_env(cls) -> "CandidateThresholds":
        return cls(
            diagnosis_top=_env_float("OPENROUTER_REDUCED_DIAGNOSIS_TOP_THRESHOLD", 0.85),
            diagnosis_margin=_env_float(
                "OPENROUTER_REDUCED_DIAGNOSIS_MARGIN_THRESHOLD", 0.08
            ),
            drug_top=_env_float("OPENROUTER_REDUCED_DRUG_TOP_THRESHOLD", 0.95),
            drug_margin=_env_float("OPENROUTER_REDUCED_DRUG_MARGIN_THRESHOLD", 0.08),
        )


@dataclass
class SelectionResult:
    selected_ids: list[str]
    accepted: bool
    reason: str
    needs_judge: bool


@dataclass
class BatchItem:
    item_id: str
    document_id: str
    entity_text: str
    entity_type: str
    context: str
    candidates: list[dict[str, Any]]


def _sorted_cands(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        cands,
        key=lambda c: (
            -float(c.get("combined_score") or 0.0),
            -float(c.get("lexical_score") or 0.0),
            str(c.get("id") or ""),
        ),
    )


def _has_strength_form_cues(text: str) -> bool:
    return bool(
        re.search(
            r"(\d+\s*(mg|mcg|µg|g|ml|iu|%)|/|\bviên\b|\bống\b|\bbột\b|\bcream\b|"
            r"\bgel\b|\bsyrup\b|\binjection\b|\btablet\b|\bcapsule\b)",
            text or "",
            re.I,
        )
    )


def select_diagnosis_deterministic(
    candidates: list[dict[str, Any]],
    thresholds: CandidateThresholds | None = None,
) -> SelectionResult:
    thr = thresholds or CandidateThresholds.from_env()
    cands = _sorted_cands(candidates)
    if not cands:
        return SelectionResult([], True, "no_candidates", False)

    exact = [
        c
        for c in cands
        if float(c.get("lexical_score") or 0.0) >= thr.exact_lexical
        or "exact" in " ".join(c.get("retrieval_sources") or []).lower()
    ]
    if len(exact) == 1:
        return SelectionResult(
            [str(exact[0]["id"])], True, "exact_normalized_alias_unique", False
        )
    if len(exact) > 1:
        # multiple exact aliases → ambiguous; do not hedge with all siblings
        return SelectionResult([], False, "exact_alias_ambiguous", True)

    if len(cands) == 1 and float(cands[0].get("lexical_score") or 0.0) >= 0.80:
        return SelectionResult(
            [str(cands[0]["id"])], True, "single_candidate_after_validation", False
        )

    top = float(cands[0].get("combined_score") or 0.0)
    second = float(cands[1].get("combined_score") or 0.0) if len(cands) > 1 else 0.0
    margin = top - second
    top_lex = float(cands[0].get("lexical_score") or 0.0)
    if top_lex >= 0.95 and (len(cands) == 1 or margin >= thr.diagnosis_margin):
        return SelectionResult(
            [str(cands[0]["id"])], True, "direct_lexical_match_dominant", False
        )
    if top >= thr.diagnosis_top and margin >= thr.diagnosis_margin:
        return SelectionResult(
            [str(cands[0]["id"])], True, "top_score_with_margin", False
        )
    return SelectionResult([], False, "ambiguous_needs_judge", True)


def select_drug_deterministic(
    text: str,
    candidates: list[dict[str, Any]],
    thresholds: CandidateThresholds | None = None,
) -> SelectionResult:
    thr = thresholds or CandidateThresholds.from_env()
    cands = _sorted_cands(candidates)
    if not cands:
        return SelectionResult([], True, "no_candidates", False)

    exact = [
        c
        for c in cands
        if float(c.get("lexical_score") or 0.0) >= thr.exact_lexical
        or "exact" in " ".join(c.get("retrieval_sources") or []).lower()
    ]
    if len(exact) == 1:
        return SelectionResult(
            [str(exact[0]["id"])], True, "exact_normalized_medication_unique", False
        )
    if len(exact) > 1:
        return SelectionResult([], False, "exact_medication_ambiguous", True)

    if len(cands) == 1 and float(cands[0].get("lexical_score") or 0.0) >= 0.85:
        return SelectionResult(
            [str(cands[0]["id"])], True, "single_candidate_after_validation", False
        )

    top = float(cands[0].get("combined_score") or 0.0)
    second = float(cands[1].get("combined_score") or 0.0) if len(cands) > 1 else 0.0
    margin = top - second
    top_lex = float(cands[0].get("lexical_score") or 0.0)
    structured = _has_strength_form_cues(text)
    if structured and top_lex >= 0.90 and margin >= thr.drug_margin:
        return SelectionResult(
            [str(cands[0]["id"])],
            True,
            "name_strength_form_unique_support",
            False,
        )
    if top_lex >= 0.95 and margin >= thr.drug_margin:
        return SelectionResult(
            [str(cands[0]["id"])], True, "lexical_and_structured_support", False
        )
    if top >= thr.drug_top and margin >= thr.drug_margin:
        return SelectionResult(
            [str(cands[0]["id"])], True, "top_score_with_margin", False
        )
    return SelectionResult([], False, "ambiguous_needs_judge", True)


@dataclass
class DocumentCandidateState:
    entities: list[dict[str, Any]] = field(default_factory=list)
    ambiguous: list[BatchItem] = field(default_factory=list)
    accepted_count: int = 0
    unresolved_count: int = 0


def apply_deterministic_selection(
    doc_id: str,
    document: str,
    entities: list[dict[str, Any]],
    thresholds: CandidateThresholds | None = None,
) -> DocumentCandidateState:
    """Mutates entity candidate fields; collects ambiguous items for batch judge."""
    thr = thresholds or CandidateThresholds.from_env()
    state = DocumentCandidateState()
    for i, ent in enumerate(entities):
        item = dict(ent)
        etype = item.get("type")
        local = list(item.get("local_candidates") or item.get("candidates_meta") or [])
        if etype == "CHẨN_ĐOÁN":
            result = select_diagnosis_deterministic(local, thr)
            if result.accepted:
                item["candidates"] = result.selected_ids
                item["candidate_decision"] = result.reason
                state.accepted_count += 1
            else:
                item["candidates"] = []
                item["candidate_decision"] = result.reason
                if result.needs_judge and local:
                    start, end = item["position"]
                    ctx = document[max(0, start - 120) : min(len(document), end + 120)]
                    state.ambiguous.append(
                        BatchItem(
                            item_id=f"{doc_id}:e{i}",
                            document_id=doc_id,
                            entity_text=item["text"],
                            entity_type=etype,
                            context=ctx,
                            candidates=local,
                        )
                    )
                    state.unresolved_count += 1
                item["entity_id"] = f"{doc_id}:e{i}"
        elif etype == "THUỐC":
            result = select_drug_deterministic(str(item.get("text") or ""), local, thr)
            if result.accepted:
                item["candidates"] = result.selected_ids
                item["candidate_decision"] = result.reason
                state.accepted_count += 1
            else:
                item["candidates"] = []
                item["candidate_decision"] = result.reason
                if result.needs_judge and local:
                    start, end = item["position"]
                    ctx = document[max(0, start - 80) : min(len(document), end + 80)]
                    state.ambiguous.append(
                        BatchItem(
                            item_id=f"{doc_id}:e{i}",
                            document_id=doc_id,
                            entity_text=item["text"],
                            entity_type=etype,
                            context=ctx,
                            candidates=local,
                        )
                    )
                    state.unresolved_count += 1
                item["entity_id"] = f"{doc_id}:e{i}"
        else:
            item.pop("candidates", None)
        if etype in {"CHẨN_ĐOÁN", "THUỐC"} and "entity_id" not in item:
            item["entity_id"] = f"{doc_id}:e{i}"
        state.entities.append(item)
    return state
