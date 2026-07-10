from __future__ import annotations

from collections.abc import Callable

from modules.pipelines.base import BasePipeline
from modules.pipelines.legacy_adapter import LegacyV5PipelineAdapter
from modules.pipelines.v5 import build_v5_refactored_pipeline
from modules.pipelines.v6 import build_v6_refined_pipeline
from modules.pipelines.v7 import build_v7_structured_pipeline
from modules.pipelines.v8 import build_v8_candidate_integrity_pipeline

NER_MODEL_CHOICES = ["vihealthbert", "vipubmed-deberta", "phobert", "xlm-roberta"]

PipelineBuilder = Callable[..., BasePipeline]


def _build_v6(model_name: str = "vihealthbert") -> BasePipeline:
    return build_v6_refined_pipeline(model_name=model_name)


def _build_v7(model_name: str = "vihealthbert") -> BasePipeline:
    return build_v7_structured_pipeline(model_name=model_name)


def _build_v8(model_name: str = "vihealthbert") -> BasePipeline:
    return build_v8_candidate_integrity_pipeline(model_name=model_name)


PIPELINE_BUILDERS: dict[str, PipelineBuilder] = {
    "legacy_v5": LegacyV5PipelineAdapter,
    "v5_refactored": build_v5_refactored_pipeline,
    "v6_refined": _build_v6,
    "v7_structured": _build_v7,
    "v8_candidate_integrity": _build_v8,
}


def available_pipelines() -> list[str]:
    return sorted(PIPELINE_BUILDERS.keys())


def build_pipeline(name: str, model_name: str = "vihealthbert") -> BasePipeline:
    try:
        builder = PIPELINE_BUILDERS[name]
    except KeyError as exc:
        available = ", ".join(available_pipelines())
        raise ValueError(
            f"Unknown pipeline '{name}'. Available pipelines: {available}"
        ) from exc
    
    import inspect
    sig = inspect.signature(builder)
    if "model_name" in sig.parameters:
        return builder(model_name=model_name)
    return builder()
