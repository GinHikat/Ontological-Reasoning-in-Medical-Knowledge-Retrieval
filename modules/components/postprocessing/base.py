from __future__ import annotations

from abc import ABC, abstractmethod

from modules.core.schemas import Document, EntityMention


class BaseMentionPostProcessor(ABC):
    @abstractmethod
    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        """Adjust, add, remove, or deduplicate raw mentions."""
