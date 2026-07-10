"""Local LLM client utilities for offline high-recall entity proposals."""

from modules.components.llm.client import LocalChatLLMClient
from modules.components.llm.document_lines import LineIndexedDocument, build_line_index
from modules.components.llm.response_parser import parse_proposer_response, parse_verifier_response
from modules.components.llm.schemas import (
    AlignedProposal,
    LLMProposal,
    VerifierDecision,
)
from modules.components.llm.span_aligner import align_proposals

__all__ = [
    "AlignedProposal",
    "LLMProposal",
    "LineIndexedDocument",
    "LocalChatLLMClient",
    "VerifierDecision",
    "align_proposals",
    "build_line_index",
    "parse_proposer_response",
    "parse_verifier_response",
]
