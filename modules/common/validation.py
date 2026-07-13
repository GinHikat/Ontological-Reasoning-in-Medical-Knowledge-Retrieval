"""Shared competition-entity validation helpers."""

from __future__ import annotations

from typing import Any

from modules.common.schema import COMPETITION_LABELS
from modules.core.constants import CANDIDATE_ELIGIBLE_LABELS


def validate_competition_entity(
    entity: dict[str, Any],
    *,
    document_text: str | None = None,
) -> list[str]:
    """Return a list of validation error strings (empty = ok)."""
    errors: list[str] = []
    etype = entity.get("type")
    if etype not in COMPETITION_LABELS:
        errors.append(f"invalid type: {etype!r}")

    text = entity.get("text")
    pos = entity.get("position")
    if not isinstance(text, str) or not text:
        errors.append("missing text")
    if not isinstance(pos, list) or len(pos) != 2:
        errors.append("position must be [start, end]")
    elif document_text is not None and isinstance(text, str):
        start, end = int(pos[0]), int(pos[1])
        if document_text[start:end] != text:
            errors.append("text does not match document[position]")

    if etype in CANDIDATE_ELIGIBLE_LABELS:
        cands = entity.get("candidates")
        if cands is not None and not isinstance(cands, list):
            errors.append("candidates must be a list")

    assertions = entity.get("assertions")
    if assertions is not None and not isinstance(assertions, list):
        errors.append("assertions must be a list")

    return errors
