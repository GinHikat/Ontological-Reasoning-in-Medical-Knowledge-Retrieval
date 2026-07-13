"""Frozen baseline track — strongest reproducible non-LLM pipeline."""

from modules.pipelines.baseline.pipeline import (
    BASELINE_TRACK_NAME,
    build_baseline_hybrid_pipeline,
)

__all__ = ["BASELINE_TRACK_NAME", "build_baseline_hybrid_pipeline"]
