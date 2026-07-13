"""Frozen baseline_hybrid — formerly scored as v7_structured (24.79660).

Do not add new rules here. This track exists only as:
  reference score / fallback / comparison target / weak-label source.
"""

from __future__ import annotations

from modules.components.assertions.rule_based import RuleBasedAssertionDetector
from modules.components.classification.rule_based import RuleBasedCompetitionLabelMapper
from modules.components.linking.hybrid import HybridEntityLinker
from modules.components.ner.vihealthbert import ViHealthBertNERExtractor
from modules.components.normalization.vietnamese import IdentityDocumentNormalizer
from modules.components.postprocessing.candidate_merge import CandidateMergePostProcessor
from modules.components.postprocessing.clinical_recall import (
    ClinicalRecallPostProcessor,
)
from modules.components.postprocessing.drug_boundary import DrugBoundaryPostProcessor
from modules.components.postprocessing.lab_pair_recall import LabPairRecallPostProcessor
from modules.components.postprocessing.ontology_diagnosis_recall import (
    OntologyDiagnosisRecallPostProcessor,
)
from modules.components.postprocessing.ontology_drug_recall import (
    OntologyDrugRecallPostProcessor,
)
from modules.components.postprocessing.overlap_dedup import OverlapDedupPostProcessor
from modules.components.postprocessing.precision_filter import (
    ClinicalPrecisionFilterPostProcessor,
)
from modules.components.postprocessing.section_recall import (
    SectionAwareRecallPostProcessor,
)
from modules.components.postprocessing.type_correction import (
    ClinicalTypeCorrectionPostProcessor,
)
from modules.components.postprocessing.word_boundary import WordBoundaryPostProcessor
from modules.components.structure.section_parser import VietnameseClinicalSectionParser
from modules.pipelines.clinical import ClinicalEntityLinkingPipeline

BASELINE_TRACK_NAME = "baseline_hybrid"
BASELINE_LEADERBOARD_SCORE = 24.79660
# Historical factory name (archived). Do not re-register as a CLI choice.
_HISTORICAL_NAME = "v7_structured"


def build_baseline_hybrid_pipeline(
    model_name: str = "vihealthbert",
) -> ClinicalEntityLinkingPipeline:
    """Frozen hybrid NER + deterministic cleanup + local ICD/RxNorm linking."""

    section_parser = VietnameseClinicalSectionParser()

    return ClinicalEntityLinkingPipeline(
        normalizer=IdentityDocumentNormalizer(),
        ner=ViHealthBertNERExtractor(model_name=model_name),
        pre_classification_postprocessors=[WordBoundaryPostProcessor()],
        classifier=RuleBasedCompetitionLabelMapper(),
        post_classification_postprocessors=[
            ClinicalTypeCorrectionPostProcessor(),
            DrugBoundaryPostProcessor(),
            SectionAwareRecallPostProcessor(section_parser=section_parser),
            LabPairRecallPostProcessor(section_parser=section_parser),
            OntologyDrugRecallPostProcessor(section_parser=section_parser),
            OntologyDiagnosisRecallPostProcessor(section_parser=section_parser),
            ClinicalRecallPostProcessor(),
            CandidateMergePostProcessor(),
            ClinicalPrecisionFilterPostProcessor(),
            OverlapDedupPostProcessor(remove_nested_same_label=True),
        ],
        linker=HybridEntityLinker(),
        assertion_detector=RuleBasedAssertionDetector(
            restrict_to_eligible_labels=True,
            section_parser=section_parser,
            use_section_parser=True,
            detect_family=True,
        ),
    )


# Back-compat alias for archived experiment code that still imports the old name.
build_v7_structured_pipeline = build_baseline_hybrid_pipeline
