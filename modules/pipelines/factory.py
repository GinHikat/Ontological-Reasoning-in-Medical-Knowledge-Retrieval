from __future__ import annotations

from collections.abc import Callable

from modules.pipelines.base import BasePipeline
from modules.pipelines.legacy_adapter import LegacyV5PipelineAdapter
from modules.pipelines.v5 import build_v5_refactored_pipeline

PipelineBuilder = Callable[[], BasePipeline]

PIPELINE_BUILDERS: dict[str, PipelineBuilder] = {
    "legacy_v5": LegacyV5PipelineAdapter,
    "v5_refactored": build_v5_refactored_pipeline,
}


def available_pipelines() -> list[str]:
    return sorted(PIPELINE_BUILDERS.keys())


def build_pipeline(name: str) -> BasePipeline:
    try:
        builder = PIPELINE_BUILDERS[name]
    except KeyError as exc:
        available = ", ".join(available_pipelines())
        raise ValueError(
            f"Unknown pipeline '{name}'. Available pipelines: {available}"
        ) from exc
    return builder()
