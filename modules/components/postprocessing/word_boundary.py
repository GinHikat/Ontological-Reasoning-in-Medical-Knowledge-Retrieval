from __future__ import annotations

import string

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.core.schemas import Document, EntityMention, Span


class WordBoundaryPostProcessor(BaseMentionPostProcessor):
    """Expand NER spans that end in the middle of a word to nearest separators."""

    def __init__(self, separators: str | None = None):
        self.separators = set(separators or (string.whitespace + string.punctuation))

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        fixed: list[EntityMention] = []
        text = document.text

        for mention in mentions:
            start_raw = mention.span.start
            end_raw = mention.span.end
            if start_raw is None or end_raw is None or start_raw > end_raw:
                continue

            start = int(start_raw)
            end = int(end_raw)

            while start > 0 and text[start - 1] not in self.separators:
                start -= 1
            while end < len(text) and text[end] not in self.separators:
                end += 1

            fixed.append(
                EntityMention(
                    text=text[start:end],
                    label=mention.label,
                    span=Span(start, end),
                    confidence=mention.confidence,
                    source=mention.source,
                    metadata=dict(mention.metadata),
                )
            )

        return fixed
