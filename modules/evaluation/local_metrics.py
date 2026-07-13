"""Local comparison helpers (entity overlap proxies — not official leaderboard)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _key(ent: dict[str, Any]) -> tuple:
    pos = ent.get("position") or [None, None]
    return (ent.get("type"), ent.get("text"), pos[0], pos[1])


def load_submission(dir_path: Path) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(dir_path.glob("*.json")):
        out[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return out


def exact_entity_overlap(
    a: dict[str, list[dict[str, Any]]],
    b: dict[str, list[dict[str, Any]]],
) -> dict[str, float]:
    """Micro-averaged exact (type, text, position) Jaccard-style overlap."""
    docs = sorted(set(a) & set(b))
    inter = union = 0
    for doc in docs:
        sa = {_key(e) for e in a[doc]}
        sb = {_key(e) for e in b[doc]}
        inter += len(sa & sb)
        union += len(sa | sb)
    return {
        "docs_compared": float(len(docs)),
        "exact_intersection": float(inter),
        "exact_union": float(union),
        "jaccard": (inter / union) if union else 0.0,
    }
