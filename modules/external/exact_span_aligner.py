"""Deterministic exact-span alignment for model proposals.

Never normalizes, translates, or rewrites source text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


AlignmentStatus = Literal[
    "valid_model_offset",
    "realigned_unique",
    "rejected_ambiguous",
    "rejected_not_found",
    "rejected_empty",
]


@dataclass
class AlignmentResult:
    status: AlignmentStatus
    text: str
    start: int | None
    end: int | None
    original_start: int | None = None
    original_end: int | None = None
    reason: str = ""


@dataclass
class AlignmentStats:
    valid_model_offset: int = 0
    realigned_unique: int = 0
    rejected_ambiguous: int = 0
    rejected_not_found: int = 0
    rejected_empty: int = 0

    def bump(self, status: AlignmentStatus) -> None:
        setattr(self, status, getattr(self, status) + 1)

    def as_dict(self) -> dict[str, int]:
        return {
            "valid_model_offset": self.valid_model_offset,
            "realigned_unique": self.realigned_unique,
            "rejected_ambiguous": self.rejected_ambiguous,
            "rejected_not_found": self.rejected_not_found,
            "rejected_empty": self.rejected_empty,
        }


def find_all_occurrences(document: str, text: str) -> list[tuple[int, int]]:
    if not text:
        return []
    out: list[tuple[int, int]] = []
    start = 0
    while True:
        idx = document.find(text, start)
        if idx < 0:
            break
        out.append((idx, idx + len(text)))
        start = idx + 1
    return out


def _score_occurrence(
    document: str,
    start: int,
    end: int,
    left_anchor: str,
    right_anchor: str,
) -> float:
    score = 0.0
    left_ctx = document[max(0, start - 80) : start]
    right_ctx = document[end : min(len(document), end + 80)]
    if left_anchor:
        if left_anchor in left_ctx:
            score += 3.0
            if left_ctx.endswith(left_anchor) or left_anchor == left_ctx[-len(left_anchor) :]:
                score += 2.0
        elif left_anchor.strip() and left_anchor.strip() in left_ctx:
            score += 1.0
    if right_anchor:
        if right_anchor in right_ctx:
            score += 3.0
            if right_ctx.startswith(right_anchor):
                score += 2.0
        elif right_anchor.strip() and right_anchor.strip() in right_ctx:
            score += 1.0
    return score


def align_span(
    document: str,
    text: str,
    start: int | None,
    end: int | None,
    left_anchor: str = "",
    right_anchor: str = "",
) -> AlignmentResult:
    text = text if text is not None else ""
    if not text:
        return AlignmentResult(
            status="rejected_empty",
            text="",
            start=None,
            end=None,
            original_start=start,
            original_end=end,
            reason="empty text",
        )

    if (
        isinstance(start, int)
        and isinstance(end, int)
        and 0 <= start < end <= len(document)
        and document[start:end] == text
    ):
        return AlignmentResult(
            status="valid_model_offset",
            text=text,
            start=start,
            end=end,
            original_start=start,
            original_end=end,
            reason="model offsets exact",
        )

    occs = find_all_occurrences(document, text)
    if not occs:
        return AlignmentResult(
            status="rejected_not_found",
            text=text,
            start=None,
            end=None,
            original_start=start,
            original_end=end,
            reason="text not found in document",
        )

    if len(occs) == 1:
        s, e = occs[0]
        return AlignmentResult(
            status="realigned_unique",
            text=document[s:e],
            start=s,
            end=e,
            original_start=start,
            original_end=end,
            reason="single occurrence",
        )

    # Disambiguate with anchors (+ optional proximity to claimed offsets)
    scored: list[tuple[float, int, int]] = []
    for s, e in occs:
        sc = _score_occurrence(document, s, e, left_anchor or "", right_anchor or "")
        if isinstance(start, int):
            sc -= abs(s - start) * 0.001
        scored.append((sc, s, e))
    scored.sort(key=lambda x: (-x[0], x[1]))
    best_score, best_s, best_e = scored[0]
    # Require unique best
    ties = [t for t in scored if abs(t[0] - best_score) < 1e-9]
    if len(ties) != 1 or best_score <= 0:
        return AlignmentResult(
            status="rejected_ambiguous",
            text=text,
            start=None,
            end=None,
            original_start=start,
            original_end=end,
            reason=f"ambiguous occurrences={len(occs)} best_score={best_score}",
        )
    return AlignmentResult(
        status="realigned_unique",
        text=document[best_s:best_e],
        start=best_s,
        end=best_e,
        original_start=start,
        original_end=end,
        reason=f"anchor-disambiguated score={best_score}",
    )


def align_entities(
    document: str,
    entities: list[dict[str, Any]],
    stats: AlignmentStats | None = None,
) -> tuple[list[dict[str, Any]], AlignmentStats]:
    stats = stats or AlignmentStats()
    aligned: list[dict[str, Any]] = []
    for ent in entities:
        result = align_span(
            document,
            str(ent.get("text") or ""),
            ent.get("start"),
            ent.get("end"),
            str(ent.get("left_anchor") or ""),
            str(ent.get("right_anchor") or ""),
        )
        stats.bump(result.status)
        if result.start is None or result.end is None:
            continue
        # Final text must be exact document slice
        final_text = document[result.start : result.end]
        out = dict(ent)
        out["text"] = final_text
        out["start"] = result.start
        out["end"] = result.end
        out["alignment_status"] = result.status
        out["alignment_reason"] = result.reason
        aligned.append(out)
    return aligned, stats
