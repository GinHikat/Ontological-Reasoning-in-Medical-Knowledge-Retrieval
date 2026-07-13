"""Schema-aware LLM pipeline — diagnostic (OpenRouter) or competition (localhost).

Architecture:
  document
      → one schema-aware LLM extraction call
      → exact-span validation
      → local ICD/RxNorm retrieval
      → optional large-model judge only for risky cases
      → final JSON

The 786-call three-extractor ensemble is archived evidence, not this track.
"""

from __future__ import annotations

from typing import Any

from modules.common.schema import Document, FinalEntity, Span
from modules.core.schemas import FinalEntity as CoreFinalEntity
from modules.pipelines.base import BasePipeline
from modules.pipelines.llm.extractor import LLMMode, mode_banner

LLM_TRACK_NAME = "llm"

# Archived frontier diagnostic score (OpenRouter free ensemble).
LLM_DIAGNOSTIC_LEADERBOARD_SCORE = 35.72280


class SchemaAwareLLMPipeline(BasePipeline):
    """Document-level runner for the LLM track.

    Full corpus runs go through ``scripts/run_llm.py`` (batch + caches).
    ``process_document`` supports smoke / single-doc use and raises a clear
    error until a live backend is configured for the selected mode.
    """

    def __init__(self, mode: LLMMode = "competition") -> None:
        self.mode = mode
        self.compliance_note = mode_banner(mode)

    def process_document(self, document: Document) -> list[FinalEntity]:
        raise NotImplementedError(
            f"LLM track ({self.mode}): use scripts/run_llm.py --mode {self.mode} "
            f"for corpus runs. ({self.compliance_note}) "
            f"doc_id={document.doc_id!r}"
        )


def build_llm_pipeline(
    model_name: str = "vihealthbert",
    mode: LLMMode = "competition",
) -> SchemaAwareLLMPipeline:
    """Factory entry — ``model_name`` ignored (LLM track does not use ViHealthBert)."""
    _ = model_name
    return SchemaAwareLLMPipeline(mode=mode)


def competition_dicts_to_final_entities(
    rows: list[dict[str, Any]],
) -> list[CoreFinalEntity]:
    """Convert competition JSON rows to FinalEntity (for compare tools)."""
    out: list[CoreFinalEntity] = []
    for row in rows:
        pos = row.get("position") or [0, 0]
        out.append(
            CoreFinalEntity(
                text=row.get("text", ""),
                type=row.get("type", ""),
                span=Span(int(pos[0]), int(pos[1])),
                candidates=list(row.get("candidates") or []),
                assertions=list(row.get("assertions") or []),
                source="llm",
            )
        )
    return out
