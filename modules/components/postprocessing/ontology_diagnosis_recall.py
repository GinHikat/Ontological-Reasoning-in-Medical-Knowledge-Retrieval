from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.components.postprocessing.ontology_drug_recall import (
    compact_with_map,
    normalize_with_map,
)
from modules.components.structure.section_parser import VietnameseClinicalSectionParser
from modules.core.config import ProjectPaths
from modules.core.constants import TARGET_LABEL_DIAGNOSIS, TARGET_LABEL_SYMPTOM
from modules.core.schemas import Document, EntityMention, Span


@dataclass(frozen=True)
class _DiagAlias:
    alias: str
    norm: str
    concept_id: str


class OntologyDiagnosisRecallPostProcessor(BaseMentionPostProcessor):
    """Conservative exact/near-exact diagnosis lexical recall against ICD dictionary."""

    PRIORITY_SECTIONS = {
        "Bệnh lý mãn tính",
        "Chẩn đoán",
        "Lý do nhập viện",
        "Kết quả chẩn đoán hình ảnh",
        "Tiền sử bệnh",
    }
    GENERIC_TERMS = {
        "bệnh",
        "hội chứng",
        "rối loạn",
        "nhiễm trùng",
        "viêm",
        "ung thư",
        "u",
        "suy",
        "tăng",
        "giảm",
        "đau",
        "sốt",
        "ho",
        "other",
        "unspecified",
        "disease",
        "disorder",
        "syndrome",
        "căng thẳng",
        "stress",
        "mệt mỏi",
        "đau đầu",
        "đau ngực",
        "đau bụng",
        "buồn nôn",
        "khó thở",
        "chóng mặt",
        "đánh trống ngực",
        "tiêu chảy",
        "táo bón",
        "ho ra máu",
        "phù",
        "ngứa",
        "ban",
        "sưng",
    }
    SHORT_WHITELIST: set[str] = set()
    SYMPTOM_LIKE = re.compile(
        r"^(?:đau|sốt|ho|nôn|buồn|khó|mệt|chóng|đánh|tiêu|táo|ngứa|phù|sưng)\b",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        dictionary_path: Path | None = None,
        section_parser: VietnameseClinicalSectionParser | None = None,
        min_alias_len: int = 5,
    ):
        self.dictionary_path = dictionary_path or (
            ProjectPaths().viettel_base_dir / "short_diagnosis.csv"
        )
        self.section_parser = section_parser or VietnameseClinicalSectionParser()
        self.min_alias_len = min_alias_len
        self._loaded = False
        self._by_norm: dict[str, list[_DiagAlias]] = defaultdict(list)

    def _safe(self, term: str) -> bool:
        t = term.strip()
        if not t:
            return False
        low = unicodedata.normalize("NFKC", t).lower().strip()
        if low in self.GENERIC_TERMS:
            return False
        if self.SYMPTOM_LIKE.match(low):
            return False
        letters = re.sub(r"[^A-Za-zÀ-ỹ]", "", t)
        if len(letters) < self.min_alias_len and low not in self.SHORT_WHITELIST:
            return False
        if len(t) > 80:
            return False
        # Prefer multi-token clinical phrases
        if len(low.split()) < 2 and len(letters) < 10:
            return False
        return True

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        path = self.dictionary_path
        if not path.exists():
            self._loaded = True
            return
        df = pd.read_csv(path)
        for row in df.itertuples(index=False):
            concept_id = str(getattr(row, "id", "") or "")
            if not concept_id or concept_id == "nan":
                continue
            for col in ("name_vi", "name_en"):
                term = str(getattr(row, col, "") or "").strip()
                if not term or term == "nan" or not self._safe(term):
                    continue
                norm, _ = normalize_with_map(term)
                if len(norm.replace(" ", "")) < self.min_alias_len:
                    continue
                self._by_norm[norm].append(
                    _DiagAlias(alias=term, norm=norm, concept_id=concept_id)
                )
        self._loaded = True

    def _in_priority_section(self, start: int, sections) -> bool:
        for section in sections:
            if section.name in self.PRIORITY_SECTIONS and section.start <= start < section.end:
                return True
        return False

    def _has_strong_symptom(self, mentions: list[EntityMention], start: int, end: int) -> bool:
        for m in mentions:
            if m.label != TARGET_LABEL_SYMPTOM:
                continue
            if m.source == "section_recall" and m.span.start == start and m.span.end == end:
                return True
            ms, me = m.span.start, m.span.end
            if ms is None or me is None:
                continue
            if start == int(ms) and end == int(me) and m.source == "section_recall":
                return True
        return False

    def _span_from_map(
        self, index_map: list[int], match_start: int, match_end: int
    ) -> tuple[int, int] | None:
        if match_start < 0 or match_end > len(index_map) or match_start >= match_end:
            return None
        idxs = index_map[match_start:match_end]
        if not idxs:
            return None
        return idxs[0], idxs[-1] + 1

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        self._ensure_loaded()
        if "clinical_sections" not in document.metadata:
            document.metadata["clinical_sections"] = self.section_parser.parse(
                document.text
            )
        sections = document.metadata["clinical_sections"]
        recalled = list(mentions)
        text = document.text
        norm, index_map = normalize_with_map(text)
        occupied = [False] * len(norm)

        aliases = sorted(self._by_norm.keys(), key=len, reverse=True)
        for alias_norm in aliases:
            start = 0
            while True:
                idx = norm.find(alias_norm, start)
                if idx < 0:
                    break
                end = idx + len(alias_norm)
                start = idx + 1
                if idx > 0 and norm[idx - 1].isalnum():
                    continue
                if end < len(norm) and norm[end].isalnum():
                    continue
                if any(occupied[idx:end]):
                    continue
                span = self._span_from_map(index_map, idx, end)
                if span is None:
                    continue
                s, e = span
                # Prefer priority sections; allow exact matches elsewhere at lower conf
                in_priority = self._in_priority_section(s, sections)
                if not in_priority:
                    # Outside priority sections: only long multi-word aliases
                    if len(alias_norm.split()) < 3 or len(alias_norm) < 18:
                        continue
                if self._has_strong_symptom(recalled, s, e):
                    continue
                # Skip if exact span already a diagnosis
                skip = False
                for m in recalled:
                    if m.span.start == s and m.span.end == e and m.label == TARGET_LABEL_DIAGNOSIS:
                        skip = True
                        break
                if skip:
                    for i in range(idx, end):
                        occupied[i] = True
                    continue

                entry = self._by_norm[alias_norm][0]
                for i in range(idx, end):
                    occupied[i] = True
                recalled.append(
                    EntityMention(
                        text=text[s:e],
                        label=TARGET_LABEL_DIAGNOSIS,
                        span=Span(s, e),
                        confidence=0.9 if in_priority else 0.78,
                        source="ontology_diagnosis_recall",
                        metadata={
                            "ontology_diagnosis_recall": True,
                            "alias": entry.alias,
                            "concept_id": entry.concept_id,
                            "section_priority": in_priority,
                        },
                    )
                )

        return sorted(
            recalled,
            key=lambda m: (
                m.span.start if m.span.start is not None else 10**9,
                m.span.end if m.span.end is not None else 10**9,
            ),
        )
