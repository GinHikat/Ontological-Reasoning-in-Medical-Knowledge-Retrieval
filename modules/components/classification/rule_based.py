from __future__ import annotations

from modules.components.classification.base import BaseEntityClassifier
from modules.core.constants import (
    DISEASE_LIKE_RAW_LABELS,
    PROCEDURE_TEST_EXACT_TERMS,
    PROCEDURE_TEST_KEYWORDS,
    RAW_LABEL_TO_TARGET,
    TARGET_LABEL_TEST_NAME,
)
from modules.core.schemas import Document, EntityMention


class RuleBasedCompetitionLabelMapper(BaseEntityClassifier):
    """Map raw NER labels to competition labels and mark disease-like mentions for dual retrieval."""

    def classify(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        mapped_mentions: list[EntityMention] = []

        for mention in mentions:
            raw_label = mention.label
            mapped_type = RAW_LABEL_TO_TARGET.get(raw_label)
            is_disease_like = raw_label in DISEASE_LIKE_RAW_LABELS

            if not mapped_type and not is_disease_like:
                continue

            term_lower = mention.text.lower()
            if (
                any(keyword in term_lower for keyword in PROCEDURE_TEST_KEYWORDS)
                or term_lower in PROCEDURE_TEST_EXACT_TERMS
            ):
                mapped_type = TARGET_LABEL_TEST_NAME
                is_disease_like = False

            metadata = dict(mention.metadata)
            metadata["raw_label"] = raw_label
            metadata["is_disease_like"] = is_disease_like

            mapped_mentions.append(
                EntityMention(
                    text=mention.text,
                    label=mapped_type or raw_label,
                    span=mention.span,
                    confidence=mention.confidence,
                    source=mention.source,
                    metadata=metadata,
                )
            )

        return mapped_mentions
