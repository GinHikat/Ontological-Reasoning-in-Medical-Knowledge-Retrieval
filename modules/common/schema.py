"""Canonical competition schema types shared by baseline / NER / LLM tracks."""

from __future__ import annotations

from modules.core.constants import TARGET_LABELS
from modules.core.schemas import Document, EntityMention, FinalEntity, Span

# Five competition labels plus explicit NONE for NER training / filtering.
COMPETITION_LABELS = frozenset(TARGET_LABELS)
LABEL_NONE = "NONE"

__all__ = [
    "COMPETITION_LABELS",
    "LABEL_NONE",
    "Document",
    "EntityMention",
    "FinalEntity",
    "Span",
]
