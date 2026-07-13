"""Optional large-model judge for risky cases only (shared by both LLM modes)."""

from __future__ import annotations

from modules.external.document_risk import RiskResult, score_document_risk

__all__ = ["RiskResult", "score_document_risk", "should_run_document_judge"]


def should_run_document_judge(
    risk: RiskResult,
    *,
    threshold: int = 3,
) -> bool:
    """Run the expensive document judge only when risk meets threshold."""
    score = int(getattr(risk, "risk_score", getattr(risk, "score", 0)) or 0)
    return score >= threshold
