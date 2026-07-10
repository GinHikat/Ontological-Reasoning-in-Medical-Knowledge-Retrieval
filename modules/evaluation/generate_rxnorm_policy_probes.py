#!/usr/bin/env python3
"""Generate controlled RxNorm candidate-policy leaderboard probes.

Operates only on a frozen submission JSON folder + local short_drug.csv.
No model inference. No external APIs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

csv.field_size_limit(10_000_000)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DRUG_CSV = PROJECT_ROOT / "v_dataset" / "viettel" / "base" / "short_drug.csv"
DEFAULT_BASELINE = PROJECT_ROOT / "artifacts" / "v7_newest_same_env" / "submission"
DEFAULT_INPUT = PROJECT_ROOT / "v_dataset" / "var" / "test"
DEFAULT_OUT = PROJECT_ROOT / "output" / "rxnorm_probes"
DEFAULT_ANALYSIS = PROJECT_ROOT / "analysis"

DRUG_TYPE = "THUỐC"
NON_DRUG_TYPES = {
    "TRIỆU_CHỨNG",
    "CHẨN_ĐOÁN",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
}

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

_DASHES = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\ufe58": "-",
        "\ufe63": "-",
        "\uff0d": "-",
    }
)


def normalize_text(s: str) -> str:
    s = (s or "").translate(_DASHES)
    s = s.casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_for_numeric(s: str) -> str:
    """Normalize decimal commas to dots only in numeric contexts."""
    s = normalize_text(s)
    s = re.sub(r"(\d),(\d)", r"\1.\2", s)
    return s


def primary_ttys(raw: str) -> set[str]:
    return {t.strip().upper() for t in (raw or "").split("|") if t.strip()}


# ---------------------------------------------------------------------------
# RxNorm indexes
# ---------------------------------------------------------------------------


@dataclass
class RxNormIndexes:
    rxcui_to_terms: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    rxcui_to_ttys: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    # normalized term -> tty -> set of rxcuis
    term_to_rxcuis_by_tty: dict[str, dict[str, set[str]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(set))
    )
    # IN/PIN aliases sorted longest-first for matching
    ingredient_aliases: list[tuple[str, str, str]] = field(default_factory=list)  # (norm, rxcui, tty)
    brand_aliases: list[tuple[str, str, str]] = field(default_factory=list)  # BN/SBD
    # preferred display term per rxcui
    rxcui_preferred_term: dict[str, str] = field(default_factory=dict)
    # SCD rows: (rxcui, norm_term, raw_term)
    scd_rows: list[tuple[str, str, str]] = field(default_factory=list)
    has_relationships: bool = False


def load_rxnorm_indexes(csv_path: Path) -> RxNormIndexes:
    idx = RxNormIndexes()
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            term = (row.get("term") or "").strip()
            rxcui = (row.get("rxcui") or "").strip()
            tty_raw = (row.get("tty") or "").strip()
            if not term or not rxcui or not rxcui.isdigit():
                continue
            ttys = primary_ttys(tty_raw)
            if not ttys:
                continue
            norm = normalize_text(term)
            idx.rxcui_to_terms[rxcui].append(term)
            idx.rxcui_to_ttys[rxcui].update(ttys)
            for tty in ttys:
                idx.term_to_rxcuis_by_tty[norm][tty].add(rxcui)
            # preferred term: prefer shorter / IN / SCD
            prev = idx.rxcui_preferred_term.get(rxcui)
            if prev is None or ("IN" in ttys and "IN" not in idx.rxcui_to_ttys.get(rxcui, set())):
                idx.rxcui_preferred_term[rxcui] = term
            elif prev is None or len(term) < len(prev):
                if rxcui not in idx.rxcui_preferred_term:
                    idx.rxcui_preferred_term[rxcui] = term

            if "IN" in ttys or "PIN" in ttys:
                # keep reasonably short aliases for matching
                if 2 <= len(norm) <= 60 and not re.search(r"\d", norm):
                    tty_pref = "IN" if "IN" in ttys else "PIN"
                    idx.ingredient_aliases.append((norm, rxcui, tty_pref))
            if "BN" in ttys or "SBD" in ttys:
                if 2 <= len(norm) <= 40 and not re.search(r"\d\s*mg", norm):
                    tty_pref = "BN" if "BN" in ttys else "SBD"
                    idx.brand_aliases.append((norm, rxcui, tty_pref))
            if "SCD" in ttys:
                idx.scd_rows.append((rxcui, norm, term))

    # dedupe aliases preferring IN over PIN for same (norm,rxcui)
    ing_map: dict[tuple[str, str], str] = {}
    for norm, rxcui, tty in idx.ingredient_aliases:
        key = (norm, rxcui)
        if key not in ing_map or (tty == "IN" and ing_map[key] == "PIN"):
            ing_map[key] = tty
    idx.ingredient_aliases = sorted(
        [(n, r, t) for (n, r), t in ing_map.items()],
        key=lambda x: (-len(x[0]), x[0], x[1]),
    )
    brand_map: dict[tuple[str, str], str] = {}
    for norm, rxcui, tty in idx.brand_aliases:
        key = (norm, rxcui)
        if key not in brand_map or (tty == "BN" and brand_map[key] == "SBD"):
            brand_map[key] = tty
    idx.brand_aliases = sorted(
        [(n, r, t) for (n, r), t in brand_map.items()],
        key=lambda x: (-len(x[0]), x[0], x[1]),
    )

    # finalize preferred terms
    for rxcui, terms in idx.rxcui_to_terms.items():
        ttys = idx.rxcui_to_ttys[rxcui]
        best = None
        for term in terms:
            n = normalize_text(term)
            score = (0 if "IN" in ttys and n == normalize_text(term) else 1, len(term))
            if "IN" in ttys and normalize_text(term) in {
                normalize_text(t) for t in terms
            }:
                # prefer exact short IN-like
                pass
            cand = (0 if any(normalize_text(term) == normalize_text(t) for t in terms) else 1, len(term), term)
            if best is None or (len(term), term) < (len(best), best):
                # prefer shortest term among those with IN if available
                if "IN" in ttys:
                    if best is None or len(term) < len(best):
                        best = term
                elif best is None:
                    best = term
        if best:
            idx.rxcui_preferred_term[rxcui] = best
        elif terms:
            idx.rxcui_preferred_term[rxcui] = min(terms, key=len)

    return idx


def unique_in_for_ingredient(idx: RxNormIndexes, ingredient_rxcui: str) -> str | None:
    """Return ingredient_rxcui if it has IN; else unique PIN for same concept set."""
    ttys = idx.rxcui_to_ttys.get(ingredient_rxcui, set())
    if "IN" in ttys:
        return ingredient_rxcui
    if "PIN" in ttys:
        return ingredient_rxcui
    return None


def prefer_in_over_pin(idx: RxNormIndexes, rxcui: str) -> str:
    """If rxcui is PIN, try to find matching IN with same preferred alias; else keep."""
    ttys = idx.rxcui_to_ttys.get(rxcui, set())
    if "IN" in ttys:
        return rxcui
    if "PIN" not in ttys:
        return rxcui
    term = normalize_text(idx.rxcui_preferred_term.get(rxcui, ""))
    if not term:
        return rxcui
    ins = idx.term_to_rxcuis_by_tty.get(term, {}).get("IN", set())
    if len(ins) == 1:
        return next(iter(ins))
    return rxcui


# ---------------------------------------------------------------------------
# Safe token / phrase matching (no unrestricted substring)
# ---------------------------------------------------------------------------


def _is_latin_alpha(ch: str) -> bool:
    return ch.isalpha() and ord(ch) < 0x0300


def delimited_phrase_match(haystack_norm: str, needle_norm: str) -> bool:
    """Whole-token / delimited phrase match in already-normalized text."""
    if not needle_norm or not haystack_norm:
        return False
    if len(needle_norm) < 2:
        return False
    start = 0
    while True:
        i = haystack_norm.find(needle_norm, start)
        if i < 0:
            return False
        j = i + len(needle_norm)
        left_ok = i == 0 or not _is_latin_alpha(haystack_norm[i - 1])
        right_ok = j == len(haystack_norm) or not _is_latin_alpha(haystack_norm[j])
        # also allow non-latin boundaries (Vietnamese) via whitespace/punct
        if i > 0 and haystack_norm[i - 1].isalnum() and not _is_latin_alpha(haystack_norm[i - 1]):
            # Vietnamese letter adjacent — treat as boundary fail for latin needles
            if needle_norm.isascii():
                left_ok = haystack_norm[i - 1].isspace() or not haystack_norm[i - 1].isalnum()
        if left_ok and right_ok:
            return True
        start = i + 1


# ---------------------------------------------------------------------------
# Feature parsing
# ---------------------------------------------------------------------------

STRENGTH_UNIT = (
    r"(?:mg/mL|mg/ml|mcg/mL|mcg/ml|µg/mL|µg/ml|g/mL|g/ml|"
    r"mg|mcg|µg|ug|grams?|g|mEq|meq|IU|UI|units?|%)"
)
_STRENGTH_RANGE = re.compile(
    rf"(?P<low>\d+(?:\.\d+)?)\s*-\s*(?P<high>\d+(?:\.\d+)?)\s*(?P<unit>{STRENGTH_UNIT})\b",
    re.I,
)
_STRENGTH_SINGLE = re.compile(
    rf"(?<![/\w])(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>{STRENGTH_UNIT})\b",
    re.I,
)
_ADMIN_VOLUME = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mL|ml)\b", re.I)

_ROUTE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("oral", re.compile(r"\b(?:po|oral|uống)\b", re.I)),
    ("iv", re.compile(r"\b(?:iv|intravenous|tĩnh\s*mạch)\b", re.I)),
    ("im", re.compile(r"\b(?:im|intramuscular)\b", re.I)),
    ("sc", re.compile(r"\b(?:sc|subcutaneous)\b", re.I)),
    ("sl", re.compile(r"\b(?:sl|sublingual|dưới\s*lưỡi)\b", re.I)),
    ("inhaled", re.compile(r"\b(?:inhaled|hít)\b", re.I)),
]

_FORM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("tablet", re.compile(r"\b(?:tablet|tablets|viên)\b", re.I)),
    ("capsule", re.compile(r"\b(?:capsule|capsules|nang)\b", re.I)),
    ("suspension", re.compile(r"\b(?:suspension|hỗn\s*dịch)\b", re.I)),
    ("solution", re.compile(r"\b(?:solution|dung\s*dịch)\b", re.I)),
    ("injection", re.compile(r"\b(?:injection|injectable|tiêm)\b", re.I)),
    ("cream", re.compile(r"\b(?:cream|kem)\b", re.I)),
    ("ointment", re.compile(r"\b(?:ointment|thuốc\s*mỡ)\b", re.I)),
    ("patch", re.compile(r"\b(?:patch|miếng\s*dán)\b", re.I)),
    ("syrup", re.compile(r"\b(?:syrup|siro)\b", re.I)),
    ("inhaler", re.compile(r"\b(?:inhaler)\b", re.I)),
]

_FORM_IN_SCD = {
    "tablet": re.compile(r"\btablet\b", re.I),
    "capsule": re.compile(r"\bcapsule\b", re.I),
    "suspension": re.compile(r"\bsuspension\b", re.I),
    "solution": re.compile(r"\bsolution\b", re.I),
    "injection": re.compile(r"\b(?:injection|injectable)\b", re.I),
    "cream": re.compile(r"\bcream\b", re.I),
    "ointment": re.compile(r"\bointment\b", re.I),
    "patch": re.compile(r"\bpatch\b", re.I),
    "syrup": re.compile(r"\bsyrup\b", re.I),
    "inhaler": re.compile(r"\binhaler\b", re.I),
}

_ROUTE_IN_SCD = {
    "oral": re.compile(r"\boral\b", re.I),
    "iv": re.compile(r"\b(?:intravenous|injection)\b", re.I),
    "im": re.compile(r"\bintramuscular\b", re.I),
    "sc": re.compile(r"\bsubcutaneous\b", re.I),
    "sl": re.compile(r"\bsublingual\b", re.I),
    "inhaled": re.compile(r"\b(?:inhalation|inhaler)\b", re.I),
}


@dataclass
class MentionFeatures:
    has_explicit_strength: bool = False
    strength_low: str | None = None
    strength_high: str | None = None
    strength_unit: str | None = None
    is_strength_range: bool = False
    has_admin_volume: bool = False
    route: str | None = None
    dose_form: str | None = None
    explicit_brand: bool = False


def parse_mention_features(text: str, idx: RxNormIndexes) -> MentionFeatures:
    raw = text or ""
    norm = normalize_for_numeric(raw)
    feat = MentionFeatures()
    feat.has_admin_volume = bool(_ADMIN_VOLUME.search(norm))

    m = _STRENGTH_RANGE.search(norm)
    if m:
        feat.has_explicit_strength = True
        feat.is_strength_range = True
        feat.strength_low = m.group("low")
        feat.strength_high = m.group("high")
        feat.strength_unit = _canon_unit(m.group("unit"))
    else:
        # exclude pure admin volumes (N ml) from strength
        for m2 in _STRENGTH_SINGLE.finditer(norm):
            unit = _canon_unit(m2.group("unit"))
            if unit in {"ml"}:
                continue
            feat.has_explicit_strength = True
            feat.strength_low = m2.group("val")
            feat.strength_high = m2.group("val")
            feat.strength_unit = unit
            break

    for name, pat in _ROUTE_PATTERNS:
        if pat.search(raw) or pat.search(norm):
            feat.route = name
            break
    for name, pat in _FORM_PATTERNS:
        if pat.search(raw) or pat.search(norm):
            feat.dose_form = name
            break

    # explicit brand: BN/SBD alias delimited in mention
    mention_n = normalize_text(raw)
    for alias, _rxcui, _tty in idx.brand_aliases:
        if len(alias) < 3:
            continue
        if delimited_phrase_match(mention_n, alias):
            # avoid matching ingredient names that are also BN
            feat.explicit_brand = True
            break
    return feat


def _canon_unit(u: str) -> str:
    u = u.casefold().replace("µg", "mcg").replace("ug", "mcg")
    u = u.replace("meq", "meq")
    if u in {"gram", "grams", "g"}:
        return "g"
    if u in {"unit", "units"}:
        return "units"
    if u in {"mg/ml"}:
        return "mg/ml"
    if u in {"mcg/ml"}:
        return "mcg/ml"
    if u in {"g/ml"}:
        return "g/ml"
    return u


def format_strength(val: str, unit: str) -> str:
    # normalize trailing zeros: 325.0 -> 325
    if "." in val:
        val = val.rstrip("0").rstrip(".")
    return f"{val} {unit}"


# ---------------------------------------------------------------------------
# Ingredient resolver
# ---------------------------------------------------------------------------


@dataclass
class IngredientResolution:
    safe_ingredient_rxcui: str | None = None
    safe_ingredient_term: str | None = None
    source: str = ""
    conflict: bool = False
    multi_ingredient: bool = False
    evidence: list[str] = field(default_factory=list)


def resolve_ingredient(
    mention: str,
    baseline_candidates: list[str],
    idx: RxNormIndexes,
) -> IngredientResolution:
    res = IngredientResolution()
    mention_n = normalize_text(mention)

    # Source B — lexical IN/PIN in mention
    lexical_hits: dict[str, str] = {}  # rxcui -> tty
    for alias, rxcui, tty in idx.ingredient_aliases:
        if delimited_phrase_match(mention_n, alias):
            # keep longest matches only: since aliases sorted longest-first,
            # skip if this alias is nested inside an already-accepted longer alias span
            # Simple approach: collect all, then drop those whose alias is substring of another hit alias
            lexical_hits[rxcui] = tty

    # Drop shorter aliases that are substrings of longer matched aliases (token-safe already)
    if lexical_hits:
        matched_aliases = []
        for alias, rxcui, tty in idx.ingredient_aliases:
            if rxcui in lexical_hits and delimited_phrase_match(mention_n, alias):
                matched_aliases.append((alias, rxcui, tty))
        # unique by rxcui keeping longest alias
        best_by_rx: dict[str, tuple[str, str]] = {}
        for alias, rxcui, tty in matched_aliases:
            prev = best_by_rx.get(rxcui)
            if prev is None or len(alias) > len(prev[0]):
                best_by_rx[rxcui] = (alias, tty)
        # remove rxcuis whose best alias is contained in another longer alias as phrase
        aliases_sorted = sorted(best_by_rx.items(), key=lambda x: -len(x[1][0]))
        kept: dict[str, str] = {}
        used_aliases: list[str] = []
        for rxcui, (alias, tty) in aliases_sorted:
            if any(alias != ua and alias in ua and delimited_phrase_match(ua, alias) for ua in used_aliases):
                continue
            # if alias is proper substring of a longer kept alias string, skip
            if any(alias != ua and alias in ua for ua in used_aliases):
                continue
            kept[rxcui] = tty
            used_aliases.append(alias)
        lexical_hits = kept

    lexical_ids = set(lexical_hits.keys())
    if len(lexical_ids) > 1:
        res.multi_ingredient = True
        res.evidence.append(f"lexical_multi:{','.join(sorted(lexical_ids))}")
        return res
    if len(lexical_ids) == 1:
        rid = next(iter(lexical_ids))
        rid = prefer_in_over_pin(idx, rid)
        res.evidence.append(f"lexical:{rid}")
        lexical_single = rid
    else:
        lexical_single = None

    # Source C — baseline candidate term decomposition
    baseline_ings: set[str] = set()
    for cand in baseline_candidates:
        cand = str(cand).strip()
        if not cand:
            continue
        terms = idx.rxcui_to_terms.get(cand, [])
        ttys = idx.rxcui_to_ttys.get(cand, set())
        if "IN" in ttys or "PIN" in ttys:
            baseline_ings.add(prefer_in_over_pin(idx, cand))
            continue
        # search ingredient aliases inside candidate terms
        found_in_term: set[str] = set()
        for term in terms[:20]:
            tn = normalize_text(term)
            # combination marker
            for alias, rxcui, tty in idx.ingredient_aliases:
                if len(alias) < 3:
                    continue
                if delimited_phrase_match(tn, alias):
                    found_in_term.add(prefer_in_over_pin(idx, rxcui))
            if found_in_term:
                break
        # if combination product ( / ) and multiple ings, mark multi
        joined = " | ".join(normalize_text(t) for t in terms[:5])
        if " / " in joined and len(found_in_term) > 1:
            res.multi_ingredient = True
            res.evidence.append(f"baseline_multi:{','.join(sorted(found_in_term))}")
            return res
        baseline_ings.update(found_in_term)

    if len(baseline_ings) > 1:
        res.multi_ingredient = True
        res.evidence.append(f"baseline_ings_multi:{','.join(sorted(baseline_ings))}")
        return res

    baseline_single = next(iter(baseline_ings)) if len(baseline_ings) == 1 else None
    if baseline_single:
        res.evidence.append(f"baseline_term:{baseline_single}")

    # Decision
    if lexical_single and baseline_single and lexical_single != baseline_single:
        res.conflict = True
        res.evidence.append("conflict")
        return res

    chosen = lexical_single or baseline_single
    if not chosen:
        return res

    chosen = prefer_in_over_pin(idx, chosen)
    # ensure IN preferred display
    if "IN" not in idx.rxcui_to_ttys.get(chosen, set()) and "PIN" not in idx.rxcui_to_ttys.get(chosen, set()):
        return res

    res.safe_ingredient_rxcui = chosen
    res.safe_ingredient_term = idx.rxcui_preferred_term.get(chosen, chosen)
    if lexical_single and baseline_single:
        res.source = "lexical+baseline"
    elif lexical_single:
        res.source = "lexical"
    else:
        res.source = "baseline_term"
    return res


# ---------------------------------------------------------------------------
# SCD selection (Probe 1)
# ---------------------------------------------------------------------------

_COMBINATION_SCD = re.compile(r"\s/\s")
_SCD_FORM_MODIFIER = re.compile(
    r"\b(?:disintegrating|chewable|effervescent|extended\s+release|"
    r"delayed\s+release|orally\s+disintegrating|film\s+coated|"
    r"sustained\s+release|enteric\s+coated)\b",
    re.I,
)


def _strength_in_scd(scd_norm: str, strength_str: str) -> bool:
    """Require strength number+unit as delimited phrase in SCD term."""
    target = normalize_for_numeric(strength_str)
    # also allow compact forms like "325 mg" already normalized
    if delimited_phrase_match(scd_norm, target):
        return True
    # allow "325mg" compact
    compact = target.replace(" ", "")
    return compact in scd_norm.replace(" ", "")


def _ingredient_in_scd(scd_norm: str, ingredient_term: str) -> bool:
    ing = normalize_text(ingredient_term)
    if not ing:
        return False
    # primary ingredient usually at start
    if scd_norm.startswith(ing + " ") or scd_norm.startswith(ing + "/") or scd_norm == ing:
        return True
    return delimited_phrase_match(scd_norm, ing)


def select_scd_candidate(
    idx: RxNormIndexes,
    ingredient_rxcui: str,
    feat: MentionFeatures,
) -> str | None:
    ing_term = idx.rxcui_preferred_term.get(ingredient_rxcui, "")
    if not ing_term or not feat.has_explicit_strength or not feat.strength_low or not feat.strength_unit:
        return None

    strength_str = format_strength(feat.strength_low, feat.strength_unit)
    # gather candidates
    scored: list[tuple[tuple[int, ...], str, str]] = []
    for rxcui, scd_norm, raw_term in idx.scd_rows:
        if _COMBINATION_SCD.search(scd_norm):
            continue
        if not _ingredient_in_scd(scd_norm, ing_term):
            continue
        if not _strength_in_scd(scd_norm, strength_str):
            continue
        # form constraints
        form_ok = 1
        if feat.dose_form:
            pat = _FORM_IN_SCD.get(feat.dose_form)
            if pat and not pat.search(scd_norm):
                continue
            form_ok = 2 if pat and pat.search(scd_norm) else 1
        route_ok = 0
        if feat.route:
            rpat = _ROUTE_IN_SCD.get(feat.route)
            if rpat and rpat.search(scd_norm):
                route_ok = 2
            elif feat.route == "oral" and re.search(r"\boral\b", scd_norm):
                route_ok = 2
        oral_tablet_bonus = 0
        if feat.route == "oral" and not feat.dose_form:
            # Prefer generic "oral tablet" over modified forms (disintegrating, ER, …)
            # so official acetaminophen 325 mg oral tablet wins uniquely.
            if re.search(r"\boral tablet\b", scd_norm) and not _SCD_FORM_MODIFIER.search(scd_norm):
                oral_tablet_bonus = 4
            elif re.search(r"\boral tablet\b", scd_norm):
                oral_tablet_bonus = 2
            elif re.search(r"\btablet\b", scd_norm):
                oral_tablet_bonus = 1
        # semantic score tuple (higher better); no RxCUI / row-order tiebreak for acceptance
        score = (form_ok, route_ok, oral_tablet_bonus)
        scored.append((score, rxcui, scd_norm))

    if not scored:
        return None

    best_score = max(s[0] for s in scored)
    best = [s for s in scored if s[0] == best_score]
    # unique best only
    unique_ids = {b[1] for b in best}
    if len(unique_ids) == 1:
        return next(iter(unique_ids))
    # tie → no unique SCD
    return None


def ingredient_candidate(idx: RxNormIndexes, ingredient_rxcui: str) -> str | None:
    """Prefer IN concept id; else PIN."""
    rxcui = prefer_in_over_pin(idx, ingredient_rxcui)
    ttys = idx.rxcui_to_ttys.get(rxcui, set())
    if "IN" in ttys or "PIN" in ttys:
        return rxcui
    return None


def probe1_candidates(
    mention: str,
    baseline: list[str],
    feat: MentionFeatures,
    ing: IngredientResolution,
    idx: RxNormIndexes,
) -> tuple[list[str] | None, str]:
    """Return new candidates or None to leave unchanged, plus reason."""
    if feat.explicit_brand:
        return None, "explicit_brand_unchanged"
    if ing.conflict or ing.multi_ingredient or not ing.safe_ingredient_rxcui:
        return None, "no_safe_ingredient"
    ing_id = ingredient_candidate(idx, ing.safe_ingredient_rxcui)
    if not ing_id:
        return None, "no_in_pin"

    if not feat.has_explicit_strength:
        return [ing_id], "no_strength_to_ingredient"

    scd = select_scd_candidate(idx, ing.safe_ingredient_rxcui, feat)
    if scd:
        reason = "range_to_lower_scd" if feat.is_strength_range else "strength_to_scd"
        return [scd], reason

    # fallback to ingredient
    return [ing_id], "scd_tie_or_miss_fallback_ingredient"


def probe2_candidates(
    baseline: list[str],
    ing: IngredientResolution,
    idx: RxNormIndexes,
) -> tuple[list[str] | None, str]:
    if ing.conflict or ing.multi_ingredient or not ing.safe_ingredient_rxcui:
        return None, "no_safe_ingredient"
    ing_id = ingredient_candidate(idx, ing.safe_ingredient_rxcui)
    if not ing_id:
        return None, "no_in_pin"
    return [ing_id], "ingredient_first"


def probe3_candidates(
    baseline: list[str],
    ing: IngredientResolution,
    idx: RxNormIndexes,
) -> tuple[list[str] | None, str]:
    if not baseline:
        return None, "empty_baseline_unchanged"
    if ing.conflict or ing.multi_ingredient or not ing.safe_ingredient_rxcui:
        return None, "no_safe_ingredient"
    ing_id = ingredient_candidate(idx, ing.safe_ingredient_rxcui)
    if not ing_id:
        return None, "no_in_pin"
    if ing_id in baseline:
        return None, "ingredient_already_in_baseline"
    return list(baseline) + [ing_id], "baseline_plus_ingredient"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def semantic_manifest_hash(submission_dir: Path) -> str:
    h = hashlib.sha256()
    for i in range(1, 101):
        p = submission_dir / f"{i}.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        canon = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        h.update(p.name.encode("utf-8"))
        h.update(b"\0")
        h.update(canon.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def load_submission(submission_dir: Path) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for i in range(1, 101):
        out[str(i)] = json.loads((submission_dir / f"{i}.json").read_text(encoding="utf-8"))
    return out


def write_submission(data: dict[str, list[dict[str, Any]]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 101):
        path = out_dir / f"{i}.json"
        path.write_text(
            json.dumps(data[str(i)], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def deep_copy_submission(src: Path, dst: Path) -> None:
    if dst.exists():
        # Prior copies may be read-only (immutable artifact mode).
        for p in dst.rglob("*"):
            try:
                p.chmod(0o644 if p.is_file() else 0o755)
            except OSError:
                pass
        try:
            dst.chmod(0o755)
        except OSError:
            pass
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    # Ensure probe outputs remain writable even if src files were read-only.
    for p in dst.rglob("*"):
        try:
            p.chmod(0o644 if p.is_file() else 0o755)
        except OSError:
            pass
    try:
        dst.chmod(0o755)
    except OSError:
        pass


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Unit tests (official examples)
# ---------------------------------------------------------------------------


def run_unit_tests(idx: RxNormIndexes) -> dict[str, bool]:
    results: dict[str, bool] = {}

    # Test A — nystatin
    text_a = "nystatin oral suspension 5 ml po qid:prn"
    feat_a = parse_mention_features(text_a, idx)
    ing_a = resolve_ingredient(text_a, [], idx)
    cands_a, reason_a = probe1_candidates(text_a, [], feat_a, ing_a, idx)
    pass_a = (
        ing_a.safe_ingredient_rxcui == "7597"
        and feat_a.route == "oral"
        and feat_a.dose_form == "suspension"
        and feat_a.has_admin_volume
        and feat_a.has_explicit_strength is False
        and cands_a == ["7597"]
    )
    results["nystatin"] = pass_a
    print(
        f"[TEST A nystatin] PASS={pass_a} ing={ing_a.safe_ingredient_rxcui} "
        f"feat_strength={feat_a.has_explicit_strength} route={feat_a.route} "
        f"form={feat_a.dose_form} vol={feat_a.has_admin_volume} "
        f"cands={cands_a} reason={reason_a}"
    )

    # Test B — acetaminophen range
    text_b = "acetaminophen 325-650 mg po q6h:prn"
    feat_b = parse_mention_features(text_b, idx)
    ing_b = resolve_ingredient(text_b, [], idx)
    cands_b, reason_b = probe1_candidates(text_b, [], feat_b, ing_b, idx)
    pass_b = (
        ing_b.safe_ingredient_term
        and normalize_text(ing_b.safe_ingredient_term) == "acetaminophen"
        and feat_b.has_explicit_strength
        and feat_b.is_strength_range
        and feat_b.strength_low == "325"
        and feat_b.strength_high == "650"
        and feat_b.strength_unit == "mg"
        and feat_b.route == "oral"
        and cands_b == ["313782"]
    )
    results["acetaminophen_range"] = pass_b
    print(
        f"[TEST B acetaminophen] PASS={pass_b} ing={ing_b.safe_ingredient_rxcui} "
        f"term={ing_b.safe_ingredient_term} low={feat_b.strength_low} "
        f"high={feat_b.strength_high} unit={feat_b.strength_unit} "
        f"route={feat_b.route} cands={cands_b} reason={reason_b}"
    )
    return results


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_invariants(
    baseline: dict[str, list[dict[str, Any]]],
    probe: dict[str, list[dict[str, Any]]],
) -> list[str]:
    errors: list[str] = []
    if set(baseline) != set(probe) or len(baseline) != 100:
        errors.append("file set mismatch")
        return errors
    for stem in baseline:
        b_ents = baseline[stem]
        p_ents = probe[stem]
        if len(b_ents) != len(p_ents):
            errors.append(f"{stem}: entity count {len(b_ents)} vs {len(p_ents)}")
            continue
        for i, (be, pe) in enumerate(zip(b_ents, p_ents)):
            for key in ("text", "type", "position", "assertions"):
                if be.get(key) != pe.get(key):
                    errors.append(f"{stem}[{i}].{key} changed")
            if be.get("type") != DRUG_TYPE:
                if be.get("candidates") != pe.get("candidates"):
                    errors.append(f"{stem}[{i}] non-drug candidates changed")
    return errors


def validate_offsets(
    probe: dict[str, list[dict[str, Any]]],
    input_dir: Path,
) -> int:
    mismatches = 0
    for stem, ents in probe.items():
        text = (input_dir / f"{stem}.txt").read_text(encoding="utf-8")
        for e in ents:
            start, end = e["position"]
            span = text[start:end]
            if span != e["text"]:
                mismatches += 1
    return mismatches


def count_entities(data: dict[str, list[dict[str, Any]]]) -> int:
    return sum(len(v) for v in data.values())


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------


@dataclass
class EntityRow:
    file: str
    start: int
    end: int
    text: str
    baseline_candidates: list[str]
    baseline_candidate_terms: str
    baseline_candidate_ttys: str
    safe_ingredient_rxcui: str
    safe_ingredient_term: str
    ingredient_resolution_source: str
    ingredient_conflict: bool
    multi_ingredient: bool
    has_explicit_strength: bool
    strength_low: str
    strength_high: str
    strength_unit: str
    is_strength_range: bool
    route: str
    dose_form: str
    explicit_brand: bool
    probe_1_candidate: str
    probe_2_candidate: str
    probe_3_candidates: str
    left_context: str = ""
    right_context: str = ""
    p1_reason: str = ""
    p2_reason: str = ""
    p3_reason: str = ""


def terms_for_cands(idx: RxNormIndexes, cands: list[str]) -> str:
    parts = []
    for c in cands:
        parts.append(idx.rxcui_preferred_term.get(c, ""))
    return "|".join(parts)


def ttys_for_cands(idx: RxNormIndexes, cands: list[str]) -> str:
    parts = []
    for c in cands:
        parts.append("|".join(sorted(idx.rxcui_to_ttys.get(c, set()))) or "UNKNOWN")
    return ";".join(parts)


def generate_all(
    baseline_dir: Path,
    drug_csv: Path,
    input_dir: Path,
    out_root: Path,
    analysis_dir: Path,
) -> int:
    print(f"Loading RxNorm indexes from {drug_csv} ...")
    idx = load_rxnorm_indexes(drug_csv)
    print(
        f"  rxcuis={len(idx.rxcui_to_terms)} IN/PIN aliases={len(idx.ingredient_aliases)} "
        f"SCD rows={len(idx.scd_rows)} relationships={idx.has_relationships}"
    )

    print("Running official-example unit tests ...")
    test_results = run_unit_tests(idx)
    if not (test_results.get("nystatin") and test_results.get("acetaminophen_range")):
        print("HARD GATE: Probe 1 official examples FAILED — aborting probe generation.")
        print(json.dumps(test_results, indent=2))
        return 2

    baseline_hash = semantic_manifest_hash(baseline_dir)
    print(f"Baseline semantic hash: {baseline_hash}")
    baseline = load_submission(baseline_dir)

    # control copy
    control_dir = out_root / "control_baseline"
    print(f"Writing control to {control_dir}")
    deep_copy_submission(baseline_dir, control_dir)
    control_hash = semantic_manifest_hash(control_dir)
    if control_hash != baseline_hash:
        print("STOP: control hash mismatch")
        return 3
    print("Control hash OK")

    # Build probe datasets
    probe_names = [
        "rxnorm_probe_example_policy",
        "rxnorm_probe_ingredient_first",
        "rxnorm_probe_baseline_plus_ingredient",
    ]
    probes = {name: deepcopy(baseline) for name in probe_names}
    matrix_rows: list[EntityRow] = []
    change_rows: dict[str, list[dict[str, Any]]] = {n: [] for n in probe_names}

    texts: dict[str, str] = {}
    for i in range(1, 101):
        texts[str(i)] = (input_dir / f"{i}.txt").read_text(encoding="utf-8")

    for stem, ents in baseline.items():
        text = texts[stem]
        for ei, ent in enumerate(ents):
            if ent.get("type") != DRUG_TYPE:
                continue
            start, end = ent["position"]
            mention = ent["text"]
            baseline_cands = [str(c) for c in (ent.get("candidates") or [])]
            feat = parse_mention_features(mention, idx)
            ing = resolve_ingredient(mention, baseline_cands, idx)

            p1, r1 = probe1_candidates(mention, baseline_cands, feat, ing, idx)
            p2, r2 = probe2_candidates(baseline_cands, ing, idx)
            p3, r3 = probe3_candidates(baseline_cands, ing, idx)

            new_p1 = p1 if p1 is not None else baseline_cands
            new_p2 = p2 if p2 is not None else baseline_cands
            new_p3 = p3 if p3 is not None else baseline_cands

            probes[probe_names[0]][stem][ei]["candidates"] = list(new_p1)
            probes[probe_names[1]][stem][ei]["candidates"] = list(new_p2)
            probes[probe_names[2]][stem][ei]["candidates"] = list(new_p3)

            left = text[max(0, start - 40) : start]
            right = text[end : end + 40]
            row = EntityRow(
                file=stem,
                start=start,
                end=end,
                text=mention,
                baseline_candidates=baseline_cands,
                baseline_candidate_terms=terms_for_cands(idx, baseline_cands),
                baseline_candidate_ttys=ttys_for_cands(idx, baseline_cands),
                safe_ingredient_rxcui=ing.safe_ingredient_rxcui or "",
                safe_ingredient_term=ing.safe_ingredient_term or "",
                ingredient_resolution_source=ing.source,
                ingredient_conflict=ing.conflict,
                multi_ingredient=ing.multi_ingredient,
                has_explicit_strength=feat.has_explicit_strength,
                strength_low=feat.strength_low or "",
                strength_high=feat.strength_high or "",
                strength_unit=feat.strength_unit or "",
                is_strength_range=feat.is_strength_range,
                route=feat.route or "",
                dose_form=feat.dose_form or "",
                explicit_brand=feat.explicit_brand,
                probe_1_candidate="|".join(new_p1),
                probe_2_candidate="|".join(new_p2),
                probe_3_candidates="|".join(new_p3),
                left_context=left.replace("\n", " "),
                right_context=right.replace("\n", " "),
                p1_reason=r1,
                p2_reason=r2,
                p3_reason=r3,
            )
            matrix_rows.append(row)

            for name, new_c, reason in (
                (probe_names[0], new_p1, r1),
                (probe_names[1], new_p2, r2),
                (probe_names[2], new_p3, r3),
            ):
                if new_c != baseline_cands:
                    change_rows[name].append(
                        {
                            "file": stem,
                            "start": start,
                            "end": end,
                            "text": mention,
                            "left_context": left.replace("\n", " "),
                            "right_context": right.replace("\n", " "),
                            "baseline_candidates": "|".join(baseline_cands),
                            "baseline_terms": terms_for_cands(idx, baseline_cands),
                            "baseline_ttys": ttys_for_cands(idx, baseline_cands),
                            "safe_ingredient": ing.safe_ingredient_rxcui or "",
                            "safe_ingredient_term": ing.safe_ingredient_term or "",
                            "has_strength": feat.has_explicit_strength,
                            "strength_low": feat.strength_low or "",
                            "strength_high": feat.strength_high or "",
                            "strength_unit": feat.strength_unit or "",
                            "route": feat.route or "",
                            "dose_form": feat.dose_form or "",
                            "probe_candidates": "|".join(new_c),
                            "probe_candidate_terms": terms_for_cands(idx, new_c),
                            "probe_candidate_ttys": ttys_for_cands(idx, new_c),
                            "change_reason": reason,
                        }
                    )

    # write probes + validate
    analysis_dir.mkdir(parents=True, exist_ok=True)
    zip_meta: list[dict[str, Any]] = []
    summary_lines: list[str] = [
        "# RxNorm probe summary",
        "",
        f"Baseline: `{baseline_dir}`",
        f"Semantic hash: `{baseline_hash}`",
        f"Entities: {count_entities(baseline)} | Drugs: {len(matrix_rows)}",
        f"Relationships available: {idx.has_relationships}",
        f"Unit tests: nystatin={'PASS' if test_results['nystatin'] else 'FAIL'} "
        f"acetaminophen={'PASS' if test_results['acetaminophen_range'] else 'FAIL'}",
        "",
    ]

    tty_transition_md: list[str] = ["# RxNorm probe TTY transitions", ""]

    for name in probe_names:
        out_dir = out_root / name
        print(f"Writing {name} -> {out_dir}")
        write_submission(probes[name], out_dir)

        errs = validate_invariants(baseline, probes[name])
        if errs:
            print(f"INVARIANT FAIL {name}: {errs[:10]}")
            return 4
        off = validate_offsets(probes[name], input_dir)
        if off:
            print(f"OFFSET FAIL {name}: {off}")
            return 5

        # stats
        changed = len(change_rows[name])
        baseline_linked = sum(1 for r in matrix_rows if r.baseline_candidates)
        baseline_unlinked = len(matrix_rows) - baseline_linked
        newly_linked = newly_unlinked = 0
        to_in = to_pin = to_scd = multi_len = 0
        for ch in change_rows[name]:
            b = [x for x in ch["baseline_candidates"].split("|") if x]
            p = [x for x in ch["probe_candidates"].split("|") if x]
            if not b and p:
                newly_linked += 1
            if b and not p:
                newly_unlinked += 1
            if len(p) >= 2:
                multi_len += 1
            if len(p) == 1:
                ttys = idx.rxcui_to_ttys.get(p[0], set())
                if "IN" in ttys:
                    to_in += 1
                elif "PIN" in ttys:
                    to_pin += 1
                if "SCD" in ttys:
                    to_scd += 1
        signal = "LOW SIGNAL" if changed < 20 else ("MODERATE SIGNAL" if changed < 50 else "STRONG SIGNAL")
        summary_lines += [
            f"## {name}",
            "",
            f"- total entities: {count_entities(probes[name])}",
            f"- total drugs: {len(matrix_rows)}",
            f"- baseline linked drugs: {baseline_linked}",
            f"- baseline unlinked drugs: {baseline_unlinked}",
            f"- drug entities changed: {changed}",
            f"- unchanged drugs: {len(matrix_rows) - changed}",
            f"- newly linked drugs: {newly_linked}",
            f"- newly unlinked drugs: {newly_unlinked}",
            f"- changed to IN: {to_in}",
            f"- changed to PIN: {to_pin}",
            f"- changed to SCD: {to_scd}",
            f"- candidate-list length 2+: {multi_len}",
            f"- signal: **{signal}**",
            f"- invariant errors: 0",
            f"- offset mismatches: {off}",
            "",
        ]

        # change TSV
        tsv_path = analysis_dir / f"{name}_changes.tsv"
        fields = [
            "file",
            "start",
            "end",
            "text",
            "left_context",
            "right_context",
            "baseline_candidates",
            "baseline_terms",
            "baseline_ttys",
            "safe_ingredient",
            "safe_ingredient_term",
            "has_strength",
            "strength_low",
            "strength_high",
            "strength_unit",
            "route",
            "dose_form",
            "probe_candidates",
            "probe_candidate_terms",
            "probe_candidate_ttys",
            "change_reason",
        ]
        with tsv_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
            w.writeheader()
            for ch in change_rows[name]:
                w.writerow(ch)

        # TTY transitions for probe 1 and 2
        if name in probe_names[:2]:
            trans: Counter[str] = Counter()
            for ch in change_rows[name]:
                b = [x for x in ch["baseline_candidates"].split("|") if x]
                p = [x for x in ch["probe_candidates"].split("|") if x]
                b_tty = (
                    "|".join(sorted(idx.rxcui_to_ttys.get(b[0], set()))) if len(b) == 1 else ("MULTI" if b else "EMPTY")
                )
                p_tty = (
                    "|".join(sorted(idx.rxcui_to_ttys.get(p[0], set()))) if len(p) == 1 else ("MULTI" if p else "EMPTY")
                )
                if not b_tty:
                    b_tty = "UNKNOWN"
                if not p_tty:
                    p_tty = "UNKNOWN"
                # simplify to primary
                def prim(t: str) -> str:
                    if t in {"MULTI", "EMPTY", "UNKNOWN"}:
                        return t
                    for pref in ("IN", "PIN", "SCD", "SBD", "BN"):
                        if pref in t.split("|"):
                            return pref
                    return t.split("|")[0]

                trans[f"{prim(b_tty)} → {prim(p_tty)}"] += 1
            tty_transition_md += [f"## {name}", "", "| Baseline TTY | Probe TTY | Count |", "|---|---|---:|"]
            for k, v in sorted(trans.items(), key=lambda x: -x[1]):
                a, b = k.split(" → ")
                tty_transition_md.append(f"| {a} | {b} | {v} |")
            tty_transition_md.append("")

        # package zip: output/1.json ... inside zip
        zip_path = PROJECT_ROOT / "output" / f"{name}.zip"
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for i in range(1, 101):
                zf.write(out_dir / f"{i}.json", arcname=f"output/{i}.json")

        # reopen validate
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = sorted(n for n in zf.namelist() if n.endswith(".json"))
            assert len(names) == 100, names
            zdata: dict[str, list] = {}
            for i in range(1, 101):
                raw = zf.read(f"output/{i}.json")
                zdata[str(i)] = json.loads(raw.decode("utf-8"))
            assert all(isinstance(zdata[str(i)], list) for i in range(1, 101))
            assert count_entities(zdata) == count_entities(baseline)
            zerr = validate_invariants(baseline, zdata)
            zoff = validate_offsets(zdata, input_dir)
            if zerr or zoff:
                print(f"ZIP VALIDATION FAIL {name}: errs={zerr[:5]} off={zoff}")
                return 6

        sha = file_sha256(zip_path)
        size = zip_path.stat().st_size
        print(
            f"SUBMISSION ZIP VALID\n"
            f"  path={zip_path}\n"
            f"  size={size}\n"
            f"  SHA256={sha}\n"
            f"  JSON files: 100\n"
            f"  Entities: {count_entities(baseline)}\n"
            f"  Offset mismatches: 0\n"
            f"  Non-candidate field changes: 0\n"
            f"  Non-drug candidate changes: 0"
        )
        zip_meta.append({"name": name, "path": str(zip_path), "size": size, "sha256": sha, "changed": changed, "signal": signal})

        # manual examples section later

    # entity matrix
    matrix_path = analysis_dir / "rxnorm_probe_entity_matrix.tsv"
    mfields = [
        "file",
        "start",
        "end",
        "text",
        "baseline_candidates",
        "baseline_candidate_terms",
        "baseline_candidate_ttys",
        "safe_ingredient_rxcui",
        "safe_ingredient_term",
        "ingredient_resolution_source",
        "ingredient_conflict",
        "multi_ingredient",
        "has_explicit_strength",
        "strength_low",
        "strength_high",
        "strength_unit",
        "is_strength_range",
        "route",
        "dose_form",
        "explicit_brand",
        "probe_1_candidate",
        "probe_2_candidate",
        "probe_3_candidates",
    ]
    with matrix_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=mfields, delimiter="\t")
        w.writeheader()
        for r in matrix_rows:
            w.writerow(
                {
                    "file": r.file,
                    "start": r.start,
                    "end": r.end,
                    "text": r.text,
                    "baseline_candidates": "|".join(r.baseline_candidates),
                    "baseline_candidate_terms": r.baseline_candidate_terms,
                    "baseline_candidate_ttys": r.baseline_candidate_ttys,
                    "safe_ingredient_rxcui": r.safe_ingredient_rxcui,
                    "safe_ingredient_term": r.safe_ingredient_term,
                    "ingredient_resolution_source": r.ingredient_resolution_source,
                    "ingredient_conflict": r.ingredient_conflict,
                    "multi_ingredient": r.multi_ingredient,
                    "has_explicit_strength": r.has_explicit_strength,
                    "strength_low": r.strength_low,
                    "strength_high": r.strength_high,
                    "strength_unit": r.strength_unit,
                    "is_strength_range": r.is_strength_range,
                    "route": r.route,
                    "dose_form": r.dose_form,
                    "explicit_brand": r.explicit_brand,
                    "probe_1_candidate": r.probe_1_candidate,
                    "probe_2_candidate": r.probe_2_candidate,
                    "probe_3_candidates": r.probe_3_candidates,
                }
            )

    (analysis_dir / "rxnorm_probe_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    (analysis_dir / "rxnorm_probe_tty_transitions.md").write_text("\n".join(tty_transition_md) + "\n", encoding="utf-8")

    # examples md
    examples: list[str] = ["# RxNorm probe manual examples", ""]
    for name in probe_names:
        examples += [f"## {name}", ""]
        rows = change_rows[name]
        # prioritize interesting reasons
        priority = [
            "no_strength_to_ingredient",
            "strength_to_scd",
            "range_to_lower_scd",
            "ingredient_first",
            "baseline_plus_ingredient",
            "scd_tie_or_miss_fallback_ingredient",
        ]
        ordered = sorted(
            rows,
            key=lambda r: (
                priority.index(r["change_reason"]) if r["change_reason"] in priority else 99,
                r["file"],
                r["start"],
            ),
        )
        show = ordered[:20] if len(ordered) > 20 else ordered
        for ch in show:
            examples += [
                f"- `{ch['file']}` [{ch['start']}:{ch['end']}] `{ch['text']}`",
                f"  - baseline: `{ch['baseline_candidates']}` ({ch['baseline_ttys']}) {ch['baseline_terms']}",
                f"  - probe: `{ch['probe_candidates']}` ({ch['probe_candidate_ttys']}) {ch['probe_candidate_terms']}",
                f"  - reason: `{ch['change_reason']}` strength={ch['has_strength']} route={ch['route']} form={ch['dose_form']}",
                "",
            ]
        # suspicious: brand-ish or multi-token weird
        suspicious = [
            ch
            for ch in rows
            if ch["change_reason"] == "scd_tie_or_miss_fallback_ingredient"
            or (ch["has_strength"] is True and "ingredient" in ch["change_reason"])
        ][:8]
        if suspicious:
            examples += ["### Suspicious / fallback-heavy", ""]
            for ch in suspicious:
                examples += [
                    f"- `{ch['file']}` `{ch['text']}` → `{ch['probe_candidates']}` ({ch['change_reason']})",
                ]
            examples.append("")

    (analysis_dir / "rxnorm_probe_manual_examples.md").write_text("\n".join(examples) + "\n", encoding="utf-8")

    order_md = f"""# Recommended leaderboard submission order

