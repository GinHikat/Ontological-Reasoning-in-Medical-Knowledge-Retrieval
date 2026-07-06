from __future__ import annotations

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from modules.core.schemas import Document, FinalEntity
from modules.pipelines.base import BasePipeline


class LegacyV5PipelineAdapter(BasePipeline):
    """
    Per-document adapter around the frozen V5 helper functions.

    This keeps old logic available through the same BasePipeline interface used by
    refactored and future pipelines. The original scripts remain unchanged under
    modules/legacy for rollback/regression comparison.
    """

    def __init__(self):
        from modules.legacy import test_sample_pipeline_legacy as legacy

        self.legacy = legacy
        (
            self.df_diag,
            self.diag_embs,
            self.df_drug,
            self.drug_embs,
            self.df_sym,
            self.sym_embs,
        ) = legacy.load_dictionaries()
        self.extractor = legacy.EntityExtractor(mode="ner + retrieval")
        self.ner_model = self.extractor._get_ner_instance(lang="vi")
        self.sapbert_vi = self.extractor._get_sapbert_instance(lang="vi")
        self.sapbert_en = self.extractor._get_sapbert_instance(lang="en")

    def process_document(self, document: Document) -> list[FinalEntity]:
        text = document.text
        boundaries = self.legacy.get_section_boundaries(text)
        ner_results = self.ner_model.extract_entities(text)

        label_map = {
            "Drug": "THUỐC",
            "Medication": "THUỐC",
            "Chemical": "THUỐC",
            "Procedure": "TÊN_XÉT_NGHIỆM",
            "Test": "TÊN_XÉT_NGHIỆM",
        }

        final_entities: list[FinalEntity] = []

        for ent in ner_results:
            raw_label = ent.get("label", "")
            mapped_type = label_map.get(raw_label)
            is_disease = raw_label in ["Disease", "Disease/Symptom", "Condition"]

            if not mapped_type and not is_disease:
                continue

            term = ent.get("term", "")
            offset = ent.get("offset", [0, 0])
            start, end = offset
            if start is None or end is None:
                continue

            import string

            seps = set(string.whitespace + string.punctuation)
            while start > 0 and text[start - 1] not in seps:
                start -= 1
            while end < len(text) and text[end] not in seps:
                end += 1

            offset = [start, end]
            term = text[start:end]

            term_lower = term.lower()
            if any(
                keyword in term_lower for keyword in ["phân tích", "xét nghiệm"]
            ) or term_lower in ["ct", "mri"]:
                mapped_type = "TÊN_XÉT_NGHIỆM"
                is_disease = False

            display_term = term
            if mapped_type == "THUỐC":
                exp_start, exp_end = self.legacy.expand_drug_boundary(text, start, end)
                offset = [exp_start, exp_end]
                display_term = text[exp_start:exp_end]

            assertions = self.legacy.check_assertions(text, start, end, boundaries)
            candidates: list[str] = []

            if is_disease:
                emb = self.sapbert_vi.encode_text([term.lower()], show_progress=False)
                best_diag_sim = -1
                best_diag_id = None
                best_sym_sim = -1

                if emb.size > 0:
                    if not self.df_diag.empty and self.diag_embs.size > 0:
                        sims = cosine_similarity(emb, self.diag_embs)[0]
                        top_3_idx = np.argsort(sims)[-3:][::-1]
                        best_hybrid_score = -1

                        for idx in top_3_idx:
                            sem_sim = sims[idx]
                            if sem_sim < 0.5:
                                continue
                            lex_sim = self.legacy.get_best_row_lexical_sim(
                                term, self.df_diag.iloc[idx]
                            )
                            hybrid_score = sem_sim + lex_sim * 0.5

                            if hybrid_score > best_hybrid_score:
                                best_hybrid_score = hybrid_score
                                best_diag_sim = sem_sim
                                best_diag_id = str(self.df_diag.iloc[idx]["id"])

                    if not self.df_sym.empty and self.sym_embs.size > 0:
                        sims = cosine_similarity(emb, self.sym_embs)[0]
                        best_idx = np.argmax(sims)
                        best_sym_sim = sims[best_idx]

                if (
                    best_diag_sim >= best_sym_sim
                    and best_diag_id is not None
                    and best_diag_sim >= 0.6
                ):
                    mapped_type = "CHẨN_ĐOÁN"
                    candidates = [best_diag_id]
                else:
                    mapped_type = "TRIỆU_CHỨNG"
                    candidates = []

            elif (
                mapped_type == "THUỐC"
                and not self.df_drug.empty
                and self.drug_embs.size > 0
            ):
                emb = self.sapbert_en.encode_text(
                    [display_term.lower()], show_progress=False
                )
                if emb.size > 0:
                    sims = cosine_similarity(emb, self.drug_embs)[0]
                    top_3_idx = np.argsort(sims)[-3:][::-1]
                    best_hybrid_score = -1
                    best_id = None
                    best_sem_sim = -1

                    for idx in top_3_idx:
                        sem_sim = sims[idx]
                        if sem_sim < 0.5:
                            continue
                        lex_sim = self.legacy.get_best_row_lexical_sim(
                            display_term, self.df_drug.iloc[idx]
                        )
                        hybrid_score = sem_sim + lex_sim * 0.5

                        if hybrid_score > best_hybrid_score:
                            best_hybrid_score = hybrid_score
                            best_sem_sim = sem_sim
                            best_id = str(self.df_drug.iloc[idx]["rxcui"])

                    if best_id and best_sem_sim >= 0.6:
                        candidates = [best_id]

            entity_output = {
                "text": display_term,
                "type": mapped_type,
                "assertions": assertions,
                "position": offset,
            }
            if mapped_type in ["CHẨN_ĐOÁN", "THUỐC"]:
                entity_output["candidates"] = candidates

            final_entities.append(
                FinalEntity.from_legacy(entity_output, source="legacy_v5")
            )

        return final_entities
