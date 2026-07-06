from __future__ import annotations

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.core.schemas import Document, EntityMention


class OverlapDedupPostProcessor(BaseMentionPostProcessor):
    """Conservative exact-span deduplication; keeps first/highest confidence mention."""

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        best_by_key: dict[tuple[int | None, int | None, str], EntityMention] = {}
        order: list[tuple[int | None, int | None, str]] = []

        for mention in mentions:
            key = (mention.span.start, mention.span.end, mention.label)
            if key not in best_by_key:
                best_by_key[key] = mention
                order.append(key)
            elif mention.confidence > best_by_key[key].confidence:
                best_by_key[key] = mention

        return [best_by_key[key] for key in order]
