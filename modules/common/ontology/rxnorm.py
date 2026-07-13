"""RxNorm retrieval facade (shared by NER and LLM)."""

from __future__ import annotations

from typing import Any

from modules.external.ontology_retrieval import LocalOntologyRetriever


def retrieve_rxnorm_candidates(
    mention_text: str,
    *,
    retriever: LocalOntologyRetriever | None = None,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    ret = retriever or LocalOntologyRetriever(use_embeddings=False, top_n=max(20, top_n))
    cands = ret.retrieve_rxnorm(mention_text)[:top_n]
    return [c.as_dict() if hasattr(c, "as_dict") else c for c in cands]
