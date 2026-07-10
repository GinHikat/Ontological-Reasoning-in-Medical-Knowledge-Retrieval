from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


ALLOWED_LLM_TYPES = frozenset({"TRIỆU_CHỨNG", "CHẨN_ĐOÁN", "THUỐC"})

PROPOSER_PROMPT_VERSION = "v9_llm_recall_proposer_v1"
VERIFIER_PROMPT_VERSION = "v9_llm_recall_verifier_v1"
DEFAULT_MODEL = "Qwen/Qwen3.5-9B"


@dataclass
class LLMProposal:
    line_id: str
    text: str
    type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AlignedProposal:
    proposal_id: int
    line_id: str
    text: str
    type: str
    start: int
    end: int
    status: str = "aligned"  # aligned | zero_match | multiple_match | bad_line
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerifierDecision:
    proposal_id: int
    accept: bool
    type: Optional[str] = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AcceptedLLMCandidate:
    text: str
    type: str
    start: int
    end: int
    line_id: str
    proposer_type: str
    verifier_type: str
    proposal_id: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LLMGenerationSettings:
    model: str = DEFAULT_MODEL
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 4096
    enable_thinking: bool = False
    proposer_prompt_version: str = PROPOSER_PROMPT_VERSION
    verifier_prompt_version: str = VERIFIER_PROMPT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentLLMCacheRecord:
    """Offline cache entry keyed by document SHA256."""

    document_sha256: str
    doc_id: str
    model: str
    prompt_versions: dict[str, str]
    generation_settings: dict[str, Any]
    raw_proposer_response: str
    parsed_proposals: list[dict[str, Any]]
    alignment_results: list[dict[str, Any]]
    raw_verifier_response: str
    verifier_decisions: list[dict[str, Any]]
    final_accepted_candidates: list[dict[str, Any]]
    diagnostics: dict[str, Any] = field(default_factory=dict)
    repair_used: bool = False
    parse_failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentLLMCacheRecord":
        return cls(
            document_sha256=str(data["document_sha256"]),
            doc_id=str(data.get("doc_id", "")),
            model=str(data.get("model", DEFAULT_MODEL)),
            prompt_versions=dict(data.get("prompt_versions") or {}),
            generation_settings=dict(data.get("generation_settings") or {}),
            raw_proposer_response=str(data.get("raw_proposer_response", "")),
            parsed_proposals=list(data.get("parsed_proposals") or []),
            alignment_results=list(data.get("alignment_results") or []),
            raw_verifier_response=str(data.get("raw_verifier_response", "")),
            verifier_decisions=list(data.get("verifier_decisions") or []),
            final_accepted_candidates=list(data.get("final_accepted_candidates") or []),
            diagnostics=dict(data.get("diagnostics") or {}),
            repair_used=bool(data.get("repair_used", False)),
            parse_failures=list(data.get("parse_failures") or []),
        )
