from __future__ import annotations

import re

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.components.structure.section_parser import VietnameseClinicalSectionParser
from modules.core.constants import TARGET_LABEL_TEST_NAME, TARGET_LABEL_TEST_RESULT
from modules.core.schemas import Document, EntityMention, Span


class LabPairRecallPostProcessor(BaseMentionPostProcessor):
    """Extract lab name / result pairs from explicit lab syntax and sections."""

    VITAL_SIGNS = {
        "huyết áp",
        "mạch",
        "nhiệt độ",
        "nhịp thở",
        "spo2",
        "spO2".lower(),
    }

    QUALITATIVE = (
        r"âm\s+tính|dương\s+tính|bình\s+thường|bất\s+thường|tăng|giảm|cao|thấp"
    )
    UNIT = (
        r"(?:mmol\/l|mg\/dl|g\/l|g\/dl|u\/l|iu\/l|%|g\/l|mmhg|mmhg|"
        r"lần\/phút|bpm|°c|c|fl|pg|ng\/ml|µg\/l|ug\/l|mcg\/l|"
        r"x\s*10\^?\d+\/[lL]|10\^?\d+\/[lL])"
    )
    NUMBER = r"\d+(?:[.,]\d+)?"
    ARROW_RESULT = rf"(?:{NUMBER})\s*(?:-->|->|→|⇒)\s*(?:{NUMBER})(?:\s*{UNIT})?"
    NUMERIC_RESULT = rf"(?:{NUMBER})(?:\s*{UNIT})?"
    RESULT = rf"(?:{ARROW_RESULT}|{NUMERIC_RESULT}|{QUALITATIVE})"

    # name [là|:|=] result — require an explicit connector to avoid prose FPs
    PAIR_PATTERN = re.compile(
        r"(?<!\w)(?P<name>[A-Za-zÀ-ỹ][A-Za-zÀ-ỹ0-9 \-]{0,40}?)"
        r"\s*(?:là|:|=)\s*"
        rf"(?P<result>{RESULT})(?!\w)",
        flags=re.IGNORECASE,
    )

    # Compact forms: INR 1.7 / WBC:14,43 / creatinine 1.2
    COMPACT_PATTERN = re.compile(
        r"(?<!\w)(?P<name>[A-Za-z][A-Za-z0-9\-]{1,20})\s*(?::|=)?\s*"
        rf"(?P<result>{ARROW_RESULT}|{NUMERIC_RESULT})(?!\w)",
        flags=re.IGNORECASE,
    )

    def __init__(self, section_parser: VietnameseClinicalSectionParser | None = None):
        self.section_parser = section_parser or VietnameseClinicalSectionParser()

    @staticmethod
    def _strip(text: str, start: int, end: int) -> tuple[int, int]:
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1] in " \t\r\n.,;:":
            end -= 1
        return start, end

    def _is_vital(self, name: str) -> bool:
        n = re.sub(r"\s+", " ", name.lower().strip())
        return n in self.VITAL_SIGNS or any(n.startswith(v) for v in self.VITAL_SIGNS)

    def _has_overlap(
        self, mentions: list[EntityMention], start: int, end: int, label: str
    ) -> bool:
        for m in mentions:
            if m.label != label:
                continue
            ms, me = m.span.start, m.span.end
            if ms is None or me is None:
                continue
            if start < int(me) and int(ms) < end:
                return True
        return False

    def _add(
        self,
        document: Document,
        mentions: list[EntityMention],
        label: str,
        start: int,
        end: int,
        confidence: float,
    ) -> None:
        start, end = self._strip(document.text, start, end)
        if start >= end:
            return
        if self._has_overlap(mentions, start, end, label):
            return
        mentions.append(
            EntityMention(
                text=document.text[start:end],
                label=label,
                span=Span(start, end),
                confidence=confidence,
                source="lab_pair_recall",
                metadata={"lab_pair_recall": True},
            )
        )

    def _emit_pair(
        self,
        document: Document,
        mentions: list[EntityMention],
        name_s: int,
        name_e: int,
        result_s: int,
        result_e: int,
    ) -> None:
        name = document.text[name_s:name_e].strip()
        if not name or self._is_vital(name):
            return
        # Reject overly long "names" that are clearly prose
        if len(name) > 40 or len(name.split()) > 5:
            return
        if "\n" in name or "\r" in name:
            return
        # Require name to look like a lab token (letters, optional spaces)
        if not re.fullmatch(r"[A-Za-zÀ-ỹ][A-Za-zÀ-ỹ0-9 \-]{0,39}", name):
            return
        self._add(
            document,
            mentions,
            TARGET_LABEL_TEST_NAME,
            name_s,
            name_e,
            confidence=0.9,
        )
        self._add(
            document,
            mentions,
            TARGET_LABEL_TEST_RESULT,
            result_s,
            result_e,
            confidence=0.9,
        )

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        if "clinical_sections" not in document.metadata:
            document.metadata["clinical_sections"] = self.section_parser.parse(
                document.text
            )

        text = document.text
        recalled = list(mentions)

        for pattern in (self.PAIR_PATTERN, self.COMPACT_PATTERN):
            for match in pattern.finditer(text):
                name_s, name_e = match.start("name"), match.end("name")
                result_s, result_e = match.start("result"), match.end("result")
                # Prefer not consuming trailing sentence text
                name_s, name_e = self._strip(text, name_s, name_e)
                result_s, result_e = self._strip(text, result_s, result_e)
                self._emit_pair(
                    document, recalled, name_s, name_e, result_s, result_e
                )

        return sorted(
            recalled,
            key=lambda m: (
                m.span.start if m.span.start is not None else 10**9,
                m.span.end if m.span.end is not None else 10**9,
            ),
        )
