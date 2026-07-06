from __future__ import annotations

from abc import ABC, abstractmethod

from modules.core.schemas import Document, FinalEntity


class BaseAssertionDetector(ABC):
    @abstractmethod
    def apply(
        self, document: Document, entities: list[FinalEntity]
    ) -> list[FinalEntity]:
        """Attach contextual assertion flags to final entities."""
