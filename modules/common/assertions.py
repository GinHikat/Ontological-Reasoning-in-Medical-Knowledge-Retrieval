"""Shared assertion detector for all active tracks."""

from __future__ import annotations

from modules.components.assertions.rule_based import RuleBasedAssertionDetector
from modules.components.structure.section_parser import VietnameseClinicalSectionParser
from modules.core.schemas import Document, FinalEntity


def build_default_assertion_detector() -> RuleBasedAssertionDetector:
    section_parser = VietnameseClinicalSectionParser()
    return RuleBasedAssertionDetector(
        restrict_to_eligible_labels=True,
        section_parser=section_parser,
        use_section_parser=True,
        detect_family=True,
    )


def detect_assertions(
    document: Document,
    entities: list[FinalEntity],
    detector: RuleBasedAssertionDetector | None = None,
) -> list[FinalEntity]:
    det = detector or build_default_assertion_detector()
    return det.apply(document, entities)
