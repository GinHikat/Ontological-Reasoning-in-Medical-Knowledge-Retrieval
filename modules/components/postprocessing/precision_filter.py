from __future__ import annotations

import re

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.core.constants import (
    TARGET_LABEL_DIAGNOSIS,
    TARGET_LABEL_DRUG,
    TARGET_LABEL_SYMPTOM,
    TARGET_LABEL_TEST_NAME,
)
from modules.core.schemas import Document, EntityMention


class ClinicalPrecisionFilterPostProcessor(BaseMentionPostProcessor):
    """Drop high-frequency extraction artifacts before linking/formatting."""

    DROP_EXACT_TERMS = {
        "nhẹ",
        "nặng",
        "vừa",
        "tăng",
        "giảm",
        "cao",
        "thấp",
        "thư",
        "bệnh nội khoa",
        "bệnh lý bất thường",
        "viện",
        "nhập viện",
        "triệu chứng hiện tại",
        "các triệu chứng hiện tại",
        "xét nghiệm",
        "phân tích",
    }

    DRUG_DOSING_ONLY_TERMS = {
        "po",
        "bid",
        "tid",
        "qid",
        "prn",
        "iv",
        "im",
        "sc",
        "uống",
        "ngày",
        "lần",
    }

    DRUG_DOSING_ONLY_PATTERN = re.compile(
        r"^(?:\d+(?:[.,]\d+)?\s*)?(?:mg|g|mcg|ml|viên|ống|lọ|gói|iu|ui|đơn\s+vị|"
        r"x\s*\d+|po|bid|tid|qid|prn|iv|im|sc|ngày|lần|giờ|phút)$",
        flags=re.IGNORECASE,
    )

    TEST_ABBREVIATIONS = {
        "ct",
        "mri",
        "ecg",
        "ekg",
        "cea",
        "wbc",
        "rbc",
        "hgb",
        "plt",
        "ast",
        "alt",
        "bun",
        "crp",
    }
    SHORT_ALLOWED_SYMPTOMS = {"ho"}

    def __init__(self, min_non_abbreviation_length: int = 3):
        self.min_non_abbreviation_length = min_non_abbreviation_length

    @staticmethod
    def _normalized(text: str) -> str:
        return " ".join(text.lower().strip(" \t\r\n.,;:-()[]{}").split())

    def _is_too_short(self, mention: EntityMention, normalized: str) -> bool:
        if normalized in self.TEST_ABBREVIATIONS:
            return False
        if (
            mention.label == TARGET_LABEL_SYMPTOM
            and normalized in self.SHORT_ALLOWED_SYMPTOMS
        ):
            return False
        if (
            mention.label == TARGET_LABEL_TEST_NAME
            and normalized in self.TEST_ABBREVIATIONS
        ):
            return False
        return len(normalized) < self.min_non_abbreviation_length

    def _is_dosing_only_drug(self, mention: EntityMention, normalized: str) -> bool:
        if mention.label != TARGET_LABEL_DRUG:
            return False
        return normalized in self.DRUG_DOSING_ONLY_TERMS or bool(
            self.DRUG_DOSING_ONLY_PATTERN.fullmatch(normalized)
        )

    def _is_generic_artifact(self, mention: EntityMention, normalized: str) -> bool:
        if normalized in self.DROP_EXACT_TERMS:
            return True
        if mention.label in {TARGET_LABEL_SYMPTOM, TARGET_LABEL_DIAGNOSIS}:
            if normalized.startswith("cảm thấy ") and len(normalized.split()) <= 2:
                return True
            if normalized in {"cảm giác", "khó chịu", "bất thường"}:
                return True
        if (
            mention.metadata.get("is_disease_like")
            and normalized in self.DROP_EXACT_TERMS
        ):
            return True
        return False

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        filtered: list[EntityMention] = []
        for mention in mentions:
            normalized = self._normalized(mention.text)
            if not normalized:
                continue
            if self._is_too_short(mention, normalized):
                continue
            if self._is_dosing_only_drug(mention, normalized):
                continue
            if self._is_generic_artifact(mention, normalized):
                continue
            filtered.append(mention)
        return filtered
