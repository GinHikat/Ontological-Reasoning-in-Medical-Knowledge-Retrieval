from __future__ import annotations

import re

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.core.constants import (
    TARGET_LABEL_DRUG,
    TARGET_LABEL_SYMPTOM,
    TARGET_LABEL_TEST_NAME,
)
from modules.core.schemas import Document, EntityMention, Span


class ClinicalTypeCorrectionPostProcessor(BaseMentionPostProcessor):
    """Correct systematic NER type errors before linking.

    The base model sometimes labels drug fragments as procedures and common
    symptom phrases as disease-like mentions. These corrections intentionally use
    only high-confidence lexical/contextual rules.
    """

    COMMON_SYMPTOM_PATTERN = re.compile(
        r"(?<!\w)(?:"
        r"đánh\s+trống\s+ngực|khó\s+thở|buồn\s+nôn|đổ\s+mồ\s+hôi|"
        r"đau\s+(?:ngực|đầu|bụng|lưng)|tiêu\s+chảy|đi\s+ngoài\s+ra\s+máu|"
        r"mệt\s+mỏi|chóng\s+mặt|sốt|ho|nôn|đờm"
        r")(?!\w)",
        flags=re.IGNORECASE,
    )

    DRUG_DOSAGE_AFTER_PATTERN = re.compile(
        r"^\s*(?:\d+(?:[.,]\d+)?\s*)?(?:mg|g|mcg|ml|viên|ống|lọ|gói|iu|ui|đơn\s+vị)\b",
        flags=re.IGNORECASE,
    )

    DRUG_CONTEXT_BEFORE_PATTERN = re.compile(
        r"(?:thuốc|dùng|uống|sử\s+dụng|điều\s+trị)\s*$",
        flags=re.IGNORECASE,
    )

    def __init__(self, context_window: int = 40):
        self.context_window = context_window

    @staticmethod
    def _copy_with(
        mention: EntityMention,
        label: str,
        text: str | None = None,
        span: Span | None = None,
    ) -> EntityMention:
        metadata = dict(mention.metadata)
        metadata["type_corrected_from"] = mention.label
        if label == TARGET_LABEL_SYMPTOM:
            metadata["is_disease_like"] = False
        return EntityMention(
            text=mention.text if text is None else text,
            label=label,
            span=mention.span if span is None else span,
            confidence=mention.confidence,
            source=mention.source,
            metadata=metadata,
        )

    def _has_drug_context(self, document: Document, mention: EntityMention) -> bool:
        start_raw = mention.span.start
        end_raw = mention.span.end
        if start_raw is None or end_raw is None or start_raw > end_raw:
            return False
        start = int(start_raw)
        end = int(end_raw)
        before = document.text[max(0, start - self.context_window) : start]
        after = document.text[end : min(len(document.text), end + self.context_window)]
        return bool(self.DRUG_DOSAGE_AFTER_PATTERN.search(after)) or bool(
            self.DRUG_CONTEXT_BEFORE_PATTERN.search(before)
        )

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        corrected: list[EntityMention] = []
        for mention in mentions:
            normalized = " ".join(mention.text.lower().split())

            if mention.metadata.get(
                "is_disease_like"
            ) and self.COMMON_SYMPTOM_PATTERN.search(normalized):
                corrected.append(self._copy_with(mention, TARGET_LABEL_SYMPTOM))
                continue

            if mention.label == TARGET_LABEL_TEST_NAME and self._has_drug_context(
                document, mention
            ):
                corrected.append(self._copy_with(mention, TARGET_LABEL_DRUG))
                continue

            corrected.append(mention)
        return corrected
