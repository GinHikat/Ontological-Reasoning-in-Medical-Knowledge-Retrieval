"""Exact-span alignment shared by LLM (and future NER) extractors."""

from __future__ import annotations

from typing import Any

from modules.external.exact_span_aligner import AlignmentStats, align_entities

__all__ = ["AlignmentStats", "align_entities"]


def require_exact_substring(text: str, span_text: str, start: int, end: int) -> bool:
    """Return True iff ``text[start:end] == span_text`` (exact competition offset)."""
    if start < 0 or end > len(text) or start >= end:
        return False
    return text[start:end] == span_text
