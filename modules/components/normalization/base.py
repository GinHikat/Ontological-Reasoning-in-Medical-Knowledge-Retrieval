from __future__ import annotations

from abc import ABC, abstractmethod

from modules.core.schemas import Document


class BaseDocumentNormalizer(ABC):
    @abstractmethod
    def normalize(self, document: Document) -> Document:
        """Return a normalized document while preserving original character offsets when required."""