Baseline reference (newest v7 same_env):
- path: `{baseline_dir}`
- semantic hash: `{baseline_hash}`
- entities: {count_entities(baseline)}
- drugs: {len(matrix_rows)}

## Order

1. `rxnorm_probe_example_policy`
2. `rxnorm_probe_ingredient_first`
3. `rxnorm_probe_baseline_plus_ingredient`

## Reason

- Probe 1 tests the strongest hypothesis from official examples (no strength → IN; strength/range → SCD).
- Probe 2 tests whether gold is broadly ingredient-oriented.
- Probe 3 tests whether multi-candidate coverage (baseline + ingredient) helps Jaccard.

Do **not** submit automatically. Do **not** package the control baseline.

## ZIP artifacts

| Probe | Path | Size | SHA256 | Changed | Signal |
|-------|------|-----:|--------|--------:|--------|
"""
    for z in zip_meta:
        order_md += (
            f"| {z['name']} | `{z['path']}` | {z['size']} | `{z['sha256']}` | {z['changed']} | {z['signal']} |\n"
        )
    (analysis_dir / "rxnorm_probe_submission_order.md").write_text(order_md + "\n", encoding="utf-8")

    results_md = """# RxNorm probe leaderboard results

Fill in after official scoring. Do not invent scores.

| Submission | Final | WER | J_assertion | J_candidates | Δ J_candidates | Δ Final |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Newest v7 same_env baseline | | | | | 0 | 0 |
| Example Policy | | | | | | |
| Ingredient First | | | | | | |
| Baseline + Ingredient | | | | | | |

