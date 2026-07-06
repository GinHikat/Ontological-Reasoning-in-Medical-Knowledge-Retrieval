from __future__ import annotations

import unicodedata

from modules.components.normalization.base import BaseDocumentNormalizer
from modules.core.schemas import Document


class IdentityDocumentNormalizer(BaseDocumentNormalizer):
    """No-op normalizer for offset-sensitive pipelines."""

    def normalize(self, document: Document) -> Document:
        return document


class VietnameseClinicalNormalizer(BaseDocumentNormalizer):
    """
    Conservative normalizer that stores normalized text in metadata without changing
    the original document text. This preserves competition character offsets.
    """

    def normalize(self, document: Document) -> Document:
        normalized = unicodedata.normalize("NFC", document.text)
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        metadata = dict(document.metadata)
        metadata["normalized_text"] = normalized
        return Document(doc_id=document.doc_id, text=document.text, metadata=metadata)
