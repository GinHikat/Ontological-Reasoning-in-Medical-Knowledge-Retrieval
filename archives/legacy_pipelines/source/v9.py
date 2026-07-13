from __future__ import annotations

"""V9: newest v7 once, freeze finals, append validated LLM-only entities."""

from copy import deepcopy
from pathlib import Path
from typing import Any

from modules.components.assertions.rule_based import RuleBasedAssertionDetector
from modules.components.formatting.competition_json import CompetitionJSONFormatter
from modules.components.linking.hybrid import HybridEntityLinker
from modules.components.llm.schemas import ALLOWED_LLM_TYPES, DEFAULT_MODEL
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


def _entity_sort_key(entity: FinalEntity) -> tuple:
    start = entity.span.start if entity.span.start is not None else -1
    end = entity.span.end if entity.span.end is not None else -1
    return (start, end, entity.type, entity.text)


def _freeze_final_entities(entities: list[FinalEntity]) -> list[FinalEntity]:
    """Deep-copy finalized v7 entities so later steps cannot mutate them."""
    frozen: list[FinalEntity] = []
    for e in entities:
        frozen.append(
            FinalEntity(
                text=e.text,
                type=e.type,
                span=Span(e.span.start, e.span.end),
                candidates=list(e.candidates),
                assertions=list(e.assertions),
                confidence=e.confidence,
                source=e.source,
                metadata=deepcopy(e.metadata),
            )
        )
    return frozen


