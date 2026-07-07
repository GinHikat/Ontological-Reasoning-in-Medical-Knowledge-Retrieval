from __future__ import annotations

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.core.schemas import Document, EntityMention


class OverlapDedupPostProcessor(BaseMentionPostProcessor):
    """Deduplicate exact spans and remove nested same-label artifacts."""

    def __init__(self, remove_nested_same_label: bool = True):
        self.remove_nested_same_label = remove_nested_same_label

    @staticmethod
    def _length(mention: EntityMention) -> int:
        start = mention.span.start
        end = mention.span.end
        if start is None or end is None or start > end:
            return 0
        return int(end) - int(start)

    @staticmethod
    def _contains(outer: EntityMention, inner: EntityMention) -> bool:
        outer_start = outer.span.start
        outer_end = outer.span.end
        inner_start = inner.span.start
        inner_end = inner.span.end
        if (
            outer_start is None
            or outer_end is None
            or inner_start is None
            or inner_end is None
            or outer_start > outer_end
            or inner_start > inner_end
        ):
            return False
        return (
            int(outer_start) <= int(inner_start)
            and int(inner_end) <= int(outer_end)
            and (outer_start, outer_end) != (inner_start, inner_end)
        )

    def _deduplicate_exact_spans(
        self, mentions: list[EntityMention]
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

    def _remove_nested_same_label(
        self, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        sorted_mentions = sorted(
            mentions,
            key=lambda mention: (
                mention.span.start if mention.span.start is not None else 10**9,
                -self._length(mention),
                -mention.confidence,
            ),
        )
        kept: list[EntityMention] = []
        for mention in sorted_mentions:
            if any(
                existing.label == mention.label and self._contains(existing, mention)
                for existing in kept
            ):
                continue
            kept.append(mention)
        return sorted(
            kept,
            key=lambda mention: (
                mention.span.start if mention.span.start is not None else 10**9,
                mention.span.end if mention.span.end is not None else 10**9,
            ),
        )

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        deduplicated = self._deduplicate_exact_spans(mentions)
        if self.remove_nested_same_label:
            deduplicated = self._remove_nested_same_label(deduplicated)
        return deduplicated
