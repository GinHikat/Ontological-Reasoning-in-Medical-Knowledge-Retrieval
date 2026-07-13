"""V10: newest v7 once, freeze finals, replace high-confidence LLM overlaps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from modules.components.assertions.rule_based import RuleBasedAssertionDetector
from modules.components.formatting.competition_json import CompetitionJSONFormatter
from modules.components.linking.hybrid import HybridEntityLinker
from modules.components.llm.schemas import ALLOWED_LLM_TYPES, DEFAULT_MODEL
from modules.components.postprocessing.llm_conflict_resolution import (
    OverlapHit,
    candidate_lexically_consistent,
    classify_one_to_one,
    decision_to_dict,
    find_overlapping_v7,
    load_diagnosis_name_index,
    load_drug_terms_by_rxcui,
)
from modules.components.postprocessing.llm_recall import (
    document_sha256,
    load_cache_record,
    spans_overlap,
)
from modules.components.structure.section_parser import VietnameseClinicalSectionParser
from modules.core.constants import TARGET_LABEL_DIAGNOSIS, TARGET_LABEL_DRUG
from modules.core.schemas import Document, EntityMention, FinalEntity, Span
from modules.pipelines.base import BasePipeline
from modules.pipelines.baseline.pipeline import build_baseline_hybrid_pipeline as build_v7_structured_pipeline
from v9 import _entity_sort_key, _freeze_final_entities


class LLMConflictResolutionPipeline(BasePipeline):
    """Run newest v7 once, freeze finals, replace selected overlapping LLM spans.

    First v10 is replacement-only: no free-form additive LLM entities.
    """

    def __init__(
        self,
        base_pipeline: BasePipeline,
        linker: HybridEntityLinker,
        assertion_detector: RuleBasedAssertionDetector,
        cache_dir: str | Path | None = None,
        require_cache: bool = True,
        model_name: str = DEFAULT_MODEL,
        diagnosis_csv: str | Path | None = None,
        drug_csv: str | Path | None = None,
    ):
        root = Path(__file__).resolve().parents[2]
        self.base_pipeline = base_pipeline
        self.linker = linker
        self.assertion_detector = assertion_detector
        self.cache_dir = Path(cache_dir) if cache_dir else root / "cache" / "v9_llm_recall"
        self.require_cache = require_cache
        self.model_name = model_name
        self._formatter = CompetitionJSONFormatter(
            include_empty_candidates_for_linkable_types=True
        )
        diag_path = (
            Path(diagnosis_csv)
            if diagnosis_csv
            else root / "v_dataset" / "viettel" / "base" / "short_diagnosis.csv"
        )
        drug_path = (
            Path(drug_csv)
            if drug_csv
            else root / "v_dataset" / "viettel" / "base" / "short_drug.csv"
        )
        self._diagnosis_names = load_diagnosis_name_index(diag_path)
        self._drug_terms = load_drug_terms_by_rxcui(drug_path)

    def process_document(self, document: Document) -> list[FinalEntity]:
        # --- Phase 1: newest v7 once ---
        v7_entities = self.base_pipeline.process_document(document)
        frozen_v7 = _freeze_final_entities(v7_entities)
        document.metadata["base_v7_entities"] = self._formatter.format(frozen_v7)
        document.metadata["base_v7_trace_txt"] = document.metadata.get("trace_txt", "")

        diagnostics: dict[str, Any] = {
            "document_sha256": document_sha256(document.text),
            "frozen_v7_count": len(frozen_v7),
            "cache_hit": False,
            "invalid_rejected": [],
            "exact_span_duplicates_skipped": [],
            "overlap_still_rejected": [],
            "multi_v7_overlap_rejected": [],
            "v7_conflict_rejected": [],
            "replacement_candidates": [],
            "replacements_accepted": [],
            "replacements_rejected_post_link": [],
            "v7_removed_for_replacement": [],
            "category_counts": {"A": 0, "B": 0, "C": 0, "D": 0},
            "final_replacements": 0,
        }

        sha = diagnostics["document_sha256"]
        record = load_cache_record(self.cache_dir, sha)
        diagnostics["cache_hit"] = record is not None

        if record is None:
            msg = (
                f"LLM conflict cache miss for doc_id={document.doc_id} "
                f"sha256={sha} under {self.cache_dir}"
            )
            diagnostics["error"] = msg
            document.metadata["llm_conflict_diagnostics"] = diagnostics
            if self.require_cache:
                raise FileNotFoundError(msg)
            document.metadata["trace_txt"] = self._append_trace(
                document.metadata.get("trace_txt", ""), diagnostics, []
            )
            return frozen_v7

        prompt_version = (
            (record.get("prompt_versions") or {}).get("proposer")
            or (record.get("generation_settings") or {}).get("proposer_prompt_version")
            or "v9_llm_recall_proposer_v1"
        )
        model = record.get("model") or self.model_name

        # --- Phase 2: classify overlap replacements (no additive path) ---
        pending: list[dict[str, Any]] = []
        claimed_v7: set[int] = set()
        claimed_llm_spans: set[tuple[int, int]] = set()

        for cand in record.get("final_accepted_candidates") or []:
            text = str(cand.get("text", ""))
            ent_type = str(cand.get("type", ""))
            start = cand.get("start")
            end = cand.get("end")
            line_id = str(cand.get("line_id", ""))
            proposer_type = str(cand.get("proposer_type", ent_type))
            verifier_type = str(cand.get("verifier_type", ent_type))

            reason = self._validate_candidate(
                document.text, text, ent_type, start, end, proposer_type, verifier_type
            )
            if reason is not None:
                diagnostics["invalid_rejected"].append(
                    {
                        "text": text,
                        "type": ent_type,
                        "start": start,
                        "end": end,
                        "reason": reason,
                    }
                )
                continue

            assert isinstance(start, int) and isinstance(end, int)

            overlaps = find_overlapping_v7(start, end, frozen_v7)
            if not overlaps:
                # First v10: no free-form additions.
                continue

            if len(overlaps) != 1:
                diagnostics["multi_v7_overlap_rejected"].append(
                    {
                        "text": text,
                        "type": ent_type,
                        "start": start,
                        "end": end,
                        "overlap_count": len(overlaps),
                        "existing": [
                            {
                                "text": e.text,
                                "type": e.type,
                                "start": e.span.start,
                                "end": e.span.end,
                                "v7_index": idx,
                            }
                            for idx, e in overlaps
                        ],
                        "reason": "MULTI_V7_OVERLAP",
                    }
                )
                continue

            v7_index, v7_entity = overlaps[0]
            assert v7_entity.span.start is not None and v7_entity.span.end is not None
            v7_start, v7_end = int(v7_entity.span.start), int(v7_entity.span.end)

            if v7_start == start and v7_end == end and v7_entity.type == ent_type:
                diagnostics["exact_span_duplicates_skipped"].append(
                    {
                        "text": text,
                        "type": ent_type,
                        "start": start,
                        "end": end,
                        "reason": "EXACT_SPAN_SAME_TYPE",
                    }
                )
                continue

            hit = OverlapHit(
                llm_text=text,
                llm_type=ent_type,
                llm_start=start,
                llm_end=end,
                v7_index=v7_index,
                v7_text=v7_entity.text,
                v7_type=v7_entity.type,
                v7_start=v7_start,
                v7_end=v7_end,
            )
            decision = classify_one_to_one(hit)
            if decision is None:
                diagnostics["overlap_still_rejected"].append(
                    {
                        "text": text,
                        "type": ent_type,
                        "start": start,
                        "end": end,
                        "existing_text": v7_entity.text,
                        "existing_type": v7_entity.type,
                        "existing_start": v7_start,
                        "existing_end": v7_end,
                        "reason": "NO_HIGH_CONFIDENCE_RULE",
                    }
                )
                continue

            # One-to-one claims: reject if another pending replacement already
            # claimed this v7 entity or this LLM span.
            if v7_index in claimed_v7 or (start, end) in claimed_llm_spans:
                diagnostics["v7_conflict_rejected"].append(
                    {
                        **decision_to_dict(decision),
                        "reason": "CLAIM_CONFLICT",
                    }
                )
                continue

            # Replacement span must not overlap any *other* frozen v7 entity.
            foreign = [
                (idx, e)
                for idx, e in find_overlapping_v7(start, end, frozen_v7)
                if idx != v7_index
            ]
            if foreign:
                diagnostics["v7_conflict_rejected"].append(
                    {
                        **decision_to_dict(decision),
                        "reason": "FOREIGN_V7_OVERLAP",
                        "foreign": [
                            {
                                "text": e.text,
                                "type": e.type,
                                "start": e.span.start,
                                "end": e.span.end,
                            }
                            for _, e in foreign
                        ],
                    }
                )
                continue

            claimed_v7.add(v7_index)
            claimed_llm_spans.add((start, end))
            entry = {
                **decision_to_dict(decision),
                "line_id": line_id,
                "proposer_type": proposer_type,
                "verifier_type": verifier_type,
                "proposal_id": cand.get("proposal_id"),
                "model": model,
                "prompt_version": prompt_version,
            }
            pending.append(entry)
            diagnostics["replacement_candidates"].append(entry)

        # --- Phase 3: link + assert only replacement mentions ---
        mentions: list[EntityMention] = []
        for entry in pending:
            mentions.append(
                EntityMention(
                    text=entry["text"],
                    label=entry["type"],
                    span=Span(entry["start"], entry["end"]),
                    confidence=1.0,
                    source="llm_conflict_resolution",
                    metadata={
                        "llm_conflict_resolution": True,
                        "replacement_category": entry["category"],
                        "replacement_reason": entry["reason"],
                        "replaced_v7_text": entry["existing_text"],
                        "replaced_v7_type": entry["existing_type"],
                        "replaced_v7_start": entry["existing_start"],
                        "replaced_v7_end": entry["existing_end"],
                        "model": entry["model"],
                        "prompt_version": entry["prompt_version"],
                        "verified": True,
                        "line_id": entry["line_id"],
                        "proposer_type": entry["proposer_type"],
                        "verifier_type": entry["verifier_type"],
                        "proposal_id": entry.get("proposal_id"),
                    },
                )
            )

        linked: list[FinalEntity] = []
        if mentions:
            linked = self.linker.link(document, mentions)
            linked = self.assertion_detector.apply(document, linked)

        eligible: list[FinalEntity] = []
        accepted_v7_indices: set[int] = set()

        for entity, entry in zip(linked, pending):
            reject_reason = self._post_link_reject(entity, entry)
            if reject_reason is not None:
                diagnostics["replacements_rejected_post_link"].append(
                    {**entry, "reject_reason": reject_reason}
                )
                continue

            eligible.append(entity)
            accepted_v7_indices.add(int(entry["v7_index"]))
            diagnostics["replacements_accepted"].append(
                {
                    **entry,
                    "candidates": list(entity.candidates),
                    "assertions": list(entity.assertions),
                    "final_type": entity.type,
                }
            )
            diagnostics["category_counts"][entry["category"]] = (
                diagnostics["category_counts"].get(entry["category"], 0) + 1
            )

        survivors: list[FinalEntity] = []
        for idx, entity in enumerate(frozen_v7):
            if idx in accepted_v7_indices:
                diagnostics["v7_removed_for_replacement"].append(
                    {
                        "text": entity.text,
                        "type": entity.type,
                        "start": entity.span.start,
                        "end": entity.span.end,
                        "v7_index": idx,
                    }
                )
                continue
            survivors.append(entity)

        # Safety: eligible replacements must not overlap surviving v7 entities.
        safe_eligible: list[FinalEntity] = []
        for entity in eligible:
            assert entity.span.start is not None and entity.span.end is not None
            conflict = False
            for other in survivors:
                if other.span.start is None or other.span.end is None:
                    continue
                if spans_overlap(
                    int(entity.span.start),
                    int(entity.span.end),
                    int(other.span.start),
                    int(other.span.end),
                ):
                    conflict = True
                    diagnostics["replacements_rejected_post_link"].append(
                        {
                            "text": entity.text,
                            "type": entity.type,
                            "start": entity.span.start,
                            "end": entity.span.end,
                            "reject_reason": "SURVIVOR_OVERLAP",
                            "other_text": other.text,
                        }
                    )
                    break
            if not conflict:
                safe_eligible.append(entity)

        diagnostics["final_replacements"] = len(safe_eligible)
        document.metadata["llm_conflict_diagnostics"] = diagnostics

        merged = list(survivors) + safe_eligible
        merged.sort(key=_entity_sort_key)
        document.metadata["trace_txt"] = self._append_trace(
            document.metadata.get("trace_txt", ""), diagnostics, safe_eligible
        )
        return merged

    def _post_link_reject(self, entity: FinalEntity, entry: dict[str, Any]) -> str | None:
        expected = str(entry.get("proposer_type") or entry["type"])
        if entity.type != expected:
            return f"linker_type_change:{entity.type}"

        category = entry["category"]
        if category == "B" and "isNegated" not in entity.assertions:
            return "negation_not_detected"

        if entity.type == TARGET_LABEL_DIAGNOSIS:
            if not entity.candidates:
                return "empty_icd"
            if not candidate_lexically_consistent(
                entity.text,
                entity.type,
                list(entity.candidates),
                diagnosis_names=self._diagnosis_names,
            ):
                return "icd_lexical_mismatch"

        if entity.type == TARGET_LABEL_DRUG:
            if not entity.candidates or len(entity.candidates) != 1:
                return "bad_rxnorm"
            if not candidate_lexically_consistent(
                entity.text,
                entity.type,
                list(entity.candidates),
                drug_terms_by_rxcui=self._drug_terms,
            ):
                return "rxnorm_lexical_mismatch"

        return None

    @staticmethod
    def _validate_candidate(
        original: str,
        text: str,
        ent_type: str,
        start: Any,
        end: Any,
        proposer_type: str,
        verifier_type: str,
    ) -> str | None:
        if ent_type not in ALLOWED_LLM_TYPES:
            return f"disallowed_type:{ent_type}"
        if not isinstance(start, int) or not isinstance(end, int):
            return "non_int_offsets"
        if start < 0 or end < start or end > len(original):
            return "offset_out_of_range"
        if original[start:end] != text:
            return "text_offset_mismatch"
        if proposer_type != verifier_type:
            return "proposer_verifier_type_mismatch"
        if ent_type != proposer_type:
            return "stored_type_mismatch"
        if not text:
            return "empty_text"
        return None

    @staticmethod
    def _append_trace(
        base_trace: str,
        diagnostics: dict[str, Any],
        replacements: list[FinalEntity],
    ) -> str:
        counts = diagnostics.get("category_counts") or {}
        lines = [
            base_trace.rstrip(),
            "",
            "=" * 80,
            "V10 LLM CONFLICT RESOLUTION (post-freeze)",
            "=" * 80,
            f"frozen_v7_count: {diagnostics.get('frozen_v7_count')}",
            f"cache_hit: {diagnostics.get('cache_hit')}",
            f"sha256: {diagnostics.get('document_sha256')}",
            f"replacement_candidates: {len(diagnostics.get('replacement_candidates') or [])}",
            f"replacements_rejected_post_link: "
            f"{len(diagnostics.get('replacements_rejected_post_link') or [])}",
            f"multi_v7_overlap_rejected: "
            f"{len(diagnostics.get('multi_v7_overlap_rejected') or [])}",
            f"overlap_still_rejected: {len(diagnostics.get('overlap_still_rejected') or [])}",
            f"final_replacements: {diagnostics.get('final_replacements')}",
            f"category_counts: A={counts.get('A', 0)} B={counts.get('B', 0)} "
            f"C={counts.get('C', 0)} D={counts.get('D', 0)}",
            "",
            "Accepted replacements:",
        ]
        if not replacements:
            lines.append("  (none)")
        for e in replacements:
            cat = e.metadata.get("replacement_category")
            lines.append(
                f"  [{e.span.start}:{e.span.end}] {e.type} | {e.text!r} | "
                f"cat={cat} | cands={e.candidates} | asserts={e.assertions} | "
                f"replaced={e.metadata.get('replaced_v7_text')!r}"
            )
        if diagnostics.get("error"):
            lines.append(f"ERROR: {diagnostics['error']}")
        return "\n".join(lines) + "\n"


def build_v10_llm_conflict_resolution_pipeline(
    model_name: str = "vihealthbert",
    llm_cache_dir: str | None = None,
    require_llm_cache: bool = True,
) -> LLMConflictResolutionPipeline:
    """V10: delegate to newest v7, freeze finals, apply LLM overlap replacements."""

    section_parser = VietnameseClinicalSectionParser()
    base = build_v7_structured_pipeline(model_name=model_name)
    linker = HybridEntityLinker()
    assertion_detector = RuleBasedAssertionDetector(
        restrict_to_eligible_labels=True,
        section_parser=section_parser,
        use_section_parser=True,
        detect_family=True,
    )
    return LLMConflictResolutionPipeline(
        base_pipeline=base,
        linker=linker,
        assertion_detector=assertion_detector,
        cache_dir=llm_cache_dir,
        require_cache=require_llm_cache,
        model_name=DEFAULT_MODEL,
    )
