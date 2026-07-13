"""Shared competition JSON writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from modules.components.formatting.competition_json import CompetitionJSONFormatter
from modules.core.schemas import FinalEntity

__all__ = ["CompetitionJSONFormatter", "write_submission_json"]


def write_submission_json(
    path: Path,
    entities: list[FinalEntity] | list[dict[str, Any]],
    *,
    indent: int | None = 4,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if entities and isinstance(entities[0], FinalEntity):
        payload = CompetitionJSONFormatter(
            include_empty_candidates_for_linkable_types=True
        ).format(entities)  # type: ignore[arg-type]
    else:
        payload = entities  # type: ignore[assignment]
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=indent),
        encoding="utf-8",
    )
