from __future__ import annotations

from typing import Any

from modules.components.formatting.base import BaseOutputFormatter
from modules.core.constants import CANDIDATE_ELIGIBLE_LABELS
from modules.core.schemas import FinalEntity


class CompetitionJSONFormatter(BaseOutputFormatter):
    """Format entities to the competition JSON schema."""

    def __init__(self, include_empty_candidates_for_linkable_types: bool = True):
        self.include_empty_candidates_for_linkable_types = (
            include_empty_candidates_for_linkable_types
        )

    def format(self, entities: list[FinalEntity]) -> list[dict[str, Any]]:
        formatted: list[dict[str, Any]] = []
        for entity in entities:
            item = {
                "text": entity.text,
                "type": entity.type,
                "assertions": entity.assertions,
                "position": entity.span.as_list(),
            }
            if entity.candidates or (
                self.include_empty_candidates_for_linkable_types
                and entity.type in CANDIDATE_ELIGIBLE_LABELS
            ):
                item["candidates"] = entity.candidates
            formatted.append(item)
        return formatted
