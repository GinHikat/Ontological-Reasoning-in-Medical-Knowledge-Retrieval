from __future__ import annotations

import re

from modules.components.assertions.base import BaseAssertionDetector
from modules.core.constants import ASSERTION_ELIGIBLE_LABELS
from modules.core.schemas import Document, FinalEntity


class RuleBasedAssertionDetector(BaseAssertionDetector):
    """V5-style historical section and negation detection."""

    def __init__(self, restrict_to_eligible_labels: bool = False):
        self.restrict_to_eligible_labels = restrict_to_eligible_labels

    @staticmethod
    def get_section_boundaries(text: str) -> dict[str, int]:
        s1_match = re.search(r"1\.\s+(Tiền sử bệnh|Tiền sử)", text)
        s2_match = re.search(r"2\.\s+(Tiền sử bệnh hiện tại|Bệnh sử hiện tại)", text)
        s3_match = re.search(r"3\.\s+Đánh giá tại bệnh viện", text)
        return {
            "s1": s1_match.start() if s1_match else -1,
            "s2": s2_match.start() if s2_match else len(text),
            "s3": s3_match.start() if s3_match else len(text),
        }

    @staticmethod
    def check_assertions(
        text: str, start: int, end: int, boundaries: dict[str, int]
    ) -> list[str]:
        assertions: list[str] = []

        if boundaries["s1"] != -1 and boundaries["s1"] <= start < boundaries["s2"]:
            assertions.append("isHistorical")

        line_start = text.rfind("\n", 0, start)
        line_start = 0 if line_start == -1 else line_start + 1
        line_end = text.find("\n", end)
        line_end = len(text) if line_end == -1 else line_end

        line_text = text[line_start:line_end].strip().lower()

        if line_text.startswith("- không") or line_text.startswith("không "):
            assertions.append("isNegated")
            return assertions

        clause_start = start
        while clause_start > line_start and text[clause_start - 1] not in ".;\n":
            clause_start -= 1

        preceding_text = text[clause_start:start].lower()

        last_neg_idx = -1
        for keyword in ["không ", "chưa ", "phủ nhận "]:
            idx = preceding_text.rfind(keyword)
            if idx > last_neg_idx:
                last_neg_idx = idx

        if last_neg_idx != -1:
            text_between = preceding_text[last_neg_idx:]
            text_between = text_between.replace("không có", "")
            text_between = text_between.replace("không ghi nhận", "")
            text_between = text_between.replace("chưa ghi nhận", "")

            contrast_words = [
                " nhưng ",
                " tuy nhiên ",
                ", có ",
                " lại có ",
                " kèm ",
                " và có ",
            ]
            if not any(word in text_between for word in contrast_words):
                assertions.append("isNegated")

        return assertions

    def apply(
        self, document: Document, entities: list[FinalEntity]
    ) -> list[FinalEntity]:
        boundaries = self.get_section_boundaries(document.text)
        updated: list[FinalEntity] = []

        for entity in entities:
            if (
                self.restrict_to_eligible_labels
                and entity.type not in ASSERTION_ELIGIBLE_LABELS
            ):
                updated.append(entity)
                continue
            start = entity.span.start
            end = entity.span.end
            if start is None or end is None or start > end:
                updated.append(entity)
                continue

            assertions = self.check_assertions(
                document.text,
                int(start),
                int(end),
                boundaries,
            )
            updated.append(
                FinalEntity(
                    text=entity.text,
                    type=entity.type,
                    span=entity.span,
                    candidates=list(entity.candidates),
                    assertions=assertions,
                    confidence=entity.confidence,
                    source=entity.source,
                    metadata=dict(entity.metadata),
                )
            )

        return updated
