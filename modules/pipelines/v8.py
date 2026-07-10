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


def build_v8_candidate_integrity_pipeline(
    model_name: str = "vihealthbert",
) -> ClinicalEntityLinkingPipeline:
    """V8: isolated candidate-integrity experiment on top of v7_structured.

    Structurally identical to v7_structured. The ONLY intended inference
    differences are:

    1. OntologyDrugRecallPostProcessor(track_rxcui_sets=True)
    2. HybridEntityLinker(use_unambiguous_preset_drug_rxcui=True)

    Entity spans, types, and assertions must remain identical to v7.
    Only THUỐC candidates may change when an ontology-recall alias maps to
    exactly one RxCUI.
    """

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
            OntologyDrugRecallPostProcessor(
                section_parser=section_parser,
                track_rxcui_sets=True,
            ),
            OntologyDiagnosisRecallPostProcessor(section_parser=section_parser),
            ClinicalRecallPostProcessor(),
            CandidateMergePostProcessor(),
            ClinicalPrecisionFilterPostProcessor(),
            OverlapDedupPostProcessor(remove_nested_same_label=True),
        ],
        linker=HybridEntityLinker(use_unambiguous_preset_drug_rxcui=True),
        assertion_detector=RuleBasedAssertionDetector(
            restrict_to_eligible_labels=True,
            section_parser=section_parser,
            use_section_parser=True,
            detect_family=True,
        ),
    )
