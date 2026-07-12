"""Local ICD-10 / RxNorm candidate retrieval for the OpenRouter teacher.

Does not invent IDs. Embedding similarity used when matrices are available
and SapBERT encode is optional (lexical+fuzzy always available).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from modules.components.linking.dictionaries import CompetitionDictionaryStore
from modules.components.postprocessing.ontology_drug_recall import normalize_with_map
from modules.core.config import ProjectPaths


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _lex_sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


@dataclass
class OntologyCandidate:
    id: str
    canonical_term: str
    aliases: list[str]
    ontology_type: str
    retrieval_sources: list[str]
    lexical_score: float
    embedding_score: float
    combined_score: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "canonical_term": self.canonical_term,
            "aliases": self.aliases,
            "ontology_type": self.ontology_type,
            "retrieval_sources": self.retrieval_sources,
            "lexical_score": round(self.lexical_score, 6),
            "embedding_score": round(self.embedding_score, 6),
            "combined_score": round(self.combined_score, 6),
        }


class LocalOntologyRetriever:
    def __init__(
        self,
        base_dir: Path | None = None,
        use_embeddings: bool = False,
        top_n: int = 20,
    ) -> None:
        self.base_dir = base_dir or ProjectPaths().viettel_base_dir
        self.use_embeddings = use_embeddings
        self.top_n = top_n
        self._bundle = CompetitionDictionaryStore(self.base_dir).load()
        self._icd_alias_index: dict[str, list[tuple[str, str]]] | None = None
        self._rx_alias_index: dict[str, list[tuple[str, str, str]]] | None = None
        self._embedder_vi = None
        self._embedder_en = None

    def _ensure_icd_index(self) -> dict[str, list[tuple[str, str]]]:
        if self._icd_alias_index is None:
            self._icd_alias_index = self._build_icd_alias_index()
        return self._icd_alias_index

    def _ensure_rx_index(self) -> dict[str, list[tuple[str, str, str]]]:
        if self._rx_alias_index is None:
            self._rx_alias_index = self._build_rx_alias_index()
        return self._rx_alias_index

    def _build_icd_alias_index(self) -> dict[str, list[tuple[str, str]]]:
        idx: dict[str, list[tuple[str, str]]] = {}
        df = self._bundle.diagnoses
        if df.empty:
            return idx
        for _, row in df.iterrows():
            cid = str(row.get("id") or "").strip()
            if not cid:
                continue
            for col in ("name_vi", "name_en"):
                name = str(row.get(col) or "").strip()
                if not name:
                    continue
                norm, _ = normalize_with_map(name)
                if not norm:
                    continue
                idx.setdefault(norm, []).append((cid, name))
        return idx

    def _build_rx_alias_index(self) -> dict[str, list[tuple[str, str, str]]]:
        # id, term, tty
        idx: dict[str, list[tuple[str, str, str]]] = {}
        df = self._bundle.drugs
        if df.empty:
            return idx
        term_col = "term" if "term" in df.columns else "name_en"
        tty_col = "tty" if "tty" in df.columns else None
        id_col = "rxcui" if "rxcui" in df.columns else "id"
        for _, row in df.iterrows():
            cid = str(row.get(id_col) or "").strip()
            if not cid:
                continue
            term = str(row.get(term_col) or "").strip()
            tty = str(row.get(tty_col) or "").strip() if tty_col else ""
            if not term:
                continue
            norm, _ = normalize_with_map(term)
            if not norm:
                continue
            idx.setdefault(norm, []).append((cid, term, tty))
        return idx

    def _maybe_load_embedders(self) -> None:
        if not self.use_embeddings:
            return
        if self._embedder_vi is not None:
            return
        try:
            from modules.model.embedding_models import EmbeddingModels

            self._embedder_vi = EmbeddingModels(
                "cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR"
            )
            self._embedder_en = EmbeddingModels(
                "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"
            )
        except Exception:
            self.use_embeddings = False
            self._embedder_vi = None
            self._embedder_en = None

    def retrieve_icd(self, mention_text: str, top_n: int | None = None) -> list[OntologyCandidate]:
        top_n = top_n or self.top_n
        text = mention_text or ""
        norm, _ = normalize_with_map(text)
        folded = _fold(text)
        by_id: dict[str, OntologyCandidate] = {}

        # exact alias
        idx = self._ensure_icd_index()
        for cid, name in idx.get(norm, []):
            by_id[cid] = OntologyCandidate(
                id=cid,
                canonical_term=name,
                aliases=[name],
                ontology_type="ICD10",
                retrieval_sources=["exact_alias"],
                lexical_score=1.0,
                embedding_score=0.0,
                combined_score=1.0,
            )

        df = self._bundle.diagnoses
        if not df.empty:
            # lexical / fuzzy over names
            scored: list[tuple[float, str, str, str]] = []
            for _, row in df.iterrows():
                cid = str(row.get("id") or "").strip()
                if not cid:
                    continue
                names = [
                    str(row.get("name_vi") or "").strip(),
                    str(row.get("name_en") or "").strip(),
                ]
                best = 0.0
                matched = names[0] or names[1]
                for n in names:
                    if not n:
                        continue
                    nf = _fold(n)
                    if folded and (folded == nf or folded in nf or nf in folded):
                        best = max(best, 0.95 if folded == nf else 0.85)
                        matched = n
                    best = max(best, _lex_sim(folded, nf))
                    if best == _lex_sim(folded, nf):
                        matched = n
                if best >= 0.55:
                    scored.append((best, cid, matched, "fuzzy_lexical"))
            scored.sort(key=lambda x: -x[0])
            for best, cid, matched, src in scored[: max(top_n * 3, 40)]:
                if cid in by_id:
                    if src not in by_id[cid].retrieval_sources:
                        by_id[cid].retrieval_sources.append(src)
                    by_id[cid].lexical_score = max(by_id[cid].lexical_score, best)
                    by_id[cid].combined_score = max(
                        by_id[cid].combined_score, by_id[cid].lexical_score
                    )
                    continue
                by_id[cid] = OntologyCandidate(
                    id=cid,
                    canonical_term=matched,
                    aliases=[matched],
                    ontology_type="ICD10",
                    retrieval_sources=[src],
                    lexical_score=best,
                    embedding_score=0.0,
                    combined_score=best,
                )

        # embedding similarity when available
        emb = self._bundle.diagnosis_embeddings
        if self.use_embeddings and emb is not None and getattr(emb, "size", 0) > 0:
            self._maybe_load_embedders()
            if self._embedder_vi is not None and not df.empty:
                try:
                    from sklearn.metrics.pairwise import cosine_similarity

                    q = self._embedder_vi.encode_text(
                        [text.lower()], show_progress=False
                    )
                    sims = cosine_similarity(q, emb)[0]
                    idxs = np.argsort(sims)[-top_n:][::-1]
                    for i in idxs:
                        sem = float(sims[i])
                        if sem < 0.45:
                            continue
                        cid = str(df.iloc[i].get("id") or "").strip()
                        name = str(df.iloc[i].get("name_vi") or df.iloc[i].get("name_en") or "")
                        if not cid:
                            continue
                        if cid in by_id:
                            if "embedding" not in by_id[cid].retrieval_sources:
                                by_id[cid].retrieval_sources.append("embedding")
                            by_id[cid].embedding_score = max(
                                by_id[cid].embedding_score, sem
                            )
                            by_id[cid].combined_score = max(
                                by_id[cid].combined_score,
                                by_id[cid].lexical_score + 0.5 * by_id[cid].embedding_score,
                            )
                        else:
                            by_id[cid] = OntologyCandidate(
                                id=cid,
                                canonical_term=name,
                                aliases=[name],
                                ontology_type="ICD10",
                                retrieval_sources=["embedding"],
                                lexical_score=0.0,
                                embedding_score=sem,
                                combined_score=0.5 * sem,
                            )
                except Exception:
                    pass

        ranked = sorted(by_id.values(), key=lambda c: -c.combined_score)
        return ranked[:top_n]

    def retrieve_rxnorm(
        self, mention_text: str, top_n: int | None = None
    ) -> list[OntologyCandidate]:
        top_n = top_n or self.top_n
        text = mention_text or ""
        norm, _ = normalize_with_map(text)
        folded = _fold(text)
        by_id: dict[str, OntologyCandidate] = {}

        idx = self._ensure_rx_index()
        for cid, term, tty in idx.get(norm, []):
            by_id[cid] = OntologyCandidate(
                id=cid,
                canonical_term=term,
                aliases=[term],
                ontology_type=f"RxNorm:{tty}" if tty else "RxNorm",
                retrieval_sources=["exact_alias"],
                lexical_score=1.0,
                embedding_score=0.0,
                combined_score=1.0,
            )

        # ingredient-ish token exacts (not ingredient-first hedge — only expand retrieval)
        tokens = [t for t in re.split(r"[^A-Za-zÀ-ỹ0-9]+", text) if len(t) >= 3]
        for tok in tokens:
            tn, _ = normalize_with_map(tok)
            for cid, term, tty in idx.get(tn, []):
                if cid in by_id:
                    if "ingredient_token" not in by_id[cid].retrieval_sources:
                        by_id[cid].retrieval_sources.append("ingredient_token")
                    continue
                by_id[cid] = OntologyCandidate(
                    id=cid,
                    canonical_term=term,
                    aliases=[term],
                    ontology_type=f"RxNorm:{tty}" if tty else "RxNorm",
                    retrieval_sources=["ingredient_token"],
                    lexical_score=0.8,
                    embedding_score=0.0,
                    combined_score=0.8,
                )

        df = self._bundle.drugs
        term_col = "term" if not df.empty and "term" in df.columns else "name_en"
        id_col = "rxcui" if not df.empty and "rxcui" in df.columns else "id"
        tty_col = "tty" if not df.empty and "tty" in df.columns else None

        # Bounded fuzzy: only aliases sharing a long token prefix (avoid 310k full scan)
        if folded and len(folded) >= 3:
            prefix = folded[: min(6, len(folded))]
            scored: list[tuple[float, str, str, str]] = []
            for alias_norm, entries in idx.items():
                if prefix not in alias_norm and alias_norm[: len(prefix)] != prefix:
                    continue
                best = _lex_sim(folded, alias_norm)
                if folded in alias_norm or alias_norm in folded:
                    best = max(best, 0.88)
                if best < 0.6:
                    continue
                for cid, term, tty in entries[:3]:
                    scored.append((best, cid, term, tty))
            scored.sort(key=lambda x: -x[0])
            for best, cid, term, tty in scored[: max(top_n * 4, 60)]:
                if cid in by_id:
                    by_id[cid].lexical_score = max(by_id[cid].lexical_score, best)
                    by_id[cid].combined_score = max(
                        by_id[cid].combined_score, by_id[cid].lexical_score
                    )
                    if "fuzzy_lexical" not in by_id[cid].retrieval_sources:
                        by_id[cid].retrieval_sources.append("fuzzy_lexical")
                    continue
                by_id[cid] = OntologyCandidate(
                    id=cid,
                    canonical_term=term,
                    aliases=[term],
                    ontology_type=f"RxNorm:{tty}" if tty else "RxNorm",
                    retrieval_sources=["fuzzy_lexical"],
                    lexical_score=best,
                    embedding_score=0.0,
                    combined_score=best,
                )

        emb = self._bundle.drug_embeddings
        if self.use_embeddings and emb is not None and getattr(emb, "size", 0) > 0:
            self._maybe_load_embedders()
            if self._embedder_en is not None and not df.empty:
                try:
                    from sklearn.metrics.pairwise import cosine_similarity

                    q = self._embedder_en.encode_text(
                        [text.lower()], show_progress=False
                    )
                    sims = cosine_similarity(q, emb)[0]
                    idxs = np.argsort(sims)[-top_n:][::-1]
                    for i in idxs:
                        sem = float(sims[i])
                        if sem < 0.45:
                            continue
                        cid = str(df.iloc[i].get(id_col) or "").strip()
                        term = str(df.iloc[i].get(term_col) or "")
                        tty = str(df.iloc[i].get(tty_col) or "") if tty_col else ""
                        if not cid:
                            continue
                        if cid in by_id:
                            if "embedding" not in by_id[cid].retrieval_sources:
                                by_id[cid].retrieval_sources.append("embedding")
                            by_id[cid].embedding_score = max(
                                by_id[cid].embedding_score, sem
                            )
                            by_id[cid].combined_score = max(
                                by_id[cid].combined_score,
                                by_id[cid].lexical_score
                                + 0.5 * by_id[cid].embedding_score,
                            )
                        else:
                            by_id[cid] = OntologyCandidate(
                                id=cid,
                                canonical_term=term,
                                aliases=[term],
                                ontology_type=f"RxNorm:{tty}" if tty else "RxNorm",
                                retrieval_sources=["embedding"],
                                lexical_score=0.0,
                                embedding_score=sem,
                                combined_score=0.5 * sem,
                            )
                except Exception:
                    pass

        ranked = sorted(by_id.values(), key=lambda c: -c.combined_score)
        return ranked[:top_n]


@lru_cache(maxsize=1)
def get_default_retriever(use_embeddings: bool = False) -> LocalOntologyRetriever:
    return LocalOntologyRetriever(use_embeddings=use_embeddings)
