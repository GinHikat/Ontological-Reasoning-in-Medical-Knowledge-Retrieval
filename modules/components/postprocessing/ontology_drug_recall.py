from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.components.structure.section_parser import VietnameseClinicalSectionParser
from modules.core.config import ProjectPaths
from modules.core.constants import TARGET_LABEL_DRUG
from modules.core.schemas import Document, EntityMention, Span


def normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Lowercase + collapse whitespace/punct; map each norm char to original index."""
    norm_chars: list[str] = []
    index_map: list[int] = []
    prev_space = True
    i = 0
    while i < len(text):
        ch = text[i]
        # NFKC single-char fold where possible
        folded = unicodedata.normalize("NFKC", ch).lower()
        for fch in folded:
            if fch.isalnum():
                norm_chars.append(fch)
                index_map.append(i)
                prev_space = False
            elif fch.isspace() or fch in "-_/.,;:()[]{}+":
                if not prev_space and norm_chars:
                    norm_chars.append(" ")
                    index_map.append(i)
                    prev_space = True
            # else drop other punctuation without emitting space twice
        i += 1
    # trim trailing space
    while norm_chars and norm_chars[-1] == " ":
        norm_chars.pop()
        index_map.pop()
    return "".join(norm_chars), index_map


def compact_with_map(norm: str, index_map: list[int]) -> tuple[str, list[int]]:
    compact_chars: list[str] = []
    compact_map: list[int] = []
    for ch, orig_i in zip(norm, index_map):
        if ch.isspace():
            continue
        compact_chars.append(ch)
        compact_map.append(orig_i)
    return "".join(compact_chars), compact_map


@dataclass(frozen=True)
class _AliasEntry:
    alias: str
    compact: str
    rxcui: str


class _CompactTrieNode:
    __slots__ = ("children", "entries")

    def __init__(self) -> None:
        self.children: dict[str, _CompactTrieNode] = {}
        self.entries: list[_AliasEntry] = []


class OntologyDrugRecallPostProcessor(BaseMentionPostProcessor):
    """Lexical drug recall using the competition RxNorm dictionary."""

    DRUG_SECTIONS = {
        "Thuốc trước khi nhập viện",
        "Điều trị",
    }
    MED_CUES = re.compile(
        r"(?:dùng|uống|tiêm|truyền|kháng\s+sinh|thuốc|điều\s+trị\s+bằng|"
        r"sử\s+dụng|đang\s+dùng)",
        flags=re.IGNORECASE,
    )
    DOSAGE_IN_ALIAS = re.compile(
        r"\d|\b(?:mg|mcg|ml|g|iu|tablet|capsule|injection|oral|solution)\b",
        flags=re.IGNORECASE,
    )
    COMMON_VI_WORDS = {
        "thuốc",
        "điều",
        "trị",
        "bệnh",
        "nhân",
        "ngày",
        "uống",
        "tiêm",
        "truyền",
        "dùng",
        "viên",
        "nước",
        "đau",
        "sốt",
        "ho",
        "máu",
        "tim",
        "gan",
        "thận",
        "phổi",
        "da",
        "mắt",
        "tai",
        "mũi",
        "họng",
        "bụng",
        "ngực",
        "đầu",
        "chân",
        "tay",
        "cấp",
        "mãn",
        "tính",
        "trước",
        "sau",
        "khi",
        "nhập",
        "viện",
        "khoa",
        "bác",
        "sĩ",
        "lactate",
        "glucose",
        "sodium",
        "potassium",
        "calcium",
        "oxygen",
        "water",
        "normal",
        "serum",
        "blood",
        "urine",
        "test",
        "acid",
        "base",
    }
    UNIT_ROUTE = {
        "mg",
        "mcg",
        "ml",
        "g",
        "iu",
        "ui",
        "po",
        "iv",
        "im",
        "sc",
        "bid",
        "tid",
        "qid",
        "prn",
        "oral",
        "tablet",
        "capsule",
    }
    SHORT_WHITELIST = {"asa", "inr"}  # rarely drugs; keep empty-ish
    PREFERRED_TTY = {"IN", "BN", "PIN", "MIN", "SY", "SCD", "SBD", "BN"}

    def __init__(
        self,
        dictionary_path: Path | None = None,
        section_parser: VietnameseClinicalSectionParser | None = None,
        max_aliases: int = 80000,
    ):
        self.dictionary_path = dictionary_path or (
            ProjectPaths().viettel_base_dir / "short_drug.csv"
        )
        self.section_parser = section_parser or VietnameseClinicalSectionParser()
        self.max_aliases = max_aliases
        self._loaded = False
        self._exact_index: dict[str, list[_AliasEntry]] = defaultdict(list)
        self._trie_root = _CompactTrieNode()
        self._compact_by_first: dict[str, list[_AliasEntry]] = defaultdict(list)

    def _safe_alias(self, term: str) -> bool:
        t = term.strip()
        if not t:
            return False
        if t.isdigit():
            return False
        low = t.lower()
        if low in self.UNIT_ROUTE or low in self.COMMON_VI_WORDS:
            return False
        letters = re.sub(r"[^A-Za-zÀ-ỹ]", "", t)
        if len(letters) < 4 and low not in self.SHORT_WHITELIST:
            return False
        if self.DOSAGE_IN_ALIAS.search(t) and len(t) > 40:
            return False
        # Prefer aliases without heavy dosing strings for lexical recall
        if re.search(r"\d+\s*(?:mg|mcg|ml|g)\b", t, flags=re.IGNORECASE):
            # allow short brand/ingredient still if mostly alpha
            if len(letters) < 6:
                return False
            if len(t.split()) > 4:
                return False
        return True

    def _add_alias(self, term: str, rxcui: str) -> None:
        if not self._safe_alias(term):
            return
        norm, _ = normalize_with_map(term)
        if not norm or len(norm.replace(" ", "")) < 4:
            return
        compact, _ = compact_with_map(norm, list(range(len(norm))))
        if len(compact) < 4:
            return
        entry = _AliasEntry(alias=term, compact=compact, rxcui=str(rxcui))
        self._exact_index[norm].append(entry)
        # trie
        node = self._trie_root
        for ch in compact:
            if ch not in node.children:
                node.children[ch] = _CompactTrieNode()
            node = node.children[ch]
        node.entries.append(entry)
        self._compact_by_first[compact[0]].append(entry)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        path = self.dictionary_path
        if not path.exists():
            self._loaded = True
            return
        df = pd.read_csv(path, usecols=lambda c: c in {"term", "rxcui", "tty"})
        # Prefer clean ingredient/brand rows first
        if "tty" in df.columns:
            preferred = df[df["tty"].isin(self.PREFERRED_TTY)].copy()
            rest = df[~df["tty"].isin(self.PREFERRED_TTY)].copy()
            ordered = pd.concat([preferred, rest], ignore_index=True)
        else:
            ordered = df

        count = 0
        seen_compact: set[str] = set()
        for row in ordered.itertuples(index=False):
            term = str(getattr(row, "term", "") or "")
            rxcui = str(getattr(row, "rxcui", "") or "")
            if not term or not rxcui or term == "nan":
                continue
            # Skip long dosage-heavy synonyms early
            if len(term) > 60:
                continue
            if self.DOSAGE_IN_ALIAS.search(term) and " " in term and len(term) > 25:
                continue
            norm, _ = normalize_with_map(term)
            compact = norm.replace(" ", "")
            if compact in seen_compact:
                continue
            if not self._safe_alias(term):
                continue
            seen_compact.add(compact)
            self._add_alias(term, rxcui)
            count += 1
            if count >= self.max_aliases:
                break
        self._loaded = True

    def _in_drug_context(
        self, text: str, start: int, end: int, sections
    ) -> tuple[bool, bool]:
        """Return (section_or_cue_gated, high_confidence_anywhere_ok)."""
        for section in sections:
            if section.name in self.DRUG_SECTIONS and section.start <= start < section.end:
                return True, True
        window = text[max(0, start - 40) : min(len(text), end + 20)]
        if self.MED_CUES.search(window):
            return True, True
        return False, False

    def _span_from_map(
        self, index_map: list[int], match_start: int, match_end: int
    ) -> tuple[int, int] | None:
        if match_start < 0 or match_end > len(index_map) or match_start >= match_end:
            return None
        orig_indices = index_map[match_start:match_end]
        if not orig_indices:
            return None
        return orig_indices[0], orig_indices[-1] + 1

    def _add_drug(
        self,
        document: Document,
        mentions: list[EntityMention],
        start: int,
        end: int,
        confidence: float,
        meta: dict,
    ) -> None:
        if start >= end:
            return
        text = document.text[start:end]
        for m in mentions:
            if m.span.start == start and m.span.end == end and m.label == TARGET_LABEL_DRUG:
                return
            ms, me = m.span.start, m.span.end
            if ms is None or me is None:
                continue
            # Prefer longer existing drug span
            if m.label == TARGET_LABEL_DRUG and start >= int(ms) and end <= int(me):
                return
        mentions.append(
            EntityMention(
                text=text,
                label=TARGET_LABEL_DRUG,
                span=Span(start, end),
                confidence=confidence,
                source="ontology_drug_recall",
                metadata={"ontology_drug_recall": True, **meta},
            )
        )

    def _exact_phrase_match(
        self, document: Document, mentions: list[EntityMention], sections
    ) -> None:
        text = document.text
        norm, index_map = normalize_with_map(text)
        # Scan for each alias using word-ish boundaries in normalized text
        # Group by length descending for longest-first
        aliases = sorted(self._exact_index.keys(), key=len, reverse=True)
        occupied = [False] * len(norm)
        for alias_norm in aliases:
            if len(alias_norm) < 4:
                continue
            start = 0
            while True:
                idx = norm.find(alias_norm, start)
                if idx < 0:
                    break
                end = idx + len(alias_norm)
                start = idx + 1
                # boundary check
                if idx > 0 and norm[idx - 1].isalnum():
                    continue
                if end < len(norm) and norm[end].isalnum():
                    continue
                if any(occupied[idx:end]):
                    continue
                span = self._span_from_map(index_map, idx, end)
                if span is None:
                    continue
                s, e = span
                gated, _ = self._in_drug_context(text, s, e, sections)
                # Exact high-confidence aliases may match outside gated sections
                entry = self._exact_index[alias_norm][0]
                conf = 0.93 if gated else 0.86
                # Always allow exact phrase matches (high confidence)
                for i in range(idx, end):
                    occupied[i] = True
                self._add_drug(
                    document,
                    mentions,
                    s,
                    e,
                    confidence=conf,
                    meta={"match": "exact_norm", "alias": entry.alias, "rxcui": entry.rxcui},
                )

    def _embedded_compact_match(
        self, document: Document, mentions: list[EntityMention], sections
    ) -> None:
        text = document.text
        # Only scan gated windows to avoid O(doc * dict)
        windows: list[tuple[int, int]] = []
        for section in sections:
            if section.name in self.DRUG_SECTIONS:
                windows.append((section.start, section.end))
        for match in self.MED_CUES.finditer(text):
            windows.append((max(0, match.start() - 10), min(len(text), match.end() + 80)))
        # Also scan lines containing concatenated latin letters without spaces
        for m in re.finditer(r"[A-Za-z]{8,}", text):
            windows.append((m.start(), m.end()))

        # merge windows
        windows.sort()
        merged: list[tuple[int, int]] = []
        for s, e in windows:
            if not merged or s > merged[-1][1]:
                merged.append((s, e))
            else:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))

        for win_s, win_e in merged:
            chunk = text[win_s:win_e]
            norm, nmap = normalize_with_map(chunk)
            compact, cmap = compact_with_map(norm, nmap)
            if len(compact) < 4:
                continue
            i = 0
            while i < len(compact):
                node = self._trie_root
                j = i
                best: tuple[int, int, _AliasEntry] | None = None
                while j < len(compact) and compact[j] in node.children:
                    node = node.children[compact[j]]
                    j += 1
                    if node.entries:
                        best = (i, j, node.entries[0])
                if best is not None:
                    bi, bj, entry = best
                    # Map compact indices back through cmap to original chunk offsets
                    orig_start = win_s + cmap[bi]
                    orig_end = win_s + cmap[bj - 1] + 1
                    # Expand end to cover original characters of the match
                    gated, _ = self._in_drug_context(text, orig_start, orig_end, sections)
                    if gated or len(entry.compact) >= 6:
                        self._add_drug(
                            document,
                            mentions,
                            orig_start,
                            orig_end,
                            confidence=0.9 if gated else 0.82,
                            meta={
                                "match": "embedded_compact",
                                "alias": entry.alias,
                                "rxcui": entry.rxcui,
                            },
                        )
                        i = bj
                        continue
                i += 1

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        self._ensure_loaded()
        if "clinical_sections" not in document.metadata:
            document.metadata["clinical_sections"] = self.section_parser.parse(
                document.text
            )
        sections = document.metadata["clinical_sections"]
        recalled = list(mentions)
        self._exact_phrase_match(document, recalled, sections)
        self._embedded_compact_match(document, recalled, sections)
        return sorted(
            recalled,
            key=lambda m: (
                m.span.start if m.span.start is not None else 10**9,
                m.span.end if m.span.end is not None else 10**9,
            ),
        )
