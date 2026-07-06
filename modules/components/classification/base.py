from __future__ import annotations

from abc import ABC, abstractmethod

from modules.core.schemas import Document, EntityMention


class BaseEntityClassifier(ABC):
    @abstractmethod
    def classify(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        """Map raw model labels to competition labels and store type metadata."""
