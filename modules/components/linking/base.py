from __future__ import annotations

from abc import ABC, abstractmethod

from modules.core.schemas import Document, EntityMention, FinalEntity


class BaseEntityLinker(ABC):
    @abstractmethod
    def link(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[FinalEntity]:
        """Attach ontology candidates and produce final entities before assertion detection."""
