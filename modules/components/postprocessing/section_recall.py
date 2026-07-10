from __future__ import annotations

import re
import unicodedata

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.components.structure.section_parser import VietnameseClinicalSectionParser
from modules.core.constants import TARGET_LABEL_SYMPTOM
from modules.core.schemas import Document, EntityMention, Span


class SectionAwareRecallPostProcessor(BaseMentionPostProcessor):
    """Independent section-aware candidate generation for symptoms and RFV phrases."""

    SYMPTOM_SECTION_NAMES = {
        "Triệu chứng hiện tại",
    }
    REASON_SECTION_NAMES = {
        "Lý do nhập viện",
    }

    NEGATION_PREFIX = re.compile(
        r"^(?:không\s+(?:có\s+)?|chưa\s+(?:có\s+)?|phủ\s+nhận\s+)",
        flags=re.IGNORECASE,
    )
    LEADING_BULLET = re.compile(r"^[\s\-–—*•]+(?:\d+[\.\)]\s*)?")
    TRAILING_PUNCT = re.compile(r"[\s.,;:!?]+$")
    SPLIT_REASON = re.compile(r"\s*(?:,|/|;|\bvà\b|\b&)\s*", flags=re.IGNORECASE)

    STATUS_STOPLIST = {
        "bệnh nhân tỉnh",
        "tiếp xúc tốt",
        "da niêm mạc hồng",
        "các cơ quan khác chưa phát hiện bất thường",
        "toàn trạng ổn định",
        "tỉnh táo",
        "tiếp xúc được",
        "da hồng",
        "niêm mạc hồng",
        "không ghi nhận gì bất thường",
        "chưa phát hiện bất thường",
    }

    def __init__(self, section_parser: VietnameseClinicalSectionParser | None = None):
        self.section_parser = section_parser or VietnameseClinicalSectionParser()

    @staticmethod
    def _norm(text: str) -> str:
        text = unicodedata.normalize("NFKC", text).lower()
        return re.sub(r"\s+", " ", text).strip(" \t\r\n.,;:-")

    def _is_stoplist(self, phrase: str) -> bool:
        n = self._norm(phrase)
        if not n or len(n) < 2:
            return True
        if n in self.STATUS_STOPLIST:
            return True
        for stop in self.STATUS_STOPLIST:
            if n == stop or n.startswith(stop + " "):
                return True
        # Generic exam filler
        if re.search(r"chưa phát hiện|không ghi nhận gì|ổn định$", n):
            return True
        return False

    def _clean_phrase_span(
        self, text: str, start: int, end: int
    ) -> tuple[int, int] | None:
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1] in " \t\r\n.,;:!?-":
            end -= 1
        if start >= end:
            return None

        fragment = text[start:end]
        # Strip leading bullet/numbering already mostly handled; strip negation cue
        neg = self.NEGATION_PREFIX.match(fragment)
        if neg:
            start = start + neg.end()
            while start < end and text[start].isspace():
                start += 1
        if start >= end:
            return None
        phrase = text[start:end]
        if self._is_stoplist(phrase):
            return None
        return start, end

    def _add_mention(
        self,
        document: Document,
        mentions: list[EntityMention],
        start: int,
        end: int,
        confidence: float,
        meta: dict,
    ) -> None:
        cleaned = self._clean_phrase_span(document.text, start, end)
        if cleaned is None:
            return
        start, end = cleaned
        text = document.text[start:end]
        # Avoid exact duplicate spans of same label
        for m in mentions:
            if (
                m.label == TARGET_LABEL_SYMPTOM
                and m.span.start == start
                and m.span.end == end
            ):
                return
        mentions.append(
            EntityMention(
                text=text,
                label=TARGET_LABEL_SYMPTOM,
                span=Span(start, end),
                confidence=confidence,
                source="section_recall",
                metadata={
                    "section_recall": True,
                    **meta,
                },
            )
        )

    def _extract_symptom_bullets(
        self, document: Document, mentions: list[EntityMention], sections
    ) -> None:
        text = document.text
        heading_break = re.compile(
            r"^\s*(?:\d+\s*[\.\)\-:]\s+)?[A-ZÀ-Ỹ].{0,80}$|"
            r"^\s*(?:lý\s+do|kết\s+quả|chẩn\s+đoán|điều\s+trị|thuốc|các\s+thủ|"
            r"tình\s+trạng|khám|cận\s+lâm|bệnh\s+sử|tiền\s+sử)",
            flags=re.IGNORECASE,
        )
        for section in sections:
            if section.name not in self.SYMPTOM_SECTION_NAMES:
                continue
            body = text[section.start : section.end]
            offset = section.start
            for raw_line in body.splitlines(keepends=True):
                line_start = offset
                offset += len(raw_line)
                line = raw_line.rstrip("\r\n")
                stripped = line.lstrip()
                if not stripped:
                    continue
                # Stop at the next structural heading inside an over-long section span
                if heading_break.match(stripped) and not re.match(
                    r"^[\-–—*•]", stripped
                ):
                    # Allow the symptom heading variants themselves only at start
                    if not re.search(r"triệu\s+chứng", stripped, flags=re.IGNORECASE):
                        break
                # Only bullet / numbered items in symptom sections
                is_bullet = bool(re.match(r"^[\-–—*•]", stripped)) or bool(
                    re.match(r"^\d+[\.\)]\s+", stripped)
                )
                if not is_bullet:
                    continue
                m = re.match(r"^(\s*(?:[\-–—*•]|\d+[\.\)]\s*)\s*)(.*)$", line)
                if not m:
                    continue
                content_local = m.start(2)
                content = m.group(2)
                if not content.strip():
                    continue
                if len(content.strip()) > 80 or len(content.strip().split()) > 12:
                    continue
                # Reject instructional / administrative bullets
                low = content.strip().lower()
                if low.startswith(
                    ("được ", "sau đó", "bệnh nhân được", "chỉ định", "đến khoa")
                ):
                    continue
                abs_start = line_start + content_local
                abs_end = abs_start + len(content)
                self._add_mention(
                    document,
                    mentions,
                    abs_start,
                    abs_end,
                    confidence=0.88,
                    meta={"section": section.name, "rule": "symptom_bullet"},
                )

    def _extract_reason_phrases(
        self, document: Document, mentions: list[EntityMention], sections
    ) -> None:
        text = document.text
        for section in sections:
            if section.name not in self.REASON_SECTION_NAMES:
                continue
            # Only short content after heading (conservative)
            # Take until first newline within section, max ~150 chars
            end = section.start
            while end < section.end and text[end] not in "\n\r":
                end += 1
            if end - section.start > 150:
                continue
            chunk = text[section.start:end]
            # Split on commas / và
            parts: list[tuple[int, int]] = []
            cursor = 0
            for match in self.SPLIT_REASON.finditer(chunk):
                parts.append((cursor, match.start()))
                cursor = match.end()
            parts.append((cursor, len(chunk)))
            for local_s, local_e in parts:
                abs_s = section.start + local_s
                abs_e = section.start + local_e
                phrase = text[abs_s:abs_e].strip()
                if not phrase or len(phrase) < 2 or len(phrase) > 60:
                    continue
                # Skip if looks like long prose clause
                if len(phrase.split()) > 8:
                    continue
                self._add_mention(
                    document,
                    mentions,
                    abs_s,
                    abs_e,
                    confidence=0.8,
                    meta={"section": section.name, "rule": "reason_for_visit"},
                )

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        sections = self.section_parser.parse(document.text)
        document.metadata["clinical_sections"] = sections
        recalled = list(mentions)
        self._extract_symptom_bullets(document, recalled, sections)
        self._extract_reason_phrases(document, recalled, sections)
        return sorted(
            recalled,
            key=lambda m: (
                m.span.start if m.span.start is not None else 10**9,
                m.span.end if m.span.end is not None else 10**9,
            ),
        )