class LLMAdditiveRecallPipeline(BasePipeline):
    """Run newest v7 once, freeze finals, then link/assert only LLM additions."""

    def __init__(
        self,
        base_pipeline: BasePipeline,
        linker: HybridEntityLinker,
        assertion_detector: RuleBasedAssertionDetector,
        cache_dir: str | Path | None = None,
        require_cache: bool = True,
        model_name: str = DEFAULT_MODEL,
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
            "exact_span_duplicates_skipped": [],
            "overlap_rejected": [],
            "invalid_rejected": [],
            "llm_internal_duplicates_rejected": [],
            "llm_internal_overlaps_rejected": [],
            "type_disagreements_logged": [],
            "unlinked_diagnoses_excluded": [],
            "unlinked_drugs_excluded": [],
            "linker_type_changes_rejected": [],
            "added": [],
            "final_llm_additions": 0,
        }

        sha = diagnostics["document_sha256"]
        record = load_cache_record(self.cache_dir, sha)
        diagnostics["cache_hit"] = record is not None

        if record is None:
            msg = (
                f"LLM recall cache miss for doc_id={document.doc_id} "
                f"sha256={sha} under {self.cache_dir}"
            )
            diagnostics["error"] = msg
            document.metadata["llm_recall_diagnostics"] = diagnostics
            if self.require_cache:
                raise FileNotFoundError(msg)
            document.metadata["trace_txt"] = self._append_llm_trace(
                document.metadata.get("trace_txt", ""), diagnostics, []
            )
            return frozen_v7

        frozen_spans = [
            (int(e.span.start), int(e.span.end), e.type, e.text)
            for e in frozen_v7
            if e.span.start is not None and e.span.end is not None
        ]

        prompt_version = (
            (record.get("prompt_versions") or {}).get("proposer")
            or (record.get("generation_settings") or {}).get("proposer_prompt_version")
            or "v9_llm_recall_proposer_v1"
        )
        model = record.get("model") or self.model_name

        # --- Phase 2: select non-overlapping LLM candidates ---
        selected_mentions: list[EntityMention] = []
        selected_spans: list[tuple[int, int, str, str]] = []

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

            exact_hit = False
            for e_start, e_end, e_label, e_text in frozen_spans:
                if e_start == start and e_end == end:
                    exact_hit = True
                    entry = {
                        "text": text,
                        "llm_type": ent_type,
                        "existing_type": e_label,
                        "existing_text": e_text,
                        "start": start,
                        "end": end,
                        "reason": "EXACT_SPAN_DUPLICATE",
                    }
                    if e_label != ent_type:
                        entry["type_disagreement"] = True
                        diagnostics["type_disagreements_logged"].append(entry)
                    diagnostics["exact_span_duplicates_skipped"].append(entry)
                    break
            if exact_hit:
                continue

            overlap_hit = False
            for e_start, e_end, e_label, e_text in frozen_spans:
                if spans_overlap(start, end, e_start, e_end):
                    overlap_hit = True
                    diagnostics["overlap_rejected"].append(
                        {
                            "text": text,
                            "type": ent_type,
                            "start": start,
                            "end": end,
                            "existing_text": e_text,
                            "existing_type": e_label,
                            "existing_start": e_start,
                            "existing_end": e_end,
                            "reason": "OVERLAP_REJECTED",
                        }
                    )
                    break
            if overlap_hit:
                continue

            # Dedup / overlap among LLM-only candidates (conservative).
            llm_dup = False
            for s_start, s_end, s_type, s_text in selected_spans:
                if s_start == start and s_end == end:
                    llm_dup = True
                    if s_type == ent_type:
                        diagnostics["llm_internal_duplicates_rejected"].append(
                            {
                                "text": text,
                                "type": ent_type,
                                "start": start,
                                "end": end,
                                "reason": "LLM_EXACT_DUP_KEEP_ONE",
                            }
                        )
                    else:
                        # Conflicting types on same span → reject both later.
                        diagnostics["llm_internal_duplicates_rejected"].append(
                            {
                                "text": text,
                                "type": ent_type,
                                "other_type": s_type,
                                "start": start,
                                "end": end,
                                "reason": "LLM_TYPE_CONFLICT_REJECT_BOTH",
                            }
                        )
                        # Mark prior for removal.
                        for m in selected_mentions:
                            if (
                                m.span.start == start
                                and m.span.end == end
                                and m.label == s_type
                            ):
                                m.metadata["v9_reject"] = "LLM_TYPE_CONFLICT"
                    break
                if spans_overlap(start, end, s_start, s_end):
                    llm_dup = True
                    diagnostics["llm_internal_overlaps_rejected"].append(
                        {
                            "text": text,
                            "type": ent_type,
                            "start": start,
                            "end": end,
                            "other_text": s_text,
                            "other_type": s_type,
                            "other_start": s_start,
                            "other_end": s_end,
                            "reason": "LLM_INTERNAL_OVERLAP_REJECT_BOTH",
                        }
                    )
                    for m in selected_mentions:
                        if m.span.start == s_start and m.span.end == s_end:
                            m.metadata["v9_reject"] = "LLM_INTERNAL_OVERLAP"
                    break
            if llm_dup:
                continue

            mention = EntityMention(
                text=text,
                label=ent_type,
                span=Span(start, end),
                confidence=1.0,
                source="llm_recall",
                metadata={
                    "llm_recall": True,
                    "model": model,
                    "prompt_version": prompt_version,
                    "verified": True,
                    "line_id": line_id,
                    "proposer_type": proposer_type,
                    "verifier_type": verifier_type,
                    "proposal_id": cand.get("proposal_id"),
                },
            )
            selected_mentions.append(mention)
            selected_spans.append((start, end, ent_type, text))
            diagnostics["added"].append(
                {
                    "text": text,
                    "type": ent_type,
                    "start": start,
                    "end": end,
                    "line_id": line_id,
                    "proposer_type": proposer_type,
                    "verifier_type": verifier_type,
                }
            )

        selected_mentions = [
            m for m in selected_mentions if not m.metadata.get("v9_reject")
        ]

        # --- Phase 3: link + assert ONLY new mentions ---
        linked: list[FinalEntity] = []
        if selected_mentions:
            linked = self.linker.link(document, selected_mentions)
            linked = self.assertion_detector.apply(document, linked)

        eligible_llm: list[FinalEntity] = []
        for entity in linked:
            # Reject linker type changes vs proposer/verifier agreement.
            expected = str(entity.metadata.get("proposer_type") or entity.type)
            if entity.type != expected:
                diagnostics["linker_type_changes_rejected"].append(
                    {
                        "text": entity.text,
                        "expected_type": expected,
                        "linker_type": entity.type,
                        "start": entity.span.start,
                        "end": entity.span.end,
                    }
                )
                continue

            if entity.type == TARGET_LABEL_DIAGNOSIS and not entity.candidates:
                diagnostics["unlinked_diagnoses_excluded"].append(
                    {
                        "text": entity.text,
                        "start": entity.span.start,
                        "end": entity.span.end,
                    }
                )
                continue

            if entity.type == TARGET_LABEL_DRUG:
                if not entity.candidates or len(entity.candidates) != 1:
                    diagnostics["unlinked_drugs_excluded"].append(
                        {
                            "text": entity.text,
                            "start": entity.span.start,
                            "end": entity.span.end,
                            "candidates": list(entity.candidates),
                        }
                    )
                    continue

            eligible_llm.append(entity)

        diagnostics["final_llm_additions"] = len(eligible_llm)
        document.metadata["llm_recall_diagnostics"] = diagnostics

        # --- Phase 4: merge frozen v7 + eligible LLM; stable sort ---
        merged = list(frozen_v7) + eligible_llm
        merged.sort(key=_entity_sort_key)

        document.metadata["trace_txt"] = self._append_llm_trace(
            document.metadata.get("trace_txt", ""), diagnostics, eligible_llm
        )
        return merged

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
    def _append_llm_trace(
        base_trace: str,
        diagnostics: dict[str, Any],
        additions: list[FinalEntity],
    ) -> str:
        lines = [
            base_trace.rstrip(),
            "",
            "=" * 80,
            "V9 LLM ADDITIVE RECALL (post-freeze)",
            "=" * 80,
            f"frozen_v7_count: {diagnostics.get('frozen_v7_count')}",
            f"cache_hit: {diagnostics.get('cache_hit')}",
            f"sha256: {diagnostics.get('document_sha256')}",
            f"overlap_rejected: {len(diagnostics.get('overlap_rejected') or [])}",
            f"exact_dup_skipped: {len(diagnostics.get('exact_span_duplicates_skipped') or [])}",
            f"unlinked_diagnoses_excluded: {len(diagnostics.get('unlinked_diagnoses_excluded') or [])}",
            f"unlinked_drugs_excluded: {len(diagnostics.get('unlinked_drugs_excluded') or [])}",
            f"final_llm_additions: {diagnostics.get('final_llm_additions')}",
            "",
            "Final LLM additions:",
        ]
        if not additions:
            lines.append("  (none)")
        for e in additions:
            lines.append(
                f"  [{e.span.start}:{e.span.end}] {e.type} | {e.text!r} | "
                f"cands={e.candidates} | asserts={e.assertions}"
            )
        if diagnostics.get("error"):
            lines.append(f"ERROR: {diagnostics['error']}")
        return "\n".join(lines) + "\n"


def build_v9_llm_recall_pipeline(
    model_name: str = "vihealthbert",
    llm_cache_dir: str | None = None,
    require_llm_cache: bool = True,
) -> LLMAdditiveRecallPipeline:
    """V9: delegate to newest v7, freeze finals, append validated LLM entities."""

    section_parser = VietnameseClinicalSectionParser()
    base = build_v7_structured_pipeline(model_name=model_name)
    # Reuse the same linker/assertion stack as v7 for LLM-only mentions.
    linker = HybridEntityLinker()
    assertion_detector = RuleBasedAssertionDetector(
        restrict_to_eligible_labels=True,
        section_parser=section_parser,
        use_section_parser=True,
        detect_family=True,
    )
    return LLMAdditiveRecallPipeline(
        base_pipeline=base,
        linker=linker,
        assertion_detector=assertion_detector,
        cache_dir=llm_cache_dir,
        require_cache=require_llm_cache,
        model_name=DEFAULT_MODEL,
    )
