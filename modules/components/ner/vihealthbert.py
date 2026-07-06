from __future__ import annotations

from modules.components.ner.base import BaseNERExtractor
from modules.core.schemas import Document, EntityMention


class ViHealthBertNERExtractor(BaseNERExtractor):
    """Adapter around the existing Hugging Face token-classification NER wrapper."""

    def __init__(self, model_name: str = "vihealthbert", mode: str = "vietnamese"):
        self.model_name = model_name
        self.mode = mode
        self._ner = None

    def _get_model(self):
        if self._ner is None:
            from modules.model.inference.inference_ner import NER

            self._ner = NER(mode=self.mode, model_name=self.model_name)
        return self._ner

    def extract(self, document: Document) -> list[EntityMention]:
        raw_entities = self._get_model().extract_entities(document.text)
        return [
            EntityMention.from_legacy(item, source=f"ner:{self.model_name}")
            for item in raw_entities
        ]
