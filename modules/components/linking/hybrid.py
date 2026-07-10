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
from modules.core.ids import normalize_rxcui
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

    PRESET_DRUG_LINK_MODES = ("disabled", "override_unambiguous", "rescue_unlinked")

    def __init__(
        self,
        dictionary_store: CompetitionDictionaryStore | None = None,
        diagnosis_threshold: float = 0.6,
        drug_threshold: float = 0.6,
        candidate_semantic_floor: float = 0.5,
        lexical_weight: float = 0.5,
        top_k: int = 3,
        use_unambiguous_preset_drug_rxcui: bool = False,
        preset_drug_link_mode: str | None = None,
    ):
        self.dictionary_store = dictionary_store or CompetitionDictionaryStore()
        self.diagnosis_threshold = diagnosis_threshold
        self.drug_threshold = drug_threshold
        self.candidate_semantic_floor = candidate_semantic_floor
        self.lexical_weight = lexical_weight
        self.top_k = top_k
        # Public strategy for ontology preset drug linking.
        # Default "disabled" preserves exact v7 SapBERT drug linking.
        # Legacy Boolean use_unambiguous_preset_drug_rxcui maps to override_unambiguous
        # when preset_drug_link_mode is not explicitly provided.
        if preset_drug_link_mode is None:
            mode = (
                "override_unambiguous"
                if use_unambiguous_preset_drug_rxcui
                else "disabled"
            )
        else:
            mode = str(preset_drug_link_mode)
        if mode not in self.PRESET_DRUG_LINK_MODES:
            raise ValueError(
                f"Unknown preset_drug_link_mode={mode!r}. "
                f"Allowed: {self.PRESET_DRUG_LINK_MODES}"
            )
        self.preset_drug_link_mode = mode
        # Backwards-compatible Boolean: True only for the old override experiment.
        self.use_unambiguous_preset_drug_rxcui = mode == "override_unambiguous"
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

    def _valid_unique_rxcuis_from(self, raw: object) -> list[str]:
        """Return sorted unique valid RxCUIs from a raw candidate list."""
        if raw is None:
            return []
        if not isinstance(raw, (list, tuple, set)):
            return []
        unique: set[str] = set()
        for item in raw:
            normalized = normalize_rxcui(item)
            if normalized is not None:
                unique.add(normalized)
        return sorted(unique)

    def _valid_unique_preset_rxcuis(self, mention: EntityMention) -> list[str]:
        """Return sorted unique valid RxCUIs from ontology-recall preset metadata."""
        return self._valid_unique_rxcuis_from(
            mention.metadata.get("preset_rxcui_candidates")
        )

    def _direct_unambiguous_preset(
        self, mention: EntityMention, metadata: dict
    ) -> tuple[list[str] | None, str]:
        """Validate direct ontology-recall preset evidence (no SapBERT)."""
        if mention.metadata.get("ontology_drug_recall") is not True:
            return None, "not_ontology_recall"

        match_type = mention.metadata.get("match")
        if match_type not in {"exact_norm", "embedded_compact"}:
            return None, "not_ontology_recall"

        if "preset_rxcui_candidates" not in mention.metadata:
            return None, "missing_preset"

        valid = self._valid_unique_preset_rxcuis(mention)
        if len(valid) == 0:
            return None, "invalid_preset"
        if len(valid) > 1:
            metadata["preset_rxcui_candidates"] = valid
            metadata["preset_rxcui_count"] = len(valid)
            return None, "ambiguous_alias"

        unique = valid[0]
        metadata["preset_rxcui"] = unique
        metadata["preset_rxcui_count"] = 1
        metadata["preset_rxcui_candidates"] = [unique]
        return [unique], "direct_preset"

    def _transferred_unambiguous_preset(
        self, mention: EntityMention, metadata: dict
    ) -> tuple[list[str] | None, str]:
        """Validate safely transferred ontology evidence from a contained donor."""
        if mention.metadata.get("ontology_drug_evidence_conflict") is True:
            return None, "conflicting_donors"
        if mention.metadata.get("ontology_drug_evidence_transferred") is not True:
            return None, "no_transferred_evidence"

        valid = self._valid_unique_rxcuis_from(
            mention.metadata.get("transferred_preset_rxcui_candidates")
        )
        if len(valid) == 0:
            return None, "invalid_transferred_preset"
        if len(valid) > 1:
            return None, "ambiguous_transferred_preset"

        unique = valid[0]
        metadata["preset_rxcui"] = unique
        metadata["transferred_preset_rxcui_count"] = 1
        metadata["transferred_preset_rxcui_candidates"] = [unique]
        return [unique], "transferred_preset"

    def _try_preset_drug_link(
        self, mention: EntityMention, metadata: dict
    ) -> tuple[list[str] | None, str]:
        """Old v8 override path: unambiguous preset may replace SapBERT entirely.

        Returns (candidates_or_None, fallback_reason).
        candidates is not None only when the preset path is used.
        """
        if self.preset_drug_link_mode != "override_unambiguous":
            return None, "feature_disabled"

        preset, reason = self._direct_unambiguous_preset(mention, metadata)
        if preset is None:
            return None, reason

        metadata["drug_link"] = "preset_unambiguous_rxcui"
        metadata["preset_used"] = True
        return preset, "preset_used"

    def _sapbert_drug_candidates(
        self, mention: EntityMention, metadata: dict, bundle
    ) -> list[str]:
        """Exact v7 SapBERT drug-linking path."""
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
        candidates: list[str] = []
        if best_drug_id is not None and best_drug_sim >= self.drug_threshold:
            candidates = [best_drug_id]
        metadata["drug_similarity"] = best_drug_sim
        return candidates

    def _rescue_unlinked_drug(
        self, mention: EntityMention, metadata: dict, bundle
    ) -> list[str]:
        """V7 SapBERT first; only rescue empty results with safe ontology evidence."""
        v7_candidates = self._sapbert_drug_candidates(mention, metadata, bundle)
        if len(v7_candidates) > 0:
            metadata["drug_link"] = "v7_candidate_preserved"
            metadata["preset_used"] = False
            return v7_candidates

        # Priority 1: direct unambiguous ontology recall evidence.
        direct, direct_reason = self._direct_unambiguous_preset(mention, metadata)
        if direct is not None:
            metadata["drug_link"] = "preset_rescue"
            metadata["drug_link_rescue_kind"] = "direct_preset_rescue"
            metadata["preset_used"] = True
            return direct

        # Priority 2: safely transferred unambiguous ontology evidence.
        transferred, transferred_reason = self._transferred_unambiguous_preset(
            mention, metadata
        )
        if transferred is not None:
            metadata["drug_link"] = "preset_rescue"
            metadata["drug_link_rescue_kind"] = "transferred_preset_rescue"
            metadata["preset_used"] = True
            return transferred

        metadata["drug_link"] = "unlinked_after_v7_and_rescue"
        metadata["preset_used"] = False
        metadata["drug_link_fallback_reason"] = (
            transferred_reason
            if transferred_reason
            not in {"no_transferred_evidence", "feature_disabled"}
            else direct_reason
        )
        return []

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

            elif mapped_type == TARGET_LABEL_DIAGNOSIS:
                # Already typed as diagnosis (e.g. ontology lexical recall).
                # Prefer an exact dictionary concept_id when provided; else SapBERT.
                preset = mention.metadata.get("concept_id")
                if preset:
                    candidates = [str(preset)]
                    metadata["diagnosis_link"] = "preset_concept_id"
                else:
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
                    if (
                        best_diag_id is not None
                        and best_diag_sim >= self.diagnosis_threshold
                    ):
                        candidates = [best_diag_id]
                    metadata["diagnosis_similarity"] = best_diag_sim

            elif mapped_type == TARGET_LABEL_DRUG:
                if self.preset_drug_link_mode == "rescue_unlinked":
                    candidates = self._rescue_unlinked_drug(
                        mention, metadata, bundle
                    )
                else:
                    preset_candidates, fallback_reason = self._try_preset_drug_link(
                        mention, metadata
                    )
                    if preset_candidates is not None:
                        candidates = preset_candidates
                    else:
                        # Exact current v7 drug-linking behavior (SapBERT).
                        candidates = self._sapbert_drug_candidates(
                            mention, metadata, bundle
                        )
                        # Diagnostic-only fields (stripped from competition JSON).
                        if self.preset_drug_link_mode == "override_unambiguous":
                            metadata["drug_link"] = "sapbert_fallback"
                            metadata["drug_link_fallback_reason"] = fallback_reason
                            metadata["preset_used"] = False

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
