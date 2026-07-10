from __future__ import annotations

from modules.components.llm.document_lines import LineIndexedDocument
from modules.components.llm.schemas import AlignedProposal, LLMProposal


def _find_exact_occurrences(haystack: str, needle: str) -> list[int]:
    """Return all start offsets of exact substring matches (non-overlapping scan)."""
    if not needle:
        return []
    starts: list[int] = []
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx < 0:
            break
        starts.append(idx)
        start = idx + 1  # allow overlapping occurrences to be detected
    return starts


def align_proposal(
    indexed: LineIndexedDocument,
    proposal: LLMProposal,
    proposal_id: int,
) -> AlignedProposal:
    """Exact deterministic alignment of a proposal to original document offsets.

    Accept only when the proposed text occurs exactly once in the referenced line
    and original_document[start:end] == proposed_text.
    """
    line = indexed.get(proposal.line_id)
    if line is None:
        return AlignedProposal(
            proposal_id=proposal_id,
            line_id=proposal.line_id,
            text=proposal.text,
            type=proposal.type,
            start=-1,
            end=-1,
            status="bad_line",
            detail=f"Unknown line_id {proposal.line_id}",
        )

    occurrences = _find_exact_occurrences(line.text, proposal.text)
    if len(occurrences) == 0:
        return AlignedProposal(
            proposal_id=proposal_id,
            line_id=proposal.line_id,
            text=proposal.text,
            type=proposal.type,
            start=-1,
            end=-1,
            status="zero_match",
            detail="Exact text not found in line",
        )
    if len(occurrences) > 1:
        return AlignedProposal(
            proposal_id=proposal_id,
            line_id=proposal.line_id,
            text=proposal.text,
            type=proposal.type,
            start=-1,
            end=-1,
            status="multiple_match",
            detail=f"Found {len(occurrences)} exact occurrences; rejecting in v9",
        )

    local_start = occurrences[0]
    abs_start = line.start + local_start
    abs_end = abs_start + len(proposal.text)
    recovered = indexed.original_text[abs_start:abs_end]
    if recovered != proposal.text:
        return AlignedProposal(
            proposal_id=proposal_id,
            line_id=proposal.line_id,
            text=proposal.text,
            type=proposal.type,
            start=-1,
            end=-1,
            status="zero_match",
            detail=(
                "Offset recovery mismatch: "
                f"document[{abs_start}:{abs_end}]={recovered!r}"
            ),
        )

    return AlignedProposal(
        proposal_id=proposal_id,
        line_id=proposal.line_id,
        text=proposal.text,
        type=proposal.type,
        start=abs_start,
        end=abs_end,
        status="aligned",
        detail="",
    )


def align_proposals(
    indexed: LineIndexedDocument,
    proposals: list[LLMProposal],
) -> list[AlignedProposal]:
    return [
        align_proposal(indexed, proposal, proposal_id=i)
        for i, proposal in enumerate(proposals)
    ]
