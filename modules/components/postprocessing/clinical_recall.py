from __future__ import annotations

import re

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.core.constants import (
    TARGET_LABEL_SYMPTOM,
    TARGET_LABEL_TEST_NAME,
    TARGET_LABEL_TEST_RESULT,
)
from modules.core.schemas import Document, EntityMention, Span


class ClinicalRecallPostProcessor(BaseMentionPostProcessor):
    """Rule-based recall for high-value entities missed by the base NER model.

    The base NER model has low recall for short tests (ECG/CEA), common one-word
    symptoms (ho), and lab/result values. This component adds conservative spans
    that are easy to identify from clinical note structure and nearby result cues.
    """

    TEST_NAME_PATTERN = re.compile(
        r"(?<!\w)(?:"
        r"phân\s+tích\s+nước\s+tiểu|"
        r"chụp\s+x[-\s]?quang(?:\s+[^\s,.;:()]+){0,2}|"
        r"x[-\s]?quang(?:\s+[^\s,.;:()]+){0,2}|"
        r"mri(?:\s+[^\s,.;:()]+){0,2}|"
        r"ct(?:\s+[^\s,.;:()]+){0,2}|"
        r"siêu\s+âm(?:\s+[^\s,.;:()]+){0,2}|"
        r"điện\s+tâm\s+đồ|"
        r"monitor\s+holter|"
        r"holter|"
        r"sinh\s+thiết|"
        r"nội\s+soi|"
        r"ecg|ekg|cea(?:\s*\([^)]*\))?|troponin|glucose|creatinine|"
        r"wbc|rbc|hgb|plt|ast|alt|bun|crp"
        r")(?!\w)",
        flags=re.IGNORECASE,
    )

    SYMPTOM_PATTERN = re.compile(
        r"(?<!\w)(?:"
        r"đánh\s+trống\s+ngực|"
        r"khó\s+thở|"
        r"buồn\s+nôn|"
        r"đổ\s+mồ\s+hôi|"
        r"đau\s+ngực|"
        r"đau\s+đầu|"
        r"đau\s+bụng(?:\s+quặn)?|"
        r"tiêu\s+chảy|"
        r"đi\s+ngoài\s+ra\s+máu|"
        r"mệt\s+mỏi|"
        r"chóng\s+mặt|"
        r"sốt|ho|nôn|đờm"
        r")(?!\w)",
        flags=re.IGNORECASE,
    )

    RESULT_CUE_PATTERN = re.compile(
        r"\b(?:"
        r"bình\s+thường|bất\s+thường|âm\s+tính|dương\s+tính|"
        r"tăng|giảm|cao|thấp|"
        r"không\s+(?:có|ghi\s+nhận|chẩn\s+đoán)|"
        r"không\s+có\s+gì\s+đáng\s+chú\s+ý|"
        r"không\s+ghi\s+nhận\s+gì\s+bất\s+thường|"
        r"chiếm\s+ưu\s+thế|thường\s+xuyên|cho\s+thấy"
        r")\b|\d",
        flags=re.IGNORECASE,
    )

    TEST_TRIM_CUE_PATTERN = re.compile(
        r"\b(?:"
        r"không|bình\s+thường|bất\s+thường|âm\s+tính|dương\s+tính|"
        r"tăng|giảm|cao|thấp|thực\s+tế|cho\s+thấy|là|hôm\s+nay|cũng|rất"
        r")\b",
        flags=re.IGNORECASE,
    )

    RESULT_CONNECTOR_PATTERN = re.compile(
        r"^[\s:;,.\-]*(?:(?:là|cho\s+thấy|thực\s+tế|hôm\s+nay|cũng|rất|nhưng)\s+)*",
        flags=re.IGNORECASE,
    )

    SYMPTOM_SECTION_PATTERN = re.compile(
        r"\b(?:các\s+)?triệu\s+chứng(?:\s+hiện\s+tại)?\b|"
        r"đặc\s+điểm\s+triệu\s+chứng",
        flags=re.IGNORECASE,
    )

    RESULT_SECTION_PATTERN = re.compile(
        r"kết\s+quả\s+(?:xét\s+nghiệm|chẩn\s+đoán|khám\s+lâm\s+sàng)|"
        r"các\s+kết\s+quả\s+chẩn\s+đoán",
        flags=re.IGNORECASE,
    )

    SECTION_BREAK_PATTERN = re.compile(
        r"^\s*(?:\d+\.\s+|[A-ZÀ-Ỹ][^\n:]{0,80}:?\s*$)",
        flags=re.IGNORECASE,
    )

    def __init__(self, add_symptoms_from_symptom_sections: bool = True):
        self.add_symptoms_from_symptom_sections = add_symptoms_from_symptom_sections

    @staticmethod
    def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
        return a_start < b_end and b_start < a_end

    @staticmethod
    def _strip_span(text: str, start: int, end: int) -> tuple[int, int]:
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1] in " \t\r\n.,;:-":
            end -= 1
        return start, end

    def _has_overlap(
        self,
        mentions: list[EntityMention],
        label: str,
        start: int,
        end: int,
        any_label: bool = False,
    ) -> bool:
        for mention in mentions:
            if not any_label and mention.label != label:
                continue
            mention_start = mention.span.start
            mention_end = mention.span.end
            if (
                mention_start is None
                or mention_end is None
                or mention_start > mention_end
            ):
                continue
            if self._overlaps(start, end, int(mention_start), int(mention_end)):
                return True
        return False

    def _add_if_new(
        self,
        document: Document,
        mentions: list[EntityMention],
        label: str,
        start: int,
        end: int,
        source: str,
        confidence: float,
        skip_any_overlap: bool = False,
    ) -> None:
        start, end = self._strip_span(document.text, start, end)
        if start >= end:
            return
        if self._has_overlap(mentions, label, start, end, any_label=skip_any_overlap):
            return
        mentions.append(
            EntityMention(
                text=document.text[start:end],
                label=label,
                span=Span(start, end),
                confidence=confidence,
                source=source,
                metadata={"rule_based_recall": True},
            )
        )

    def _trim_test_span(self, text: str, start: int, end: int) -> tuple[int, int]:
        candidate = text[start:end]
        cue_match = self.TEST_TRIM_CUE_PATTERN.search(candidate)
        if cue_match and cue_match.start() > 0:
            end = start + cue_match.start()
        return self._strip_span(text, start, end)

    def _looks_like_result(self, text: str) -> bool:
        return bool(self.RESULT_CUE_PATTERN.search(text))

    def _result_span_after_test(
        self, text: str, test_end: int, line_end: int
    ) -> tuple[int, int] | None:
        tail = text[test_end:line_end]
        connector = self.RESULT_CONNECTOR_PATTERN.match(tail)
        result_start = test_end + (connector.end() if connector else 0)
        result_start, result_end = self._strip_span(text, result_start, line_end)
        if result_start >= result_end:
            return None
        comma_idx = text.find(",", result_start, result_end)
        if comma_idx != -1:
            result_end = comma_idx
            result_start, result_end = self._strip_span(text, result_start, result_end)
        result_text = text[result_start:result_end]
        if not self._looks_like_result(result_text):
            return None
        return result_start, result_end

    def _iter_lines(self, text: str):
        offset = 0
        for line in text.splitlines(keepends=True):
            line_start = offset
            line_end = offset + len(line.rstrip("\r\n"))
            yield line_start, line_end, text[line_start:line_end]
            offset += len(line)

    def _add_test_and_result_mentions(
        self, document: Document, mentions: list[EntityMention]
    ) -> None:
        text = document.text
        active_result_section = False

        for line_start, line_end, line in self._iter_lines(text):
            if self.RESULT_SECTION_PATTERN.search(line):
                active_result_section = True
            elif active_result_section and self.SECTION_BREAK_PATTERN.match(line):
                active_result_section = False

            line_has_result_context = active_result_section or bool(
                self.RESULT_SECTION_PATTERN.search(line)
            )

            found_test = False
            for match in self.TEST_NAME_PATTERN.finditer(line):
                test_start = line_start + match.start()
                test_end = line_start + match.end()
                test_start, test_end = self._trim_test_span(text, test_start, test_end)
                if test_start >= test_end:
                    continue

                found_test = True
                self._add_if_new(
                    document,
                    mentions,
                    TARGET_LABEL_TEST_NAME,
                    test_start,
                    test_end,
                    source="rule:clinical_test_recall",
                    confidence=0.92,
                    skip_any_overlap=True,
                )

                if line_has_result_context or self._looks_like_result(
                    text[test_end:line_end]
                ):
                    result_span = self._result_span_after_test(text, test_end, line_end)
                    if result_span is not None:
                        self._add_if_new(
                            document,
                            mentions,
                            TARGET_LABEL_TEST_RESULT,
                            result_span[0],
                            result_span[1],
                            source="rule:lab_result_recall",
                            confidence=0.9,
                        )

            if not found_test and line_has_result_context and ":" in line:
                colon_idx = line.find(":")
                rest_start = line_start + colon_idx + 1
                rest_start, rest_end = self._strip_span(text, rest_start, line_end)
                if rest_start < rest_end and self._looks_like_result(
                    text[rest_start:rest_end]
                ):
                    self._add_if_new(
                        document,
                        mentions,
                        TARGET_LABEL_TEST_RESULT,
                        rest_start,
                        rest_end,
                        source="rule:lab_result_section_recall",
                        confidence=0.82,
                    )

    def _add_symptom_mentions(
        self, document: Document, mentions: list[EntityMention]
    ) -> None:
        if not self.add_symptoms_from_symptom_sections:
            return

        active_symptom_section = False
        for line_start, _line_end, line in self._iter_lines(document.text):
            if self.SYMPTOM_SECTION_PATTERN.search(line):
                active_symptom_section = True
                continue
            if active_symptom_section and self.SECTION_BREAK_PATTERN.match(line):
                active_symptom_section = False
            if not active_symptom_section or not line.lstrip().startswith("-"):
                continue

            for match in self.SYMPTOM_PATTERN.finditer(line):
                start = line_start + match.start()
                end = line_start + match.end()
                self._add_if_new(
                    document,
                    mentions,
                    TARGET_LABEL_SYMPTOM,
                    start,
                    end,
                    source="rule:symptom_section_recall",
                    confidence=0.86,
                    skip_any_overlap=True,
                )

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        recalled = list(mentions)
        self._add_test_and_result_mentions(document, recalled)
        self._add_symptom_mentions(document, recalled)
        return sorted(
            recalled,
            key=lambda mention: (
                mention.span.start if mention.span.start is not None else 10**9,
                mention.span.end if mention.span.end is not None else 10**9,
            ),
        )
