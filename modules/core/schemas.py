from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Span:
    """Character-level span in the original document text."""

    start: Optional[int]
    end: Optional[int]

    @property
    def is_valid(self) -> bool:
        return (
            self.start is not None and self.end is not None and self.start <= self.end
        )

    def as_tuple(self) -> tuple[Optional[int], Optional[int]]:
        return self.start, self.end

    def as_list(self) -> list[int]:
        start = self.start
        end = self.end
        if start is None or end is None or start > end:
            raise ValueError(f"Cannot serialize invalid span: {self}")
        return [int(start), int(end)]

    def extract(self, text: str) -> str:
        start = self.start
        end = self.end
        if start is None or end is None or start > end:
            return ""
        return text[int(start) : int(end)]


@dataclass
class Document:
    """Raw clinical note plus optional metadata used by pipeline components."""

    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityMention:
    """A span-level entity produced by NER or dictionary recall components."""

    text: str
    label: str
    span: Span
    confidence: float = 1.0
    source: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_legacy(
        cls, item: dict[str, Any], source: str = "legacy"
    ) -> "EntityMention":
        start, end = item.get("offset", (None, None))
        return cls(
            text=str(item.get("term", "")),
            label=str(item.get("label", "")),
            span=Span(start, end),
            confidence=float(item.get("confidence", item.get("score", 1.0))),
            source=source,
            metadata={
                k: v for k, v in item.items() if k not in {"term", "label", "offset"}
            },
        )

    def to_legacy(self) -> dict[str, Any]:
        data = dict(self.metadata)
        data.update(
            {"term": self.text, "label": self.label, "offset": self.span.as_tuple()}
        )
        return data


@dataclass
class LinkedCandidate:
    """A candidate ontology mapping for an entity mention."""

    candidate_id: str
    canonical_name: str
    score: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FinalEntity:
    """Final competition-level entity after classification, linking, and assertions."""

    text: str
    type: str
    span: Span
    candidates: list[str] = field(default_factory=list)
    assertions: list[str] = field(default_factory=list)
    confidence: float = 1.0
    source: str = "pipeline"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_legacy(cls, item: dict[str, Any], source: str = "legacy") -> "FinalEntity":
        position = item.get("position", [None, None])
        return cls(
            text=str(item.get("text", "")),
            type=str(item.get("type", "")),
            span=Span(position[0], position[1]),
            candidates=[str(c) for c in item.get("candidates", [])],
            assertions=[str(a) for a in item.get("assertions", [])],
            source=source,
            metadata={
                k: v
                for k, v in item.items()
                if k not in {"text", "type", "position", "candidates", "assertions"}
            },
        )

    def to_submission_dict(
        self, include_empty_candidates: bool = False
    ) -> dict[str, Any]:
        output = {
            "text": self.text,
            "type": self.type,
            "assertions": self.assertions,
            "position": self.span.as_list(),
        }
        if include_empty_candidates or self.candidates:
            output["candidates"] = self.candidates
        return output
