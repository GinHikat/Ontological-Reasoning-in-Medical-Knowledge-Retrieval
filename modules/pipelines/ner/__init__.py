"""Task-specific NER track — five competition labels + NONE."""

from modules.pipelines.ner.pipeline import (
    NER_TRACK_NAME,
    build_ner_pipeline,
)

__all__ = ["NER_TRACK_NAME", "build_ner_pipeline"]
