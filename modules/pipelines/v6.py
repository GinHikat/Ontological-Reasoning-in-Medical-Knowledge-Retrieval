from __future__ import annotations

from modules.components.assertions.rule_based import RuleBasedAssertionDetector
from modules.components.classification.rule_based import RuleBasedCompetitionLabelMapper
from modules.components.linking.hybrid import HybridEntityLinker
from modules.components.ner.vihealthbert import ViHealthBertNERExtractor
from modules.components.normalization.vietnamese import IdentityDocumentNormalizer
from modules.components.postprocessing.clinical_recall import (
    ClinicalRecallPostProcessor,
)
from modules.components.postprocessing.drug_boundary import DrugBoundaryPostProcessor
from modules.components.postprocessing.overlap_dedup import OverlapDedupPostProcessor
from modules.components.postprocessing.precision_filter import (
    ClinicalPrecisionFilterPostProcessor,
)
from modules.components.postprocessing.type_correction import (
    ClinicalTypeCorrectionPostProcessor,
)
from modules.components.postprocessing.word_boundary import WordBoundaryPostProcessor
from modules.pipelines.clinical import ClinicalEntityLinkingPipeline


def build_v6_refined_pipeline(
    model_name: str = "vihealthbert",
) -> ClinicalEntityLinkingPipeline:
    """Build V6 with rule-based recall and precision cleanup on top of V5.

    `model_name` selects the base NER model and is used to namespace outputs
    (e.g. `output/vihealthbert/run1/...`).
    """

    return ClinicalEntityLinkingPipeline(
        normalizer=IdentityDocumentNormalizer(),
        ner=ViHealthBertNERExtractor(model_name=model_name),
        pre_classification_postprocessors=[WordBoundaryPostProcessor()],
        classifier=RuleBasedCompetitionLabelMapper(),
        post_classification_postprocessors=[
            ClinicalTypeCorrectionPostProcessor(),
            DrugBoundaryPostProcessor(),
            ClinicalRecallPostProcessor(),
            ClinicalPrecisionFilterPostProcessor(),
            OverlapDedupPostProcessor(remove_nested_same_label=True),
        ],
        linker=HybridEntityLinker(),
        assertion_detector=RuleBasedAssertionDetector(restrict_to_eligible_labels=True),
    )
