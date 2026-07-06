from __future__ import annotations

import difflib

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from modules.components.linking.base import BaseEntityLinker
from modules.components.linking.dictionaries import CompetitionDictionaryStore
from modules.core.constants import (
    TARGET_LABEL_DIAGNOSIS,
    TARGET_LABEL_DRUG,
    TARGET_LABEL_SYMPTOM,
)
from modules.core.schemas import Document, EntityMention, FinalEntity


def get_lexical_similarity(str1: str, str2: str) -> float:
    if not str1 or not str2:
        return 0.0
    return difflib.SequenceMatcher(None, str(str1).lower(), str(str2).lower()).ratio()


def get_best_row_lexical_similarity(query: str, row) -> float:
    best_sim = 0.0
    for value in row.values:
        value_str = str(value)
        if not value_str or value_str == "nan":
            continue
        if "|" in value_str:
            for synonym in value_str.split("|"):
                best_sim = max(best_sim, get_lexical_similarity(query, synonym))
        else:
            best_sim = max(best_sim, get_lexical_similarity(query, value_str))
    return best_sim


class HybridEntityLinker(BaseEntityLinker):
    """V5-style SapBERT retrieval with lexical reranking and disease/symptom split."""

    def __init__(
        self,
        dictionary_store: CompetitionDictionaryStore | None = None,
        diagnosis_threshold: float = 0.6,
        drug_threshold: float = 0.6,
        candidate_semantic_floor: float = 0.5,
        lexical_weight: float = 0.5,
        top_k: int = 3,
    ):
        self.dictionary_store = dictionary_store or CompetitionDictionaryStore()
        self.diagnosis_threshold = diagnosis_threshold
        self.drug_threshold = drug_threshold
        self.candidate_semantic_floor = candidate_semantic_floor
        self.lexical_weight = lexical_weight
        self.top_k = top_k
        self._sapbert_vi = None
        self._sapbert_en = None

    def _get_sapbert_vi(self):
        if self._sapbert_vi is None:
            from modules.model.embedding_models import EmbeddingModels

            self._sapbert_vi = EmbeddingModels(
                model_choice="cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR"
            )
        return self._sapbert_vi

    def _get_sapbert_en(self):
        if self._sapbert_en is None:
            from modules.model.embedding_models import EmbeddingModels

            self._sapbert_en = EmbeddingModels(
                model_choice="cambridgeltl/SapBERT-from-PubMedBERT-fulltext"
            )
        return self._sapbert_en

    def _best_hybrid_match(
        self, query: str, embedding: np.ndarray, df, embeddings, id_column: str
    ):
        if df.empty or embeddings.size == 0 or embedding.size == 0:
            return None, -1.0

        sims = cosine_similarity(embedding, embeddings)[0]
        top_indices = np.argsort(sims)[-self.top_k :][::-1]

        best_hybrid_score = -1.0
        best_id = None
        best_semantic_score = -1.0

        for idx in top_indices:
            semantic_score = float(sims[idx])
            if semantic_score < self.candidate_semantic_floor:
                continue
            lexical_score = get_best_row_lexical_similarity(query, df.iloc[idx])
            hybrid_score = semantic_score + lexical_score * self.lexical_weight

            if hybrid_score > best_hybrid_score:
                best_hybrid_score = hybrid_score
                best_semantic_score = semantic_score
                best_id = str(df.iloc[idx][id_column])

        return best_id, best_semantic_score

    def link(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[FinalEntity]:
        bundle = self.dictionary_store.load()
        final_entities: list[FinalEntity] = []

        for mention in mentions:
            mapped_type = mention.label
            candidates: list[str] = []
            metadata = dict(mention.metadata)

            if mention.metadata.get("is_disease_like"):
                embedding = self._get_sapbert_vi().encode_text(
                    [mention.text.lower()], show_progress=False
                )
                best_diag_id, best_diag_sim = self._best_hybrid_match(
                    mention.text,
                    embedding,
                    bundle.diagnoses,
                    bundle.diagnosis_embeddings,
                    "id",
                )

                best_sym_sim = -1.0
                if (
                    not bundle.symptoms.empty
                    and bundle.symptom_embeddings.size > 0
                    and embedding.size > 0
                ):
                    sym_sims = cosine_similarity(embedding, bundle.symptom_embeddings)[
                        0
                    ]
                    best_sym_sim = float(sym_sims[int(np.argmax(sym_sims))])

                if (
                    best_diag_sim >= best_sym_sim
                    and best_diag_id is not None
                    and best_diag_sim >= self.diagnosis_threshold
                ):
                    mapped_type = TARGET_LABEL_DIAGNOSIS
                    candidates = [best_diag_id]
                    metadata["diagnosis_similarity"] = best_diag_sim
                    metadata["symptom_similarity"] = best_sym_sim
                else:
                    mapped_type = TARGET_LABEL_SYMPTOM
                    candidates = []
                    metadata["diagnosis_similarity"] = best_diag_sim
                    metadata["symptom_similarity"] = best_sym_sim

            elif mapped_type == TARGET_LABEL_DRUG:
                embedding = self._get_sapbert_en().encode_text(
                    [mention.text.lower()], show_progress=False
                )
                best_drug_id, best_drug_sim = self._best_hybrid_match(
                    mention.text,
                    embedding,
                    bundle.drugs,
                    bundle.drug_embeddings,
                    "rxcui",
                )
                if best_drug_id is not None and best_drug_sim >= self.drug_threshold:
                    candidates = [best_drug_id]
                metadata["drug_similarity"] = best_drug_sim

            final_entities.append(
                FinalEntity(
                    text=mention.text,
                    type=mapped_type,
                    span=mention.span,
                    candidates=candidates,
                    assertions=[],
                    confidence=mention.confidence,
                    source=mention.source,
                    metadata=metadata,
                )
            )

        return final_entities