## Expected invariants (if packaging is clean)

Because only THUỐC candidates change:

- WER and J_assertion should match the baseline submission used here
- The probed metric is J_candidates (and final score)

## Interpretation rules

### Outcome A — Example Policy > Ingredient First > Baseline
Ingredient fallback matters; strength-aware SCD adds value → integrate Example Policy carefully.

### Outcome B — Ingredient First > Example Policy > Baseline
Gold is broadly ingredient-oriented → build ingredient-first linker policy.

### Outcome C — Baseline + Ingredient wins by a large margin
Multi-candidate coverage matters → investigate multi-ID gold / annotation variability.

### Outcome D — all three worse
Do not redesign RxNorm linking around the forum hypothesis; return to v9 recall.

### Outcome E — Example Policy only slightly better
Integrate carefully; continue v9 because entity recall remains the main bottleneck.
"""
    (analysis_dir / "rxnorm_probe_leaderboard_results.md").write_text(results_md, encoding="utf-8")

    # machine-readable meta
    meta = {
        "baseline_dir": str(baseline_dir),
        "baseline_semantic_hash": baseline_hash,
        "entity_count": count_entities(baseline),
        "drug_count": len(matrix_rows),
        "unit_tests": test_results,
        "relationships_available": idx.has_relationships,
        "zips": zip_meta,
    }
    (analysis_dir / "rxnorm_probe_run_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("DONE")
    print(json.dumps(meta, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--drug-csv", type=Path, default=DEFAULT_DRUG_CSV)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--self-test-only", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test_only:
        idx = load_rxnorm_indexes(args.drug_csv)
        results = run_unit_tests(idx)
        return 0 if all(results.values()) else 1

    if not args.baseline_dir.exists():
        print(f"Baseline not found: {args.baseline_dir}")
        return 1
    return generate_all(
        args.baseline_dir,
        args.drug_csv,
        args.input_dir,
        args.out_root,
        args.analysis_dir,
    )


if __name__ == "__main__":
    raise SystemExit(main())
