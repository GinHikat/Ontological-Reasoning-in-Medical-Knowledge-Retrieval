"""Common interface for task-specific span extractors (GLiNER / token / span)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from modules.common.schema import COMPETITION_LABELS, LABEL_NONE, Document, EntityMention

ExtractorBackend = Literal["gliner", "span_classifier", "token_classifier", "clinical_lm"]

# Direct competition labels — no Procedure → TÊN_XÉT_NGHIỆM remapping.
NER_LABEL_SET = frozenset({*COMPETITION_LABELS, LABEL_NONE})


class BaseTaskNERModel(ABC):
    """Backend-agnostic extractor that emits competition labels (or NONE)."""

    backend: ExtractorBackend

    @abstractmethod
    def extract(self, document: Document) -> list[EntityMention]:
        """Return spans labeled with competition types; drop or omit NONE."""
