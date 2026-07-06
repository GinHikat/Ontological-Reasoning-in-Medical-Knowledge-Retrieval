from __future__ import annotations

import re

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.core.constants import TARGET_LABEL_DRUG
from modules.core.schemas import Document, EntityMention, Span


class DrugBoundaryPostProcessor(BaseMentionPostProcessor):
    """Expand drug mentions to include immediately trailing dosage/frequency text."""

    DEFAULT_PATTERN = (
        r"^[\s\-]*(\d+(?:[.,]\d+)?\s*"
        r"(?:mg|g|mcg|ml|viên|ống|lọ|gói|đơn vị|IU|UI|x\s*\d+|po|bid|tid|qid|prn|giọt|lần|/|ngày|giờ|phút)"
        r"[a-zA-Z0-9\s/]*)"
    )

    def __init__(self, pattern: str | None = None):
        self.pattern = pattern or self.DEFAULT_PATTERN

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        expanded: list[EntityMention] = []
        text = document.text

        for mention in mentions:
            start_raw = mention.span.start
            end_raw = mention.span.end
            if (
                mention.label != TARGET_LABEL_DRUG
                or start_raw is None
                or end_raw is None
                or start_raw > end_raw
            ):
                expanded.append(mention)
                continue

            start = int(start_raw)
            end = int(end_raw)
            match = re.match(self.pattern, text[end:], flags=re.IGNORECASE)
            if match:
                new_end = end + match.end()
                while new_end > end and text[new_end - 1].isspace():
                    new_end -= 1
                end = new_end

            expanded.append(
                EntityMention(
                    text=text[start:end],
                    label=mention.label,
                    span=Span(start, end),
                    confidence=mention.confidence,
                    source=mention.source,
                    metadata=dict(mention.metadata),
                )
            )

        return expanded
