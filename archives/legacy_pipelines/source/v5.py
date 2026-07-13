from __future__ import annotations

from modules.components.assertions.rule_based import RuleBasedAssertionDetector
from modules.components.classification.rule_based import RuleBasedCompetitionLabelMapper
from modules.components.linking.hybrid import HybridEntityLinker
from modules.components.ner.vihealthbert import ViHealthBertNERExtractor
from modules.components.normalization.vietnamese import IdentityDocumentNormalizer
from modules.components.postprocessing.drug_boundary import DrugBoundaryPostProcessor
from modules.components.postprocessing.word_boundary import WordBoundaryPostProcessor
from modules.pipelines.clinical import ClinicalEntityLinkingPipeline


def build_v5_refactored_pipeline() -> ClinicalEntityLinkingPipeline:
    """Build the current V5 behavior using the new composable architecture."""

    return ClinicalEntityLinkingPipeline(
        normalizer=IdentityDocumentNormalizer(),
        ner=ViHealthBertNERExtractor(model_name="vihealthbert"),
        pre_classification_postprocessors=[WordBoundaryPostProcessor()],
        classifier=RuleBasedCompetitionLabelMapper(),
        post_classification_postprocessors=[DrugBoundaryPostProcessor()],
        linker=HybridEntityLinker(),
        assertion_detector=RuleBasedAssertionDetector(
            restrict_to_eligible_labels=False
        ),
    )
