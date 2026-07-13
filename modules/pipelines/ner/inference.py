"""NER inference entrypoints for the task-specific track."""

from __future__ import annotations

from modules.common.schema import Document, EntityMention
from modules.pipelines.ner.model import BaseTaskNERModel, ExtractorBackend


class UntrainedTaskNERModel(BaseTaskNERModel):
    """Placeholder until a five-label (+NONE) model is trained / wired."""

    backend: ExtractorBackend = "token_classifier"

    def __init__(self, backend: ExtractorBackend = "token_classifier") -> None:
        self.backend = backend

    def extract(self, document: Document) -> list[EntityMention]:
        raise NotImplementedError(
            "NER track model is not trained yet. Train a direct five-label + NONE "
            "extractor (no Procedure remapping), then register it in "
            "modules/pipelines/ner/inference.py. "
            f"Requested backend={self.backend!r}; document={document.doc_id!r}."
        )


def load_task_ner_model(
    backend: ExtractorBackend = "token_classifier",
    checkpoint: str | None = None,
) -> BaseTaskNERModel:
    """Load the active task NER backend.

    ``checkpoint`` is reserved for future HF / GLiNER weight paths.
    """
    _ = checkpoint
    return UntrainedTaskNERModel(backend=backend)
