"""Task-specific NER pipeline: extract → assert → shared ontology → JSON-ready."""

from __future__ import annotations

from modules.common.assertions import build_default_assertion_detector
from modules.common.ontology import SharedOntologyLayer
from modules.common.schema import Document, FinalEntity, LABEL_NONE
from modules.pipelines.base import BasePipeline
from modules.pipelines.ner.inference import load_task_ner_model
from modules.pipelines.ner.model import BaseTaskNERModel, ExtractorBackend

NER_TRACK_NAME = "ner"


class TaskSpecificNERPipeline(BasePipeline):
    """
    document
        → task-specific span extractor (5 labels + NONE)
        → drop NONE
        → contextual assertions
        → shared local ICD/RxNorm linking
    """

    def __init__(
        self,
        extractor: BaseTaskNERModel,
        ontology: SharedOntologyLayer | None = None,
    ) -> None:
        self.extractor = extractor
        self.ontology = ontology or SharedOntologyLayer(mode="hybrid")
        self.assertion_detector = build_default_assertion_detector()

    def process_document(self, document: Document) -> list[FinalEntity]:
        mentions = [
            m
            for m in self.extractor.extract(document)
            if m.label != LABEL_NONE
        ]
        linked = self.ontology.link_mentions(document, mentions)
        return self.assertion_detector.apply(document, linked)


def build_ner_pipeline(
    model_name: str = "vihealthbert",
    backend: ExtractorBackend = "token_classifier",
    checkpoint: str | None = None,
) -> TaskSpecificNERPipeline:
    """Build the active NER-direction pipeline.

    ``model_name`` is accepted for factory symmetry with baseline; the task
    model ignores the generic three-class ViHealthBert weights until replaced.
    """
    _ = model_name
    extractor = load_task_ner_model(backend=backend, checkpoint=checkpoint)
    return TaskSpecificNERPipeline(extractor=extractor)
