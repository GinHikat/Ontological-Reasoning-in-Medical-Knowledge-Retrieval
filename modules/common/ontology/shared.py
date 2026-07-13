"""One ontology layer for fair NER vs LLM comparison."""

from __future__ import annotations

from typing import Any

from modules.components.linking.hybrid import HybridEntityLinker
from modules.core.constants import (
    TARGET_LABEL_DIAGNOSIS,
    TARGET_LABEL_DRUG,
)
from modules.core.schemas import Document, EntityMention, FinalEntity
from modules.external.ontology_retrieval import LocalOntologyRetriever


class SharedOntologyLayer:
    """ICD/RxNorm linking used by both active extraction tracks.

    - ``hybrid_linker``: SapBERT + lexical (baseline / ClinicalEntityLinkingPipeline)
    - ``teacher_retriever``: lexical(+optional embedding) used by schema LLM path

    Prefer one path per experiment so NER vs LLM is not confounded by linkers.
    """

    def __init__(
        self,
        *,
        mode: str = "hybrid",
        use_embeddings: bool = False,
    ) -> None:
        if mode not in {"hybrid", "teacher"}:
            raise ValueError("mode must be 'hybrid' or 'teacher'")
        self.mode = mode
        self._hybrid = HybridEntityLinker() if mode == "hybrid" else None
        self._teacher = (
            LocalOntologyRetriever(use_embeddings=use_embeddings)
            if mode == "teacher"
            else None
        )

    def link_mentions(
        self,
        document: Document,
        mentions: list[EntityMention],
    ) -> list[FinalEntity]:
        if self.mode == "hybrid":
            assert self._hybrid is not None
            return self._hybrid.link(document, mentions)
        return self._link_teacher(document, mentions)

    def _link_teacher(
        self,
        document: Document,
        mentions: list[EntityMention],
    ) -> list[FinalEntity]:
        assert self._teacher is not None
        out: list[FinalEntity] = []
        for m in mentions:
            candidates: list[str] = []
            if m.label == TARGET_LABEL_DIAGNOSIS:
                raw = self._teacher.retrieve_icd(m.text)
                if raw:
                    candidates = [raw[0].id]
            elif m.label == TARGET_LABEL_DRUG:
                raw = self._teacher.retrieve_rxnorm(m.text)
                if raw:
                    candidates = [raw[0].id]
            out.append(
                FinalEntity(
                    text=m.text,
                    type=m.label,
                    span=m.span,
                    candidates=candidates,
                    assertions=[],
                    confidence=m.confidence,
                    source=m.source,
                    metadata=dict(m.metadata or {}),
                )
            )
        return out

    def retrieve_for_type(
        self,
        text: str,
        label: str,
        *,
        top_n: int = 5,
    ) -> list[dict[str, Any]]:
        ret = self._teacher or LocalOntologyRetriever(use_embeddings=False)
        if label == TARGET_LABEL_DIAGNOSIS:
            return [c.as_dict() for c in ret.retrieve_icd(text)[:top_n]]
        if label == TARGET_LABEL_DRUG:
            return [c.as_dict() for c in ret.retrieve_rxnorm(text)[:top_n]]
        return []
