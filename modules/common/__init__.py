"""Shared schema, ontology, validation, and output helpers for all tracks."""

from modules.common.assertions import detect_assertions
from modules.common.exact_span import align_entities
from modules.common.output_writer import CompetitionJSONFormatter, write_submission_json
from modules.common.schema import (
    COMPETITION_LABELS,
    LABEL_NONE,
    Document,
    EntityMention,
    FinalEntity,
    Span,
)
from modules.common.validation import validate_competition_entity

__all__ = [
    "COMPETITION_LABELS",
    "LABEL_NONE",
    "CompetitionJSONFormatter",
    "Document",
    "EntityMention",
    "FinalEntity",
    "Span",
    "align_entities",
    "detect_assertions",
    "validate_competition_entity",
    "write_submission_json",
]
