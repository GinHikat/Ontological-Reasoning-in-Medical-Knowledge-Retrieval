from __future__ import annotations

import re

from modules.components.assertions.base import BaseAssertionDetector
from modules.components.structure.section_parser import (
    SectionSpan,
    VietnameseClinicalSectionParser,
)
from modules.core.constants import ASSERTION_ELIGIBLE_LABELS
from modules.core.schemas import Document, FinalEntity


class RuleBasedAssertionDetector(BaseAssertionDetector):
    """Historical section and negation detection, optionally using shared section parser."""

    HISTORICAL_SECTION_NAMES = {
        "Tiền sử bệnh",
        "Tiền sử bệnh nội khoa",
        "Bệnh lý mãn tính",
        "Thuốc trước khi nhập viện",
        "Tiền sử phẫu thuật / thủ thuật",
    }

    FAMILY_OWNERSHIP = re.compile(
        r"(?:tiền\s+sử\s+gia\s+đình|"
        r"(?:bố|mẹ|cha)\s+(?:của\s+)?(?:bệnh\s+nhân\s+)?(?:bị|có|mắc)|"
        r"(?:anh|chị)\s+(?:trai|gái)?\s+(?:của\s+)?(?:bệnh\s+nhân\s+)?(?:bị|có|mắc))",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        restrict_to_eligible_labels: bool = False,
        section_parser: VietnameseClinicalSectionParser | None = None,
        use_section_parser: bool = False,
        detect_family: bool = False,
    ):
        self.restrict_to_eligible_labels = restrict_to_eligible_labels
        self.section_parser = section_parser or VietnameseClinicalSectionParser()
        self.use_section_parser = use_section_parser
        self.detect_family = detect_family

    @staticmethod
    def get_section_boundaries(text: str) -> dict[str, int]:
        """Legacy numbered-section boundaries (kept for v5/v6 compatibility)."""
        s1_match = re.search(r"1\.\s+(Tiền sử bệnh|Tiền sử)", text)
        s2_match = re.search(r"2\.\s+(Tiền sử bệnh hiện tại|Bệnh sử hiện tại)", text)
        s3_match = re.search(r"3\.\s+Đánh giá tại bệnh viện", text)
        return {
            "s1": s1_match.start() if s1_match else -1,
            "s2": s2_match.start() if s2_match else len(text),
            "s3": s3_match.start() if s3_match else len(text),
        }

    def _is_historical_by_sections(
        self, start: int, sections: list[SectionSpan]
    ) -> bool:
        for section in sections:
            if section.name in self.HISTORICAL_SECTION_NAMES and (
                section.start <= start < section.end
            ):
                return True
        return False

    @staticmethod
    def check_negation(text: str, start: int, end: int) -> bool:
        line_start = text.rfind("\n", 0, start)
        line_start = 0 if line_start == -1 else line_start + 1
        line_end = text.find("\n", end)
        line_end = len(text) if line_end == -1 else line_end

        line_text = text[line_start:line_end].strip().lower()

        clause_start = start
        while clause_start > line_start and text[clause_start - 1] not in ".;\n":
            clause_start -= 1

        preceding_text = text[clause_start:start].lower()

        last_neg_idx = -1
        for keyword in ["không ", "chưa ", "phủ nhận "]:
            idx = preceding_text.rfind(keyword)
            if idx > last_neg_idx:
                last_neg_idx = idx

        # Whole-line leading negation (bullet lists)
        if last_neg_idx == -1 and (
            line_text.startswith("- không") or line_text.startswith("không ")
        ):
            rel = text[line_start:start].lower()
            for keyword in ["không ", "chưa ", "phủ nhận "]:
                idx = rel.rfind(keyword)
                if idx > last_neg_idx:
                    last_neg_idx = idx
                    preceding_text = rel

        if last_neg_idx == -1:
            return False

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
        if any(word in text_between for word in contrast_words):
            return False
        return True

    @classmethod
    def check_assertions(
        cls, text: str, start: int, end: int, boundaries: dict[str, int]
    ) -> list[str]:
        """Legacy API used by older call sites / tests."""
        assertions: list[str] = []
        if boundaries["s1"] != -1 and boundaries["s1"] <= start < boundaries["s2"]:
            assertions.append("isHistorical")
        if cls.check_negation(text, start, end):
            assertions.append("isNegated")
        return assertions

    def _check_family(self, text: str, start: int, end: int) -> bool:
        # Do NOT treat "Theo lời người nhà kể" as family ownership
        window_start = max(0, start - 80)
        window = text[window_start:end]
        if re.search(r"theo\s+lời\s+người\s+nhà", window, flags=re.IGNORECASE):
            return False
        return bool(self.FAMILY_OWNERSHIP.search(window))

    def apply(
        self, document: Document, entities: list[FinalEntity]
    ) -> list[FinalEntity]:
        text = document.text
        boundaries = self.get_section_boundaries(text)
        sections: list[SectionSpan] = []
        if self.use_section_parser:
            if "clinical_sections" in document.metadata:
                sections = list(document.metadata["clinical_sections"])
            else:
                sections = self.section_parser.parse(text)
                document.metadata["clinical_sections"] = sections

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

            assertions: list[str] = []
            start_i, end_i = int(start), int(end)

            historical = False
            if self.use_section_parser and sections:
                historical = self._is_historical_by_sections(start_i, sections)
            if not historical:
                if boundaries["s1"] != -1 and boundaries["s1"] <= start_i < boundaries["s2"]:
                    historical = True
            if historical:
                assertions.append("isHistorical")

            if self.check_negation(text, start_i, end_i):
                assertions.append("isNegated")

            if self.detect_family and self._check_family(text, start_i, end_i):
                assertions.append("isFamily")

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
