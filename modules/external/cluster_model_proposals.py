"""Cluster independent model proposals for judge adjudication."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _overlap_chars(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def _char_iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = _overlap_chars(a, b)
    if inter <= 0:
        return 0.0
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union else 0.0


def _contains(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] <= b[0] and a[1] >= b[1]


def _norm_text(s: str) -> str:
    return " ".join(s.lower().split())


@dataclass
class Proposal:
    proposal_id: str
    document: str
    model: str
    role: str
    text: str
    start: int
    end: int
    type: str
    assertions: list[str]
    confidence: float
    brief_reason: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Cluster:
    cluster_id: str
    document: str
    proposals: list[Proposal]
    agreement_type: str = "SINGLE_MODEL_ONLY"

    @property
    def models(self) -> list[str]:
        return sorted({p.model for p in self.proposals})

    def span_union(self) -> tuple[int, int]:
        return (
            min(p.start for p in self.proposals),
            max(p.end for p in self.proposals),
        )


def classify_agreement(cluster: Cluster) -> str:
    props = cluster.proposals
    if len(props) == 1:
        return "SINGLE_MODEL_ONLY"
    spans = {(p.start, p.end) for p in props}
    types = {p.type for p in props}
    assertions = {tuple(sorted(p.assertions)) for p in props}
    texts = {_norm_text(p.text) for p in props}

    exact_same = len(spans) == 1 and len(types) == 1 and len(assertions) == 1
    if exact_same:
        return "EXACT_AGREEMENT"

    # containment / overlapping different spans → boundary or multi-concept
    sorted_props = sorted(props, key=lambda p: (p.start, -p.end))
    nested = False
    for i, a in enumerate(sorted_props):
        for b in sorted_props[i + 1 :]:
            if _contains((a.start, a.end), (b.start, b.end)) or _contains(
                (b.start, b.end), (a.start, a.end)
            ):
                nested = True
    if nested and len(types) > 1:
        return "MULTIPLE_CONCEPT_SEGMENTATION"
    if len(types) > 1:
        return "TYPE_DISAGREEMENT"
    if len(assertions) > 1:
        return "ASSERTION_DISAGREEMENT"
    if len(spans) > 1 or len(texts) > 1:
        return "BOUNDARY_DISAGREEMENT"
    return "BOUNDARY_DISAGREEMENT"


def _should_merge(a: Proposal, b: Proposal, iou_thresh: float = 0.5) -> bool:
    # Never merge distant repeated mentions of same text
    sa, sb = (a.start, a.end), (b.start, b.end)
    if _overlap_chars(sa, sb) > 0:
        return True
    if _contains(sa, sb) or _contains(sb, sa):
        return True
    if _char_iou(sa, sb) >= iou_thresh:
        return True
    # same normalized text near same position
    if _norm_text(a.text) == _norm_text(b.text) and _norm_text(a.text):
        mid_a = (a.start + a.end) / 2
        mid_b = (b.start + b.end) / 2
        if abs(mid_a - mid_b) <= max(10, 0.5 * max(len(a.text), len(b.text))):
            return True
    return False


def cluster_proposals(
    proposals: list[Proposal],
    document_id: str,
) -> list[Cluster]:
    if not proposals:
        return []
    parent = list(range(len(proposals)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i, a in enumerate(proposals):
        for j in range(i + 1, len(proposals)):
            if _should_merge(a, proposals[j]):
                union(i, j)

    groups: dict[int, list[Proposal]] = {}
    for i, p in enumerate(proposals):
        groups.setdefault(find(i), []).append(p)

    clusters: list[Cluster] = []
    for idx, (_, props) in enumerate(
        sorted(groups.items(), key=lambda kv: min(p.start for p in kv[1]))
    ):
        cid = f"{document_id}::c{idx:04d}"
        c = Cluster(cluster_id=cid, document=document_id, proposals=props)
        c.agreement_type = classify_agreement(c)
        clusters.append(c)
    return clusters


def write_disagreements_tsv(clusters: list[Cluster], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "cluster_id",
                "model",
                "text",
                "start",
                "end",
                "type",
                "assertions",
                "confidence",
                "reason",
                "agreement_type",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        for c in clusters:
            for p in c.proposals:
                writer.writerow(
                    {
                        "file": c.document,
                        "cluster_id": c.cluster_id,
                        "model": p.model,
                        "text": p.text,
                        "start": p.start,
                        "end": p.end,
                        "type": p.type,
                        "assertions": "|".join(p.assertions),
                        "confidence": p.confidence,
                        "reason": p.brief_reason,
                        "agreement_type": c.agreement_type,
                    }
                )


def clusters_to_judge_payload(clusters: list[Cluster]) -> list[dict[str, Any]]:
    out = []
    for c in clusters:
        out.append(
            {
                "cluster_id": c.cluster_id,
                "agreement_type": c.agreement_type,
                "models": c.models,
                "proposals": [
                    {
                        "proposal_id": p.proposal_id,
                        "model": p.model,
                        "role": p.role,
                        "text": p.text,
                        "start": p.start,
                        "end": p.end,
                        "type": p.type,
                        "assertions": p.assertions,
                        "confidence": p.confidence,
                        "brief_reason": p.brief_reason,
                    }
                    for p in c.proposals
                ],
            }
        )
    return out
