"""Active track factory — only baseline_hybrid, ner, and llm."""

from __future__ import annotations

from collections.abc import Callable

from modules.pipelines.base import BasePipeline
from modules.pipelines.baseline import build_baseline_hybrid_pipeline
from modules.pipelines.llm import build_llm_pipeline
from modules.pipelines.ner import build_ner_pipeline

NER_MODEL_CHOICES = ["vihealthbert", "vipubmed-deberta", "phobert", "xlm-roberta"]

PipelineBuilder = Callable[..., BasePipeline]

ACTIVE_TRACKS = ("baseline_hybrid", "ner", "llm")

PIPELINE_BUILDERS: dict[str, PipelineBuilder] = {
    "baseline_hybrid": build_baseline_hybrid_pipeline,
    "ner": build_ner_pipeline,
    "llm": build_llm_pipeline,
}

# Historical names → archive pointer (not registered as runnable).
ARCHIVED_PIPELINE_ALIASES = {
    "legacy_v5": "archives/legacy_pipelines/",
    "v5_refactored": "archives/legacy_pipelines/",
    "v6_refined": "archives/legacy_pipelines/",
    "v7_structured": "baseline_hybrid (frozen rename)",
    "v8_candidate_integrity": "archives/legacy_pipelines/",
    "v8_candidate_rescue": "archives/legacy_pipelines/",
    "v9_llm_recall": "archives/legacy_pipelines/",
    "v10_llm_conflict_resolution": "archives/legacy_pipelines/",
}


def available_pipelines() -> list[str]:
    return list(ACTIVE_TRACKS)


def build_pipeline(name: str, model_name: str = "vihealthbert", **kwargs) -> BasePipeline:
    if name in ARCHIVED_PIPELINE_ALIASES and name not in PIPELINE_BUILDERS:
        hint = ARCHIVED_PIPELINE_ALIASES[name]
        raise ValueError(
            f"Pipeline '{name}' is archived. "
            f"Active tracks: {', '.join(available_pipelines())}. "
            f"See {hint}"
        )
    try:
        builder = PIPELINE_BUILDERS[name]
    except KeyError as exc:
        available = ", ".join(available_pipelines())
        raise ValueError(
            f"Unknown pipeline '{name}'. Active tracks: {available}"
        ) from exc

    import inspect

    sig = inspect.signature(builder)
    call_kwargs: dict = {}
    if "model_name" in sig.parameters:
        call_kwargs["model_name"] = model_name
    for key, value in kwargs.items():
        if key in sig.parameters:
            call_kwargs[key] = value
    return builder(**call_kwargs)
