"""Schema-aware LLM track — one-pass extraction + local ontology linking."""

from modules.pipelines.llm.pipeline import (
    LLM_TRACK_NAME,
    build_llm_pipeline,
)

__all__ = ["LLM_TRACK_NAME", "build_llm_pipeline"]
