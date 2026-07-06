from __future__ import annotations

from abc import ABC, abstractmethod

from modules.core.schemas import Document, EntityMention


class BaseNERExtractor(ABC):
    @abstractmethod
    def extract(self, document: Document) -> list[EntityMention]:
        """Return raw entity mentions with offsets in the original document."""
