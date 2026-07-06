from __future__ import annotations

from modules.components.assertions.base import BaseAssertionDetector
from modules.components.classification.base import BaseEntityClassifier
from modules.components.linking.base import BaseEntityLinker
from modules.components.ner.base import BaseNERExtractor
from modules.components.normalization.base import BaseDocumentNormalizer
from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.core.schemas import Document, FinalEntity
from modules.pipelines.base import BasePipeline


class ClinicalEntityLinkingPipeline(BasePipeline):
    """Composable pipeline orchestration for iterative competition experiments."""

    def __init__(
        self,
        ner: BaseNERExtractor,
        classifier: BaseEntityClassifier,
        linker: BaseEntityLinker,
        assertion_detector: BaseAssertionDetector,
        normalizer: BaseDocumentNormalizer | None = None,
        pre_classification_postprocessors: list[BaseMentionPostProcessor] | None = None,
        post_classification_postprocessors: list[BaseMentionPostProcessor]
        | None = None,
    ):
        self.normalizer = normalizer
        self.ner = ner
        self.pre_classification_postprocessors = pre_classification_postprocessors or []
        self.classifier = classifier
        self.post_classification_postprocessors = (
            post_classification_postprocessors or []
        )
        self.linker = linker
        self.assertion_detector = assertion_detector

    def process_document(self, document: Document) -> list[FinalEntity]:
        working_document = (
            self.normalizer.normalize(document) if self.normalizer else document
        )

        mentions = self.ner.extract(working_document)
        for postprocessor in self.pre_classification_postprocessors:
            mentions = postprocessor.apply(working_document, mentions)

        mentions = self.classifier.classify(working_document, mentions)
        for postprocessor in self.post_classification_postprocessors:
            mentions = postprocessor.apply(working_document, mentions)

        final_entities = self.linker.link(working_document, mentions)
        final_entities = self.assertion_detector.apply(working_document, final_entities)
        return final_entities
