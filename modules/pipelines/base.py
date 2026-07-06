from __future__ import annotations

from abc import ABC, abstractmethod

from modules.core.schemas import Document, FinalEntity


class BasePipeline(ABC):
    """Stable interface implemented by all versioned pipelines."""

    @abstractmethod
    def process_document(self, document: Document) -> list[FinalEntity]:
        """Run the full entity extraction/linking/assertion pipeline for one document."""

    def process_text(self, text: str, doc_id: str = "") -> list[FinalEntity]:
        return self.process_document(Document(doc_id=doc_id, text=text))
