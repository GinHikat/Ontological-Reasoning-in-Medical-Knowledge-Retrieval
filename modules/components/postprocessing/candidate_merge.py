from __future__ import annotations

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.core.constants import TARGET_LABEL_SYMPTOM
from modules.core.schemas import Document, EntityMention


def _source_rank(mention: EntityMention) -> int:
    """Higher is better. Explicit section > exact ontology > NER > generic regex."""
    src = (mention.source or "").lower()
    meta = mention.metadata or {}

    if src == "section_recall" or meta.get("section_recall"):
        return 400
    if src in {"ontology_drug_recall", "ontology_diagnosis_recall"} or meta.get(
        "ontology_drug_recall"
    ) or meta.get("ontology_diagnosis_recall"):
        return 300
    if src == "lab_pair_recall" or meta.get("lab_pair_recall"):
        return 280
    if src.startswith("rule:") or meta.get("rule_based_recall"):
        return 100
    if src in {"vihealthbert", "ner", "unknown", "pipeline"} or "bert" in src:
        return 200
    return 150


def _label_preference(mention: EntityMention, other: EntityMention) -> EntityMention:
    """Resolve identical spans with different labels using evidence precedence."""
    if (
        mention.label == TARGET_LABEL_SYMPTOM
        and mention.source == "section_recall"
        and other.label != TARGET_LABEL_SYMPTOM
    ):
        return mention
    if (
        other.label == TARGET_LABEL_SYMPTOM
        and other.source == "section_recall"
        and mention.label != TARGET_LABEL_SYMPTOM
    ):
        return other

    if mention.source == "ontology_drug_recall" and other.source != "ontology_drug_recall":
        if mention.label == "THUỐC":
            return mention
    if other.source == "ontology_drug_recall" and mention.source != "ontology_drug_recall":
        if other.label == "THUỐC":
            return other

    if mention.source == "ontology_diagnosis_recall" and other.source == "section_recall":
        if other.label == TARGET_LABEL_SYMPTOM:
            return other
    if other.source == "ontology_diagnosis_recall" and mention.source == "section_recall":
        if mention.label == TARGET_LABEL_SYMPTOM:
            return mention

    mr, or_ = _source_rank(mention), _source_rank(other)
    if mr != or_:
        return mention if mr > or_ else other
    if mention.confidence != other.confidence:
        return mention if mention.confidence > other.confidence else other
    return mention


class CandidateMergePostProcessor(BaseMentionPostProcessor):
    """Deterministic merge for identical-span conflicts and nested noise."""

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        trace = []
        for m in mentions:
            trace.append(
                {
                    "text": m.text,
                    "label": m.label,
                    "start": m.span.start,
                    "end": m.span.end,
                    "source": m.source,
                    "confidence": m.confidence,
                }
            )
        document.metadata["candidate_merge_trace"] = trace

        # One entity per exact [start, end]
        best: dict[tuple[int | None, int | None], EntityMention] = {}
        order: list[tuple[int | None, int | None]] = []

        for mention in mentions:
            key = (mention.span.start, mention.span.end)
            if key not in best:
                best[key] = mention
                order.append(key)
            else:
                best[key] = _label_preference(best[key], mention)

        candidates = [best[k] for k in order]

        def length(m: EntityMention) -> int:
            if m.span.start is None or m.span.end is None:
                return 0
            return int(m.span.end) - int(m.span.start)

        def contains(outer: EntityMention, inner: EntityMention) -> bool:
            if (
                outer.span.start is None
                or outer.span.end is None
                or inner.span.start is None
                or inner.span.end is None
            ):
                return False
            return (
                int(outer.span.start) <= int(inner.span.start)
                and int(inner.span.end) <= int(outer.span.end)
                and (outer.span.start, outer.span.end)
                != (inner.span.start, inner.span.end)
            )

        # Drop long outer spans that fully contain a higher-ranked / more specific span
        sorted_ments = sorted(
            candidates,
            key=lambda m: (-_source_rank(m), -m.confidence, length(m)),
        )
        kept: list[EntityMention] = []
        for mention in sorted_ments:
            drop = False
            for existing in kept:
                if contains(mention, existing):
                    # Long outer container around a better inner entity
                    if length(mention) >= max(40, int(length(existing) * 1.5)):
                        drop = True
                        break
                if contains(existing, mention) and existing.label == mention.label:
                    drop = True
                    break
            if not drop:
                kept.append(mention)

        return sorted(
            kept,
            key=lambda m: (
                m.span.start if m.span.start is not None else 10**9,
                m.span.end if m.span.end is not None else 10**9,
            ),
        )
