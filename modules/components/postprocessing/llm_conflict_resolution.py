"""Deterministic LLM↔v7 overlap conflict classifiers for v10.

Reuses the v9 LLM cache (`final_accepted_candidates`) but only proposes
one-to-one span/type replacements — never free-form additive recall.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Optional

from modules.components.postprocessing.llm_recall import spans_overlap
from modules.core.constants import (
    TARGET_LABEL_DIAGNOSIS,
    TARGET_LABEL_DRUG,
    TARGET_LABEL_SYMPTOM,
)
from modules.core.schemas import FinalEntity

Category = Literal["A", "B", "C", "D"]

NEGATION_CUES = frozenset({"không", "chưa", "chua"})
ALLOWED_REPLACEMENT_TYPES = frozenset(
    {TARGET_LABEL_DIAGNOSIS, TARGET_LABEL_DRUG, TARGET_LABEL_SYMPTOM}
)

# Trailing junk glued to drug names / punctuation / connectors.
_TRAILING_PUNCT_RE = re.compile(r"^[\s\.\,\;\:\!\?\-\*\)]+$")
_GLUED_TOKEN_RE = re.compile(r"^[A-Za-zÀ-ỹà-ỹ0-9]+$")
_THUOC_PREFIX_RE = re.compile(r"(?i)^thu[oố]c\s*i?\s*$")
_DOSAGE_HINT_RE = re.compile(
    r"(?i)(\d+\s*(mg|mcg|g|ml|viên|ống|gói)|sau\s+ăn|uống|tiêm)"
)
_LEADING_JUNK_RE = re.compile(r"(?i)^(vì|dõi|ho\s*)$")

# Category C: reject explanatory / dump expansions.
_C_BAD_SUBSTRINGS = (
    " vì ",
    " do ",
    " nên ",
    " khiến ",
    " gây ra ",
    " kể từ ",
    "không đặc hiệu",
    "ngày càng",
)


@dataclass(frozen=True)
class OverlapHit:
    """One LLM candidate vs one overlapping frozen v7 entity."""

    llm_text: str
    llm_type: str
    llm_start: int
    llm_end: int
    v7_index: int
    v7_text: str
    v7_type: str
    v7_start: int
    v7_end: int


@dataclass(frozen=True)
class ReplacementDecision:
    category: Category
    hit: OverlapHit
    reason: str


def find_overlapping_v7(
    llm_start: int,
    llm_end: int,
    frozen_v7: list[FinalEntity],
) -> list[tuple[int, FinalEntity]]:
    hits: list[tuple[int, FinalEntity]] = []
    for idx, entity in enumerate(frozen_v7):
        if entity.span.start is None or entity.span.end is None:
            continue
        if spans_overlap(llm_start, llm_end, int(entity.span.start), int(entity.span.end)):
            hits.append((idx, entity))
    return hits


def _leftover_parts(
    llm_start: int,
    llm_end: int,
    v7_start: int,
    v7_end: int,
    v7_text: str,
) -> tuple[str, str]:
    """Prefix/suffix of v7 relative to an inner LLM span (offsets in original)."""
    rel_start = llm_start - v7_start
    rel_end = llm_end - v7_start
    return v7_text[:rel_start], v7_text[rel_end:]


def _is_junk_drug_leftover(prefix: str, suffix: str) -> bool:
    leftover = prefix + suffix
    if not leftover:
        return False
    if _DOSAGE_HINT_RE.search(leftover):
        return False
    if _TRAILING_PUNCT_RE.fullmatch(leftover):
        return True
    stripped = leftover.strip()
    if stripped and " " not in stripped and _GLUED_TOKEN_RE.fullmatch(stripped):
        return True
    if _THUOC_PREFIX_RE.fullmatch(prefix) and not suffix.strip():
        return True
    if not prefix.strip() and suffix.strip().lower() in {"để", "de"}:
        return True
    return False


def classify_one_to_one(hit: OverlapHit) -> Optional[ReplacementDecision]:
    """Return a category if this exact 1:1 overlap is a high-confidence replacement."""
    ls, le = hit.llm_start, hit.llm_end
    es, ee = hit.v7_start, hit.v7_end
    llm_text, v7_text = hit.llm_text, hit.v7_text
    llm_type, v7_type = hit.llm_type, hit.v7_type

    if llm_type not in ALLOWED_REPLACEMENT_TYPES:
        return None

    llm_inside = ls >= es and le <= ee and (ls > es or le < ee)
    v7_inside = es >= ls and ee <= le and (es > ls or ee < le)

    # --- A: junk attached to drug names (LLM ⊂ v7) ---
    if (
        llm_inside
        and llm_type == TARGET_LABEL_DRUG
        and v7_type == TARGET_LABEL_DRUG
    ):
        # Confirm slice equality inside v7 text.
        rel_s, rel_e = ls - es, le - es
        if v7_text[rel_s:rel_e] != llm_text:
            return None
        prefix, suffix = _leftover_parts(ls, le, es, ee, v7_text)
        if _is_junk_drug_leftover(prefix, suffix):
            return ReplacementDecision(
                category="A",
                hit=hit,
                reason="drug_junk_boundary",
            )

    # --- B: leading negation cue inside v7 span ---
    if llm_inside and llm_type in {
        TARGET_LABEL_SYMPTOM,
        TARGET_LABEL_DIAGNOSIS,
    }:
        rel_s, rel_e = ls - es, le - es
        if v7_text[rel_s:rel_e] != llm_text:
            return None
        prefix, suffix = _leftover_parts(ls, le, es, ee, v7_text)
        if not suffix.strip() and prefix.strip().lower() in NEGATION_CUES:
            return ReplacementDecision(
                category="B",
                hit=hit,
                reason="leading_negation_trim",
            )

    # --- C: more complete diagnosis span (v7 ⊂ LLM, same start) ---
    if (
        v7_inside
        and llm_type == TARGET_LABEL_DIAGNOSIS
        and v7_type in {TARGET_LABEL_SYMPTOM, TARGET_LABEL_DIAGNOSIS}
        and ls == es
        and le > ee
    ):
        if not llm_text.startswith(v7_text):
            return None
        if len(llm_text) > 60 or len(llm_text.split()) > 10:
            return None
        # Avoid expanding ultra-short / generic cores.
        if len(v7_text.strip()) < 10 and len(v7_text.split()) < 3:
            return None
        added = llm_text[len(v7_text) :].strip(" ,")
        if not added or len(added.split()) > 5:
            return None
        low = llm_text.lower()
        if any(bad in low for bad in _C_BAD_SUBSTRINGS):
            return None
        if ":" in llm_text or "(" in llm_text or "/" in llm_text:
            return None
        return ReplacementDecision(
            category="C",
            hit=hit,
            reason="diagnosis_span_expand",
        )

    # --- D: type correction with boundary cleanup ---
    if llm_type == TARGET_LABEL_DIAGNOSIS and v7_type == TARGET_LABEL_SYMPTOM:
        # Trailing punctuation only on v7.
        if ls == es and le < ee and v7_text.startswith(llm_text):
            trailing = v7_text[len(llm_text) :]
            if _TRAILING_PUNCT_RE.fullmatch(trailing or ""):
                return ReplacementDecision(
                    category="D",
                    hit=hit,
                    reason="trailing_punct_type_upgrade",
                )
        # Leading glued junk on v7, clinical core matches LLM.
        if llm_inside:
            rel_s, rel_e = ls - es, le - es
            if v7_text[rel_s:rel_e] == llm_text:
                prefix, suffix = _leftover_parts(ls, le, es, ee, v7_text)
                if not suffix.strip() and _LEADING_JUNK_RE.fullmatch(prefix.strip()):
                    return ReplacementDecision(
                        category="D",
                        hit=hit,
                        reason="leading_junk_type_upgrade",
                    )
        # Exact-span type-only flips are deferred: LLM type alone is not enough
        # for first v10 (would flood 100+ replacements). Require boundary evidence.

    return None


def candidate_lexically_consistent(
    span_text: str,
    ent_type: str,
    candidates: list[str],
    diagnosis_names: dict[str, str] | None = None,
    drug_terms_by_rxcui: dict[str, list[str]] | None = None,
) -> bool:
    """Hard gate: non-empty + light lexical agreement with ontology labels."""
    if ent_type == TARGET_LABEL_DIAGNOSIS:
        if not candidates:
            return False
        if not diagnosis_names:
            return True
        span_tokens = _tokenize(span_text)
        if not span_tokens:
            return False
        for code in candidates:
            name = diagnosis_names.get(str(code), "")
            name_tokens = _tokenize(name)
            if not name_tokens:
                continue
            if span_tokens & name_tokens:
                return True
            # Allow when span is a near-substring of the concept name.
            if _norm(span_text) in _norm(name) or _norm(name) in _norm(span_text):
                return True
        return False

    if ent_type == TARGET_LABEL_DRUG:
        if not candidates or len(candidates) != 1:
            return False
        if not drug_terms_by_rxcui:
            return True
        rxcui = str(candidates[0])
        terms = drug_terms_by_rxcui.get(rxcui) or []
        needle = _norm(span_text)
        if not needle:
            return False
        for term in terms:
            t = _norm(term)
            if needle == t or needle in t or t in needle:
                return True
        # Fallback: any term token overlap.
        span_tokens = _tokenize(span_text)
        for term in terms:
            if span_tokens & _tokenize(term):
                return True
        return False

    # Symptoms: no ontology candidate required.
    return True


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[A-Za-zÀ-ỹà-ỹ0-9]+", text.lower()) if len(t) > 1}


def load_diagnosis_name_index(csv_path: Any) -> dict[str, str]:
    import csv
    from pathlib import Path

    path = Path(csv_path)
    out: dict[str, str] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            code = str(row.get("id") or "").strip()
            name = str(row.get("name_vi") or row.get("name_en") or "").strip()
            if code and name:
                out[code] = name
    return out


def load_drug_terms_by_rxcui(csv_path: Any) -> dict[str, list[str]]:
    import csv
    import sys
    from pathlib import Path

    path = Path(csv_path)
    out: dict[str, list[str]] = {}
    if not path.exists():
        return out
    # short_drug.csv has very wide ingredient cells.
    csv.field_size_limit(min(sys.maxsize, 8 * 1024 * 1024))
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rxcui = str(row.get("rxcui") or "").strip()
            term = str(row.get("term") or "").strip()
            if not rxcui:
                continue
            bucket = out.setdefault(rxcui, [])
            if term:
                bucket.append(term)
            # Keep only the first few ingredient fragments for lexical checks.
            ingredients = str(row.get("ingredients") or "")
            if ingredients:
                for part in ingredients.split("|")[:8]:
                    part = part.strip()
                    if part:
                        bucket.append(part)
    return out


def decision_to_dict(decision: ReplacementDecision) -> dict[str, Any]:
    h = decision.hit
    return {
        "category": decision.category,
        "reason": decision.reason,
        "text": h.llm_text,
        "type": h.llm_type,
        "start": h.llm_start,
        "end": h.llm_end,
        "existing_text": h.v7_text,
        "existing_type": h.v7_type,
        "existing_start": h.v7_start,
        "existing_end": h.v7_end,
        "v7_index": h.v7_index,
    }
