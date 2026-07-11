#!/usr/bin/env python3
"""Schema-first principles audit over frozen base-v7 + v10 traces.

Produces inventory, provenance, type/span/assertion/candidate audits, risk
ranking, and annotation pool under analysis/schema_audit/.

Does not rerun NER/Qwen/linking models. Offline lexical ICD alternatives only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]

TYPE_SYMPTOM = "TRIỆU_CHỨNG"
TYPE_TEST = "TÊN_XÉT_NGHIỆM"
TYPE_RESULT = "KẾT_QUẢ_XÉT_NGHIỆM"
TYPE_DIAG = "CHẨN_ĐOÁN"
TYPE_DRUG = "THUỐC"
ALLOWED_TYPES = {TYPE_SYMPTOM, TYPE_TEST, TYPE_RESULT, TYPE_DIAG, TYPE_DRUG}

COMPONENT_ALIASES = {
    "ViHealthBertNERExtractor": "ViHealthBERT",
    "SectionAwareRecallPostProcessor": "section-aware recall",
    "LabPairRecallPostProcessor": "lab-pair recall",
    "OntologyDrugRecallPostProcessor": "ontology drug recall",
    "OntologyDiagnosisRecallPostProcessor": "ontology diagnosis recall",
    "ClinicalRecallPostProcessor": "clinical recall",
    "DrugBoundaryPostProcessor": "drug boundary",
    "ClinicalTypeCorrectionPostProcessor": "type correction",
    "WordBoundaryPostProcessor": "word boundary",
    "CandidateMergePostProcessor": "candidate merge",
    "ClinicalPrecisionFilterPostProcessor": "precision filter",
    "OverlapDedupPostProcessor": "overlap dedup",
    "HybridEntityLinker": "entity linker",
    "RuleBasedAssertionDetector": "assertion detector",
    "RuleBasedCompetitionLabelMapper": "label mapper",
    "LLMConflictResolutionPostProcessor": "LLM replacement",
    "LLMRecallPostProcessor": "LLM additive recall",
}

PROCEDURE_CUES = [
    "đặt stent",
    "đặt shunt",
    "đặt catheter",
    "đặt sonde",
    "đặt ống",
    "thay van",
    "phẫu thuật",
    "dẫn lưu",
    "can thiệp",
    "điều trị",
    "truyền",
    "tiêm",
    "nạo",
    "chọc",
    "ghép",
    "cắt",
    "đặt ",
]
PROCEDURE_CUE_WORDS = [
    "đặt",
    "dẫn lưu",
    "phẫu thuật",
    "cắt",
    "nạo",
    "chọc",
    "can thiệp",
    "ghép",
    "thay van",
    "truyền",
    "tiêm",
    "điều trị",
    "shunt",
    "stent",
    "catheter",
    "sonde",
]
PROCEDURE_SECTIONS = [
    "các thủ thuật đã thực hiện",
    "thủ thuật",
    "tiền sử phẫu thuật",
    "điều trị",
    "xử trí",
    "can thiệp",
]
TEST_CUES = [
    "xét nghiệm",
    "công thức máu",
    "wbc",
    "creatinin",
    "creatinine",
    "kali",
    "inr",
    "mri",
    "ct",
    "x-quang",
    "xquang",
    "siêu âm",
    "điện tâm đồ",
    "ecg",
    "ekg",
    "cấy máu",
    "cấy nước tiểu",
    "holter",
    "hemoglobin",
    "crp",
    "troponin",
    "glucose",
    "ure",
    "ast",
    "alt",
    "platelet",
    "neut",
    "lyph",
    "twbc",
]
GENERIC_STATUS = [
    "bệnh nhân tỉnh",
    "tiếp xúc tốt",
    "tỉnh táo",
    "da niêm mạc hồng",
    "toàn trạng ổn",
    "ổn định",
    "tỉnh",
    "hợp tác",
    "tiếp xúc",
]
SECTION_HEADING_LIKE = re.compile(
    r"^(tiền sử|bệnh sử|khám|chẩn đoán|điều trị|xử trí|thuốc|"
    r"các xét nghiệm|kết quả|diễn biến|tóm tắt)",
    re.I,
)

ADD_RE = re.compile(
    r'^\s*-\s*"(?P<text>(?:\\.|[^"\\])*)"\s*\[(?P<start>\d+|None),\s*(?P<end>\d+|None)\]\s*\((?P<label>[^)]+)\)\s*$'
)
MOD_SPAN_RE = re.compile(
    r'^\s*-\s*"(?P<text>(?:\\.|[^"\\])*)"\s*\[(?P<start>\d+|None),\s*(?P<end>\d+|None)\]\s*\((?P<label>[^)]+)\)\s*$'
)
SPAN_CHANGE_RE = re.compile(
    r"span:\s*\[(?P<os>\d+),\s*(?P<oe>\d+)\]\s*->\s*\[(?P<ns>\d+),\s*(?P<ne>\d+)\]"
)
STEP_RE = re.compile(
    r"^\[Step\s+\d+\]\s+(?:[^:]+:\s+)?(?P<comp>.+?)\s*$"
)
DIAG_SIM_RE = re.compile(r"diagnosis_similarity:\s*([0-9.eE+-]+)")
BEST_DIAG_RE = re.compile(r"best_diagnosis_id:\s*(\[[^\]]*\]|'[^']*'|\"[^\"]*\"|[^\s,]+)")
DRUG_SIM_RE = re.compile(r"drug_similarity:\s*([0-9.eE+-]+)")
FINAL_CAND_RE = re.compile(r"final_candidates:\s*(\[[^\]]*\])")


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _aggregate_sha(paths: Iterable[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: (len(x.stem), x.stem)):
        h.update(_sha256_file(p).encode())
        h.update(b"\n")
    return h.hexdigest()


def _write_tsv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for row in rows:
            out = {k: row.get(k, "") for k in fieldnames}
            for k, v in out.items():
                if isinstance(v, (list, tuple, dict)):
                    out[k] = json.dumps(v, ensure_ascii=False)
                elif v is None:
                    out[k] = ""
            w.writerow(out)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            out = {k: row.get(k, "") for k in fieldnames}
            for k, v in out.items():
                if isinstance(v, (list, tuple, dict)):
                    out[k] = json.dumps(v, ensure_ascii=False)
                elif v is None:
                    out[k] = ""
            w.writerow(out)


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_vals[int(k)])
    return float(sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f))


def _section_guess(text: str, start: int) -> str:
    prefix = text[: max(0, start)]
    lines = prefix.split("\n")
    for line in reversed(lines):
        s = line.strip()
        if not s:
            continue
        if re.match(r"^\d+\.\s+", s) or s.endswith(":") or len(s) <= 80:
            return s[:120]
    return ""


def _local_sentence(text: str, start: int, end: int) -> str:
    left = max(0, start - 120)
    right = min(len(text), end + 120)
    chunk = text[left:right]
    # trim to nearby newlines when possible
    a = chunk.rfind("\n", 0, start - left)
    b = chunk.find("\n", end - left)
    if a < 0:
        a = 0
    else:
        a += 1
    if b < 0:
        b = len(chunk)
    return chunk[a:b].strip()


def _context(text: str, start: int, end: int, window: int = 40) -> tuple[str, str]:
    left = text[max(0, start - window) : start]
    right = text[end : min(len(text), end + window)]
    return left.replace("\n", " "), right.replace("\n", " ")


@dataclass
class Entity:
    file: str
    start: int
    end: int
    text: str
    type: str
    assertions: list[str]
    candidates: list[str]
    section: str = ""
    source_component: str = "UNRESOLVED"
    trace_provenance: str = "UNRESOLVED"
    length_characters: int = 0
    length_words: int = 0
    contains_newline: bool = False
    risk_score: int = 0
    risk_reasons: list[str] = field(default_factory=list)
    flags: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, int, int, str]:
        return (self.file, self.start, self.end, self.text)


def load_entities(path: Path, file_id: str, doc_text: str) -> list[Entity]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[Entity] = []
    for item in raw:
        start, end = int(item["position"][0]), int(item["position"][1])
        text = str(item.get("text", ""))
        out.append(
            Entity(
                file=file_id,
                start=start,
                end=end,
                text=text,
                type=str(item.get("type", "")),
                assertions=list(item.get("assertions") or []),
                candidates=[str(c) for c in (item.get("candidates") or [])],
                section=_section_guess(doc_text, start),
                length_characters=len(text),
                length_words=len(text.split()),
                contains_newline=("\n" in text),
            )
        )
    return out


def parse_trace_provenance(trace_path: Path) -> dict[tuple[int, int], dict[str, Any]]:
    """Map final-ish spans to first introducing component via add/modify lineage."""
    if not trace_path.exists():
        return {}
    lines = trace_path.read_text(encoding="utf-8", errors="replace").splitlines()
    current_comp = "UNRESOLVED"
    mode: str | None = None  # added | modified
    # lineage: current_span -> first source info
    span_source: dict[tuple[int, int], dict[str, Any]] = {}
    pending_old: tuple[int, int] | None = None

    def alias(comp: str) -> str:
        comp = comp.strip()
        return COMPONENT_ALIASES.get(comp, comp)

    for i, line in enumerate(lines):
        mstep = STEP_RE.match(line)
        if mstep:
            current_comp = alias(mstep.group("comp"))
            mode = None
            pending_old = None
            continue
        if "[+] Added:" in line:
            mode = "added"
            pending_old = None
            continue
        if "[*] Modified:" in line:
            mode = "modified"
            pending_old = None
            continue
        if "[-] Removed:" in line:
            mode = "removed"
            pending_old = None
            continue
        if line.startswith("  All current") or line.startswith("-----"):
            mode = None
            pending_old = None
            continue

        if mode == "added":
            m = ADD_RE.match(line)
            if not m:
                continue
            if m.group("start") == "None" or m.group("end") == "None":
                continue
            s, e = int(m.group("start")), int(m.group("end"))
            if (s, e) not in span_source:
                span_source[(s, e)] = {
                    "source_component": current_comp,
                    "trace_provenance": f"added@{current_comp}",
                    "intro_text": m.group("text"),
                    "intro_label": m.group("label"),
                }
            continue

        if mode == "modified":
            m = MOD_SPAN_RE.match(line)
            if m and m.group("start") != "None":
                pending_old = (int(m.group("start")), int(m.group("end")))
                continue
            if pending_old is not None:
                ch = SPAN_CHANGE_RE.search(line)
                if ch:
                    old = (int(ch.group("os")), int(ch.group("oe")))
                    new = (int(ch.group("ns")), int(ch.group("ne")))
                    src = span_source.get(old) or span_source.get(pending_old)
                    if src is None:
                        # inherit nearest overlapping prior if any
                        src = {
                            "source_component": current_comp,
                            "trace_provenance": f"modified@{current_comp}",
                            "intro_text": "",
                            "intro_label": "",
                        }
                    else:
                        src = dict(src)
                        src["trace_provenance"] = (
                            src.get("trace_provenance", "")
                            + f"|span_expand@{current_comp}"
                        )
                    span_source[new] = src
                    pending_old = None
                continue

        # Linker diagnostics: attach sims onto exact spans appearing as entity lines
        if "diagnosis_similarity:" in line or "drug_similarity:" in line:
            # look backward for entity header
            for j in range(i - 1, max(-1, i - 30), -1):
                hm = ADD_RE.match(lines[j].lstrip() if False else lines[j])
                # entity lines in "All current entities" use same format with optional candidates
                em = re.match(
                    r'^\s*-\s*"(?P<text>(?:\\.|[^"\\])*)"\s*\[(?P<start>\d+),\s*(?P<end>\d+)\]',
                    lines[j],
                )
                if em:
                    key = (int(em.group("start")), int(em.group("end")))
                    info = span_source.setdefault(
                        key,
                        {
                            "source_component": "UNRESOLVED",
                            "trace_provenance": "UNRESOLVED",
                        },
                    )
                    ds = DIAG_SIM_RE.search(line)
                    if ds:
                        info["diagnosis_similarity"] = float(ds.group(1))
                    dgs = DRUG_SIM_RE.search(line)
                    if dgs:
                        info["drug_similarity"] = float(dgs.group(1))
                    break

    return span_source


def resolve_provenance(
    ent: Entity, span_source: dict[tuple[int, int], dict[str, Any]]
) -> None:
    exact = span_source.get((ent.start, ent.end))
    if exact:
        ent.source_component = exact.get("source_component", "UNRESOLVED")
        ent.trace_provenance = exact.get("trace_provenance", "UNRESOLVED")
        ent.flags["diagnosis_similarity"] = exact.get("diagnosis_similarity")
        ent.flags["drug_similarity"] = exact.get("drug_similarity")
        return
    # containment / overlap fallback
    best = None
    best_score = -1
    for (s, e), info in span_source.items():
        if e <= ent.start or s >= ent.end:
            continue
        overlap = min(ent.end, e) - max(ent.start, s)
        if overlap <= 0:
            continue
        score = overlap
        # prefer same text containment
        intro = str(info.get("intro_text") or "")
        if intro and (intro in ent.text or ent.text in intro):
            score += 1000
        if score > best_score:
            best_score = score
            best = info
    if best:
        ent.source_component = best.get("source_component", "UNRESOLVED")
        ent.trace_provenance = (
            str(best.get("trace_provenance", "UNRESOLVED")) + "|overlap_match"
        )
        ent.flags["diagnosis_similarity"] = best.get("diagnosis_similarity")
        ent.flags["drug_similarity"] = best.get("drug_similarity")
    else:
        ent.source_component = "UNRESOLVED"
        ent.trace_provenance = "UNRESOLVED"


# ---------------------------------------------------------------------------
# ICD lexical helpers (no SapBERT)
# ---------------------------------------------------------------------------


def load_icd_index(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "id": str(row.get("id", "")).strip(),
                    "name_vi": str(row.get("name_vi", "") or ""),
                    "name_en": str(row.get("name_en", "") or ""),
                }
            )
    return rows


def format_icd_display(code: str) -> str:
    code = code.strip()
    if "." in code:
        return code
    if len(code) <= 3:
        return code
    # A000 -> A00.0 style when 4+ chars alphanumeric ICD
    if re.match(r"^[A-TV-Z][0-9]{2}[0-9A-Z]+$", code, re.I):
        return code[:3] + "." + code[3:]
    return code


def normalize_icd_key(code: str) -> str:
    return code.replace(".", "").upper()


def lexical_icd_alternatives(
    text: str,
    current: list[str],
    icd_rows: list[dict[str, str]],
    limit: int = 8,
) -> list[dict[str, Any]]:
    q = _fold(text)
    if not q:
        return []
    cur_keys = {normalize_icd_key(c) for c in current}
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in icd_rows:
        names = [_fold(row["name_vi"]), _fold(row["name_en"])]
        best = 0.0
        matched = ""
        for n in names:
            if not n:
                continue
            if q == n:
                sim = 1.0
            elif q in n or n in q:
                sim = 0.92 if min(len(q), len(n)) >= 8 else 0.75
            else:
                # token overlap
                tq = set(q.split())
                tn = set(n.split())
                if not tq or not tn:
                    continue
                inter = len(tq & tn)
                sim = inter / max(len(tq), 1) * 0.7
            if sim > best:
                best = sim
                matched = n
        if best < 0.55:
            continue
        cid = row["id"]
        scored.append(
            (
                best,
                {
                    "id": cid,
                    "id_display": format_icd_display(cid),
                    "name_vi": row["name_vi"],
                    "name_en": row["name_en"],
                    "matched": matched,
                    "similarity": round(best, 4),
                    "is_current": normalize_icd_key(cid) in cur_keys,
                },
            )
        )
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    # dedupe by normalized id
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for _, item in scored:
        k = normalize_icd_key(item["id"])
        if k in seen:
            continue
        seen.add(k)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def sibling_unspecified_pairs(code: str, icd_ids: set[str]) -> list[str]:
    """Heuristic: parent / .9 unspecified / sibling specified codes."""
    key = normalize_icd_key(code)
    alts: list[str] = []
    if len(key) >= 3:
        parent = key[:3]
        if parent in icd_ids and parent != key:
            alts.append(parent)
        # unspecified .9
        unspec = parent + "9"
        if unspec in icd_ids and unspec != key:
            alts.append(unspec)
        # all children of parent with same length family
        for cid in icd_ids:
            if cid.startswith(parent) and cid != key and len(cid) <= len(parent) + 2:
                alts.append(cid)
    # unique preserve order
    seen: set[str] = set()
    out: list[str] = []
    for a in alts:
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out[:12]


# ---------------------------------------------------------------------------
# Audits
# ---------------------------------------------------------------------------


def audit_test_name(ent: Entity, doc: str) -> dict[str, Any]:
    text_f = _fold(ent.text)
    left, right = _context(doc, ent.start, ent.end)
    proc_hits = [c for c in PROCEDURE_CUE_WORDS if c in text_f]
    # also multiword cues
    for c in PROCEDURE_CUES:
        if c.strip() in text_f and c.strip() not in proc_hits:
            proc_hits.append(c.strip())
    test_hits = [c for c in TEST_CUES if c in text_f]
    sec_f = _fold(ent.section)
    in_proc_section = any(s in sec_f for s in PROCEDURE_SECTIONS)
    reasons: list[str] = []
    status = "AMBIGUOUS"
    if "đặt shunt dẫn lưu tĩnh mạch cửa qua da" in text_f:
        status = "LIKELY_PROCEDURE_NOT_TEST"
        reasons.append("required_example_shunt")
    if proc_hits and not test_hits:
        status = "LIKELY_PROCEDURE_NOT_TEST"
        reasons.append("procedure_cues_without_test_cues:" + "|".join(proc_hits))
    elif proc_hits and test_hits:
        status = "AMBIGUOUS"
        reasons.append("both_procedure_and_test_cues")
    elif in_proc_section and proc_hits:
        status = "LIKELY_PROCEDURE_NOT_TEST"
        reasons.append("procedure_section+" + "|".join(proc_hits))
    elif test_hits and not proc_hits:
        status = "LIKELY_GENUINE_TEST"
        reasons.append("test_cues:" + "|".join(test_hits))
    elif re.search(r"\b(mri|ct|ecg|ekg|wbc|inr)\b", text_f):
        status = "AMBIGUOUS"
        reasons.append("imaging_or_abbrev_review")
    elif len(ent.text.split()) <= 4 and not proc_hits:
        status = "LIKELY_GENUINE_TEST"
        reasons.append("short_non_procedure")
    else:
        reasons.append("no_strong_cue")
    if in_proc_section:
        reasons.append("procedure_section")
    return {
        "file": ent.file,
        "text": ent.text,
        "position": f"{ent.start}-{ent.end}",
        "section": ent.section,
        "left_context": left,
        "right_context": right,
        "source_component": ent.source_component,
        "procedure_cues": "|".join(proc_hits),
        "test_cues": "|".join(test_hits),
        "risk_status": status,
        "risk_reasons": ";".join(reasons),
    }


def audit_test_result(ent: Entity, doc: str) -> dict[str, Any]:
    text = ent.text.strip()
    text_f = _fold(text)
    left, right = _context(doc, ent.start, ent.end)
    unit_re = re.compile(
        r"(\d+([.,]\d+)?)\s*(mmol/l|mg/dl|g/l|g/dl|%|u/l|iu/l|mmhg|bpm|°c|/mm3|x10\^?\d+)?",
        re.I,
    )
    qualitative = any(
        k in text_f
        for k in [
            "dương tính",
            "âm tính",
            "bình thường",
            "tăng",
            "giảm",
            "âm",
            "dương",
            "positive",
            "negative",
        ]
    )
    has_test_name = any(c in text_f for c in TEST_CUES) or bool(
        re.search(r"[a-záàảãạăâèéêìíòóôơùúưỳýđ]{3,}", text_f)
        and re.search(r"\d", text_f)
        and any(
            w in text_f
            for w in ["là", ":", "=", "khoảng", "bằng"]
        )
    )
    cls = "INVALID_RESULT"
    if re.fullmatch(r"\d+([.,]\d+)?", text.replace(" ", "")):
        cls = "VALUE_ONLY"
    elif unit_re.fullmatch(text.replace(" ", "")) or (
        re.search(r"\d", text) and re.search(r"(mmol|mg|g/|%|u/l|mmhg)", text_f)
    ):
        cls = "VALUE_PLUS_UNIT"
    elif qualitative and not re.search(r"\d", text):
        cls = "QUALITATIVE_RESULT"
    elif has_test_name and re.search(r"\d", text):
        cls = "OVERLONG_RESULT_CLAUSE"
    elif len(text.split()) >= 6:
        cls = "OVERLONG_RESULT_CLAUSE"
    elif re.search(r"\d", text):
        cls = "VALUE_ONLY"
    else:
        cls = "NON_RESULT_PHRASE"
    return {
        "file": ent.file,
        "text": ent.text,
        "position": f"{ent.start}-{ent.end}",
        "section": ent.section,
        "left_context": left,
        "right_context": right,
        "source_component": ent.source_component,
        "result_class": cls,
        "contains_test_name_cue": has_test_name,
    }


def audit_drug(ent: Entity, doc: str) -> dict[str, Any]:
    text = ent.text
    text_f = _fold(text)
    left, right = _context(doc, ent.start, ent.end, 60)
    nearby = _fold(doc[max(0, ent.start - 5) : min(len(doc), ent.end + 80)])
    has_strength = bool(re.search(r"\d+\s*(mg|mcg|g|ml|iu|%)", text_f))
    has_route = bool(re.search(r"\b(po|iv|im|sc|sl|pr|uống|tiêm)\b", text_f))
    has_freq = bool(
        re.search(r"\b(bid|tid|qid|qd|q\d+h|prn|ngày|lần)\b", text_f)
        or re.search(r"\bx\s*\d+", text_f)
    )
    has_prn = "prn" in text_f or "khi cần" in text_f
    has_form = bool(re.search(r"(viên|nang|ống|chai|syrup|tab|capsule)", text_f))
    details_outside = False
    outside = nearby[len(text_f) :] if nearby.startswith(text_f) else nearby
    if not has_strength and re.search(r"\d+\s*(mg|mcg|g|ml)", outside):
        details_outside = True
    if not has_route and re.search(r"\b(po|iv|im|sc|uống)\b", outside):
        details_outside = True
    if not has_freq and re.search(r"\b(bid|tid|qid|prn)\b", outside):
        details_outside = True

    cls = "AMBIGUOUS"
    if re.search(r"(trong|kéo dài)$", text_f) or re.search(
        r"(atenololtrong|dùngmethadone|vancozosynbactrim)", text_f
    ):
        cls = "ATTACHED_JUNK"
    elif re.search(r"(iv\s+\w+){2,}|(\w+)(\1)", text_f) or "iv morphineiv" in text_f:
        cls = "ATTACHED_JUNK"
    elif re.search(r"[a-z]{4,}[a-z]{4,}", text_f) and not " " in text and len(text) > 18:
        # concatenated tokens without space
        if not has_strength:
            cls = "ATTACHED_JUNK"
    elif "," in text or " và " in text_f or "/" in text and has_strength is False:
        # multiple drug names heuristic
        toks = re.split(r"[,/]| và ", text_f)
        if len([t for t in toks if len(t.strip()) > 3]) >= 2 and not has_strength:
            cls = "MULTIPLE_DRUGS_MERGED"
    elif has_strength or has_route or has_freq or has_prn or has_form:
        if details_outside:
            cls = "TRUNCATED"
        else:
            cls = "MAXIMAL_COMPLETE"
    elif details_outside:
        cls = "NAME_ONLY_BUT_DETAILS_AVAILABLE"
    elif len(text.split()) == 1 and len(text) >= 3:
        cls = "NAME_ONLY_BUT_DETAILS_AVAILABLE" if details_outside else "AMBIGUOUS"
    if text_f in {"không", "có", "uống", "tiêm"} or len(text) <= 2:
        cls = "LIKELY_NOT_DRUG"
    return {
        "file": ent.file,
        "text": ent.text,
        "position": f"{ent.start}-{ent.end}",
        "section": ent.section,
        "left_context": left,
        "right_context": right,
        "source_component": ent.source_component,
        "has_strength": has_strength,
        "has_dose": has_strength,
        "has_route": has_route,
        "has_frequency": has_freq,
        "has_prn": has_prn,
        "has_dose_form": has_form,
        "details_available_nearby": details_outside,
        "span_class": cls,
        "candidates": "|".join(ent.candidates),
        "candidate_count": len(ent.candidates),
    }


def audit_symptom(ent: Entity, doc: str) -> dict[str, Any]:
    text = ent.text
    text_f = _fold(text)
    left, right = _context(doc, ent.start, ent.end)
    cls = "LIKELY_VALID_MINIMAL"
    reasons: list[str] = []
    if any(g in text_f for g in GENERIC_STATUS) or text_f in {
        "tỉnh",
        "hợp tác",
        "tiếp xúc tốt",
        "bệnh nhân tỉnh",
    }:
        cls = "GENERIC_STATUS"
        reasons.append("generic_status")
    if text_f.startswith("không ") or text_f.startswith("ko "):
        cls = "NEGATION_INCLUDED"
        reasons.append("leading_negation")
    if "," in text or " và " in text_f or " hay " in text_f:
        if len(text.split()) >= 4:
            cls = "MERGED_MULTIPLE"
            reasons.append("comma_or_va_merge")
    if len(text.split()) >= 8 or len(text) >= 45:
        if cls == "LIKELY_VALID_MINIMAL":
            cls = "OVERLONG"
        reasons.append("overlong")
    if any(
        k in text_f
        for k in ["tuần qua", "ngày nay", "khi gắng sức", "khởi phát", "trong"]
    ) and len(text.split()) >= 6:
        if cls == "LIKELY_VALID_MINIMAL":
            cls = "OVERLONG"
        reasons.append("temporal_explanation")
    if any(
        k in text_f
        for k in ["viêm", "suy", "ung thư", "nhồi máu", "xơ gan", "đái tháo đường"]
    ):
        if cls in {"LIKELY_VALID_MINIMAL", "OVERLONG"}:
            cls = "LIKELY_DIAGNOSIS"
        reasons.append("diagnosis_like_lexeme")
    if any(c in text_f for c in TEST_CUES) and re.search(r"\d", text_f):
        cls = "LIKELY_TEST_FINDING"
        reasons.append("test_finding_like")
    if re.search(r"^(tim|gan|phổi|thận|dạ dày)$", text_f):
        cls = "OTHER_SUSPICIOUS"
        reasons.append("anatomy_alone")
    if not reasons and cls == "LIKELY_VALID_MINIMAL":
        reasons.append("minimal_ok")
    return {
        "file": ent.file,
        "text": ent.text,
        "position": f"{ent.start}-{ent.end}",
        "section": ent.section,
        "left_context": left,
        "right_context": right,
        "source_component": ent.source_component,
        "span_class": cls,
        "reasons": ";".join(reasons),
        "assertions": "|".join(ent.assertions),
        "length_words": ent.length_words,
    }


def audit_diagnosis(ent: Entity, doc: str) -> dict[str, Any]:
    text_f = _fold(ent.text)
    sec_f = _fold(ent.section)
    left, right = _context(doc, ent.start, ent.end)
    origin = "other"
    if any(k in sec_f for k in ["chẩn đoán", "kết luận"]):
        origin = "explicit_diagnosis_section"
    elif "tiền sử" in sec_f:
        origin = "history_section"
    elif any(k in sec_f for k in ["siêu âm", "x-quang", "ct", "mri", "hình ảnh"]):
        origin = "imaging_conclusion"
    elif any(k in sec_f for k in ["đánh giá", "nhận định", "assessment"]):
        origin = "assessment"
    elif any(k in sec_f for k in ["triệu chứng", "bệnh sử"]):
        origin = "symptom_section"

    flags: list[str] = []
    if len(ent.text.split()) <= 1 and len(ent.text) <= 4:
        flags.append("fragment")
    if len(ent.text.split()) >= 10:
        flags.append("whole_explanatory_clause")
    if any(g in text_f for g in ["đau", "khó thở", "buồn nôn", "sốt"]) and not any(
        k in text_f for k in ["viêm", "suy", "hội chứng", "bệnh"]
    ):
        flags.append("symptom_mislabeled")
    if any(c in text_f for c in PROCEDURE_CUE_WORDS):
        flags.append("procedure_mislabeled")
    if any(c in text_f for c in TEST_CUES) and re.search(r"\d", text_f):
        flags.append("test_finding_mislabeled")
    if re.search(r"^(tim|gan|phổi|thận)$", text_f):
        flags.append("generic_anatomy")
    if any(k in text_f for k in ["theo dõi", "nghi ngờ", "không loại trừ", "có thể"]):
        flags.append("uncertain_watch")
    return {
        "file": ent.file,
        "text": ent.text,
        "position": f"{ent.start}-{ent.end}",
        "section": ent.section,
        "section_origin": origin,
        "left_context": left,
        "right_context": right,
        "source_component": ent.source_component,
        "flags": "|".join(flags) if flags else "ok",
        "candidates": "|".join(ent.candidates),
        "candidate_count": len(ent.candidates),
    }


def audit_assertions(ent: Entity, doc: str) -> dict[str, Any]:
    sent = _local_sentence(doc, ent.start, ent.end)
    sent_f = _fold(sent)
    text_f = _fold(ent.text)
    sec_f = _fold(ent.section)
    neg_cues = ["không", "chưa", "hết", "không còn", "phủ định"]
    fam_cues = ["bố", "mẹ", "anh", "chị", "em", "con", "gia đình", "họ hàng", "cha"]
    hist_cues = ["tiền sử", "trước đây", "đã từng", "đã dùng", "trước khi nhập viện"]
    temporal = ["tuần qua", "hôm nay", "hiện tại", "đang", "nay"]
    found_neg = [c for c in neg_cues if c in sent_f]
    found_fam = [c for c in fam_cues if c in sent_f]
    found_hist = [c for c in hist_cues if c in sent_f or c in sec_f]
    found_temp = [c for c in temporal if c in sent_f]
    risks: list[str] = []
    assertions = set(ent.assertions)
    if "isHistorical" in assertions:
        if "điều trị" in sec_f or "xử trí" in sec_f:
            if "đã dùng" in sent_f or "đã điều trị" in sent_f:
                risks.append("current_treatment_marked_historical")
        if "tiền sử" in sec_f and ent.type == TYPE_SYMPTOM:
            # indication-like short symptoms in med list may be over-historical
            if any(k in sec_f for k in ["thuốc"]):
                risks.append("symptom_in_historical_med_list")
        if "tiền sử" in sec_f and not found_hist and ent.type != TYPE_DRUG:
            risks.append("history_section_auto_historical")
    if "isNegated" in assertions:
        if text_f.startswith("không ") or text_f.startswith("chưa "):
            risks.append("negation_cue_inside_span")
        if not found_neg:
            risks.append("negation_without_local_cue")
    if "isFamily" in assertions and not found_fam:
        risks.append("family_without_member_evidence")
    if not assertions and found_neg and ent.type in {TYPE_SYMPTOM, TYPE_DIAG, TYPE_DRUG}:
        risks.append("possible_missed_negation")
    return {
        "file": ent.file,
        "text": ent.text,
        "type": ent.type,
        "section": ent.section,
        "local_sentence": sent.replace("\t", " ")[:300],
        "assertions": "|".join(ent.assertions),
        "negation_cue": "|".join(found_neg),
        "family_cue": "|".join(found_fam),
        "history_cue": "|".join(found_hist),
        "temporal_cue": "|".join(found_temp),
        "assertion_risk": "|".join(risks) if risks else "ok",
        "source_component": ent.source_component,
    }


def find_type_collisions(entities: list[Entity]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_file: dict[str, list[Entity]] = defaultdict(list)
    for e in entities:
        by_file[e.file].append(e)
    norm_types: dict[str, set[str]] = defaultdict(set)
    for e in entities:
        norm_types[_fold(e.text)].add(e.type)

    for file_id, ents in by_file.items():
        n = len(ents)
        for i in range(n):
            a = ents[i]
            for j in range(i + 1, n):
                b = ents[j]
                if a.type == b.type:
                    continue
                if a.start == b.start and a.end == b.end:
                    kind = "exact_span_different_type"
                elif a.start <= b.start and a.end >= b.end:
                    kind = "a_contains_b"
                elif b.start <= a.start and b.end >= a.end:
                    kind = "b_contains_a"
                elif a.start < b.end and b.start < a.end:
                    kind = "partial_overlap"
                else:
                    continue
                rows.append(
                    {
                        "file": file_id,
                        "kind": kind,
                        "text_a": a.text,
                        "type_a": a.type,
                        "span_a": f"{a.start}-{a.end}",
                        "text_b": b.text,
                        "type_b": b.type,
                        "span_b": f"{b.start}-{b.end}",
                        "pair": " ↔ ".join(sorted([a.type, b.type])),
                    }
                )
    for text_n, types in norm_types.items():
        if len(types) >= 2 and text_n:
            rows.append(
                {
                    "file": "*",
                    "kind": "same_normalized_text_multi_type",
                    "text_a": text_n,
                    "type_a": "|".join(sorted(types)),
                    "span_a": "",
                    "text_b": "",
                    "type_b": "",
                    "span_b": "",
                    "pair": " ↔ ".join(sorted(types)),
                }
            )
    return rows


def score_entity_risk(
    ent: Entity,
    test_audit: dict[str, Any] | None,
    result_audit: dict[str, Any] | None,
    drug_audit: dict[str, Any] | None,
    symptom_audit: dict[str, Any] | None,
    diag_audit: dict[str, Any] | None,
    assertion_audit: dict[str, Any] | None,
    in_collision: bool,
) -> None:
    score = 0
    reasons: list[str] = []
    if test_audit and test_audit.get("risk_status") == "LIKELY_PROCEDURE_NOT_TEST":
        score += 3
        reasons.append("procedure_as_test")
    if symptom_audit and symptom_audit.get("span_class") == "GENERIC_STATUS":
        score += 3
        reasons.append("generic_status_as_symptom")
    if ent.type in {TYPE_DIAG, TYPE_DRUG}:
        if not ent.candidates:
            score += 3
            reasons.append("empty_candidates")
        # malformed candidates later
    if symptom_audit and symptom_audit.get("span_class") in {
        "OVERLONG",
        "MERGED_MULTIPLE",
    }:
        score += 2
        reasons.append(str(symptom_audit.get("span_class")))
    if result_audit and result_audit.get("result_class") in {
        "OVERLONG_RESULT_CLAUSE",
        "NON_RESULT_PHRASE",
        "INVALID_RESULT",
    }:
        score += 2
        reasons.append(str(result_audit.get("result_class")))
    if drug_audit and drug_audit.get("span_class") in {
        "ATTACHED_JUNK",
        "MULTIPLE_DRUGS_MERGED",
        "LIKELY_NOT_DRUG",
    }:
        score += 2
        reasons.append(str(drug_audit.get("span_class")))
    if assertion_audit:
        ar = str(assertion_audit.get("assertion_risk", "ok"))
        if ar != "ok":
            score += 2
            reasons.append("assertion_risk:" + ar)
    if in_collision:
        score += 2
        reasons.append("type_collision")
    sec_f = _fold(ent.section)
    if not ent.section or len(ent.section) < 3:
        score += 1
        reasons.append("ambiguous_section")
    if SECTION_HEADING_LIKE.search(ent.text.strip()) and len(ent.text.split()) <= 6:
        score += 3
        reasons.append("section_heading_like")
    if ent.end <= ent.start or not ent.text:
        score += 3
        reasons.append("invalid_span")
    ent.risk_score = score
    ent.risk_reasons = reasons


def build_annotation_pool(
    entities: list[Entity],
    test_rows: list[dict[str, Any]],
    result_rows: list[dict[str, Any]],
    symptom_rows: list[dict[str, Any]],
    diag_rows: list[dict[str, Any]],
    drug_rows: list[dict[str, Any]],
    assertion_rows: list[dict[str, Any]],
    multi_icd_rows: list[dict[str, Any]],
    v10_repl_keys: set[tuple[str, int, int]],
    docs: dict[str, str],
) -> list[dict[str, Any]]:
    """Build ~300-item pool with balanced categories (dedupe by entity key)."""
    by_key = {(e.file, e.start, e.end): e for e in entities}
    selected: dict[tuple[str, int, int], dict[str, Any]] = {}

    def add(ent: Entity, category: str) -> None:
        k = (ent.file, ent.start, ent.end)
        doc = docs.get(ent.file, "")
        left, right = _context(doc, ent.start, ent.end, 80)
        if k not in selected:
            selected[k] = {
                "item_id": "",
                "file": ent.file,
                "full_context": (left + "⟦" + ent.text + "⟧" + right).replace("\n", " "),
                "current_text": ent.text,
                "current_start": ent.start,
                "current_end": ent.end,
                "current_type": ent.type,
                "current_assertions": "|".join(ent.assertions),
                "current_candidates": "|".join(ent.candidates),
                "source_component": ent.source_component,
                "risk_categories": category,
                "risk_score": ent.risk_score,
                "human_keep": "",
                "human_corrected_text": "",
                "human_corrected_start": "",
                "human_corrected_end": "",
                "human_corrected_type": "",
                "human_corrected_assertions": "",
                "human_corrected_candidates": "",
                "human_notes": "",
            }
        else:
            cats = set(selected[k]["risk_categories"].split("|"))
            cats.add(category)
            selected[k]["risk_categories"] = "|".join(sorted(c for c in cats if c))
            selected[k]["risk_score"] = max(int(selected[k]["risk_score"]), ent.risk_score)

    def take(cat: str, candidates: list[Entity], n: int) -> None:
        have = sum(
            1 for it in selected.values() if cat in it["risk_categories"].split("|")
        )
        for ent in candidates:
            if have >= n:
                break
            k = (ent.file, ent.start, ent.end)
            already = k in selected and cat in selected[k]["risk_categories"].split("|")
            if already:
                continue
            add(ent, cat)
            have = sum(
                1
                for it in selected.values()
                if cat in it["risk_categories"].split("|")
            )

    proc_ents: list[Entity] = []
    for r in test_rows:
        if r["risk_status"] == "LIKELY_PROCEDURE_NOT_TEST":
            ent = by_key.get((r["file"], *map(int, r["position"].split("-"))))
            if ent:
                proc_ents.append(ent)
    proc_ents.sort(key=lambda e: (-e.risk_score, e.file, e.start))

    v10_ents = [e for e in entities if (e.file, e.start, e.end) in v10_repl_keys]

    symptom_ents: list[Entity] = []
    for r in symptom_rows:
        if r["span_class"] != "LIKELY_VALID_MINIMAL":
            ent = by_key.get((r["file"], *map(int, r["position"].split("-"))))
            if ent:
                symptom_ents.append(ent)
    symptom_ents.sort(key=lambda e: (-e.risk_score, e.file, e.start))
    if len(symptom_ents) < 60:
        symptom_ents = symptom_ents + sorted(
            [e for e in entities if e.type == TYPE_SYMPTOM],
            key=lambda e: (-e.risk_score, e.file, e.start),
        )

    result_ents: list[Entity] = []
    for r in result_rows:
        if r["result_class"] not in {
            "VALUE_ONLY",
            "VALUE_PLUS_UNIT",
            "QUALITATIVE_RESULT",
        }:
            ent = by_key.get((r["file"], *map(int, r["position"].split("-"))))
            if ent:
                result_ents.append(ent)

    test_mix = proc_ents + result_ents + [
        e for e in entities if e.type in {TYPE_TEST, TYPE_RESULT}
    ]
    seen_tm: set[tuple[str, int, int]] = set()
    test_unique: list[Entity] = []
    for e in test_mix:
        k = (e.file, e.start, e.end)
        if k in seen_tm:
            continue
        seen_tm.add(k)
        test_unique.append(e)

    diag_span_ents: list[Entity] = []
    for r in diag_rows:
        if r["flags"] != "ok":
            ent = by_key.get((r["file"], *map(int, r["position"].split("-"))))
            if ent:
                diag_span_ents.append(ent)
    multi_ents: list[Entity] = []
    for r in multi_icd_rows:
        ent = by_key.get((r["file"], *map(int, str(r["position"]).split("-"))))
        if ent:
            multi_ents.append(ent)
    diag_mix = diag_span_ents + multi_ents + [e for e in entities if e.type == TYPE_DIAG]
    seen_d: set[tuple[str, int, int]] = set()
    diag_unique: list[Entity] = []
    for e in diag_mix:
        k = (e.file, e.start, e.end)
        if k in seen_d:
            continue
        seen_d.add(k)
        diag_unique.append(e)

    drug_ents: list[Entity] = []
    for r in drug_rows:
        if r["span_class"] != "MAXIMAL_COMPLETE":
            ent = by_key.get((r["file"], *map(int, r["position"].split("-"))))
            if ent:
                drug_ents.append(ent)
    drug_ents.sort(key=lambda e: (-e.risk_score, e.file, e.start))
    if len(drug_ents) < 40:
        drug_ents = drug_ents + [e for e in entities if e.type == TYPE_DRUG]

    assert_ents: list[Entity] = []
    for r in assertion_rows:
        if r["assertion_risk"] == "ok":
            continue
        ent = by_key.get((r["file"], int(r["_start"]), int(r["_end"])))
        if ent:
            assert_ents.append(ent)
    assert_ents.sort(key=lambda e: (-e.risk_score, e.file, e.start))
    if len(assert_ents) < 40:
        assert_ents = assert_ents + [
            e
            for e in entities
            if e.assertions and e.type in {TYPE_SYMPTOM, TYPE_DIAG, TYPE_DRUG}
        ]

    for e in proc_ents:
        add(e, "procedure_as_test")
    for e in v10_ents:
        add(e, "v10_replacement")

    take("test_name_result", test_unique, 60)
    take("symptom_case", symptom_ents, 60)
    take("diagnosis_case", diag_unique, 60)
    take("drug_case", drug_ents, 40)
    take("assertion_case", assert_ents, 40)
    take("multi_icd", multi_ents, 40)

    cleans = sorted(
        [e for e in entities if e.risk_score == 0],
        key=lambda e: (e.file, e.start),
    )
    take("clean_control", cleans, 40)

    # No hard trim: must-include procedure-as-test + quotas may exceed ~300.
    final = sorted(
        selected.values(),
        key=lambda r: (-int(r["risk_score"]), r["file"], int(r["current_start"])),
    )
    for i, r in enumerate(final, 1):
        r["item_id"] = f"SA-{i:04d}"
    return final



def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--base-dir",
        type=Path,
        default=ROOT / "output/v10_llm_conflict_resolution/base_v7_snapshot",
    )
    ap.add_argument(
        "--v10-dir",
        type=Path,
        default=ROOT / "output/v10_llm_conflict_resolution/submission",
    )
    ap.add_argument(
        "--trace-dir",
        type=Path,
        default=ROOT / "output/v10_llm_conflict_resolution/trace",
    )
    ap.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "v_dataset/var/test",
    )
    ap.add_argument(
        "--analysis-dir",
        type=Path,
        default=ROOT / "analysis/schema_audit",
    )
    ap.add_argument(
        "--icd-csv",
        type=Path,
        default=ROOT / "v_dataset/viettel/base/short_diagnosis.csv",
    )
    ap.add_argument(
        "--v10-replacements",
        type=Path,
        default=ROOT / "analysis/v10_replacements.tsv",
    )
    args = ap.parse_args()
    out_dir: Path = args.analysis_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    base_files = sorted(args.base_dir.glob("*.json"), key=lambda p: int(p.stem))
    v10_files = sorted(args.v10_dir.glob("*.json"), key=lambda p: int(p.stem))
    traces = sorted(args.trace_dir.glob("*_trace.txt"), key=lambda p: int(p.stem.split("_")[0]))
    inputs = sorted(args.input_dir.glob("*.txt"), key=lambda p: int(p.stem))

    docs = {p.stem: p.read_text(encoding="utf-8") for p in inputs}
    empty_traces = [p for p in traces if p.stat().st_size == 0]

    # Phase 1 manifest
    per_file = []
    total_entities = 0
    type_counter: Counter[str] = Counter()
    for p in base_files:
        ents = json.loads(p.read_text(encoding="utf-8"))
        total_entities += len(ents)
        tc = Counter(e["type"] for e in ents)
        type_counter.update(tc)
        per_file.append(
            {
                "file": p.name,
                "sha256": _sha256_file(p),
                "entity_count": len(ents),
                "types": dict(tc),
            }
        )
    manifest = {
        "base_dir": str(args.base_dir),
        "v10_dir": str(args.v10_dir),
        "trace_dir": str(args.trace_dir),
        "input_dir": str(args.input_dir),
        "base_count": len(base_files),
        "v10_count": len(v10_files),
        "trace_count": len(traces),
        "empty_traces": len(empty_traces),
        "input_count": len(inputs),
        "base_aggregate_sha256": _aggregate_sha(base_files),
        "v10_aggregate_sha256": _aggregate_sha(v10_files),
        "total_base_entities": total_entities,
        "type_counts": dict(type_counter),
        "per_file": per_file,
        "validation": {
            "base_100": len(base_files) == 100,
            "v10_100": len(v10_files) == 100,
            "traces_100_nonempty": len(traces) == 100 and len(empty_traces) == 0,
        },
    }
    (out_dir / "artifact_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    icd_rows = load_icd_index(args.icd_csv) if args.icd_csv.exists() else []
    icd_ids = {normalize_icd_key(r["id"]) for r in icd_rows}

    # v10 replacement keys from tsv if present (base-v7 uses OLD spans)
    v10_repl_keys: set[tuple[str, int, int]] = set()
    if args.v10_replacements.exists():
        with args.v10_replacements.open(encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                file_id = str(row.get("file") or row.get("doc") or row.get("stem") or "")
                file_id = file_id.replace(".json", "")
                try:
                    if "old_start" in row and str(row.get("old_start", "")) != "":
                        s, e = int(row["old_start"]), int(row["old_end"])
                    elif "v10_start" in row:
                        s, e = int(row["v10_start"]), int(row["v10_end"])
                    elif "new_start" in row:
                        s, e = int(row["new_start"]), int(row["new_end"])
                    elif "start" in row:
                        s, e = int(row["start"]), int(row["end"])
                    else:
                        continue
                    v10_repl_keys.add((file_id, s, e))
                except Exception:
                    continue

    entities: list[Entity] = []
    inventory_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    drug_rows: list[dict[str, Any]] = []
    symptom_rows: list[dict[str, Any]] = []
    diag_rows: list[dict[str, Any]] = []
    assertion_rows: list[dict[str, Any]] = []
    diag_cand_rows: list[dict[str, Any]] = []
    drug_cand_rows: list[dict[str, Any]] = []
    multi_icd_rows: list[dict[str, Any]] = []

    # provenance tallies
    introduced: Counter[str] = Counter()
    surviving: Counter[str] = Counter()
    source_types: dict[str, Counter[str]] = defaultdict(Counter)
    source_lens: dict[str, list[int]] = defaultdict(list)
    source_assertions: dict[str, Counter[str]] = defaultdict(Counter)
    source_cand_cov: dict[str, list[int]] = defaultdict(list)
    source_flagged: Counter[str] = Counter()

    test_audit_by_key: dict[tuple[str, int, int], dict[str, Any]] = {}
    result_audit_by_key: dict[tuple[str, int, int], dict[str, Any]] = {}
    drug_audit_by_key: dict[tuple[str, int, int], dict[str, Any]] = {}
    symptom_audit_by_key: dict[tuple[str, int, int], dict[str, Any]] = {}
    diag_audit_by_key: dict[tuple[str, int, int], dict[str, Any]] = {}
    assertion_audit_by_key: dict[tuple[str, int, int], dict[str, Any]] = {}

    for bf in base_files:
        file_id = bf.stem
        doc = docs.get(file_id, "")
        ents = load_entities(bf, file_id, doc)
        trace_path = args.trace_dir / f"{file_id}_trace.txt"
        span_source = parse_trace_provenance(trace_path)
        # count introduced
        for info in span_source.values():
            introduced[info.get("source_component", "UNRESOLVED")] += 1

        for ent in ents:
            resolve_provenance(ent, span_source)
            surviving[ent.source_component] += 1
            source_types[ent.source_component][ent.type] += 1
            source_lens[ent.source_component].append(ent.length_characters)
            for a in ent.assertions:
                source_assertions[ent.source_component][a] += 1
            if ent.type in {TYPE_DIAG, TYPE_DRUG}:
                source_cand_cov[ent.source_component].append(1 if ent.candidates else 0)

            # audits
            if ent.type == TYPE_TEST:
                ta = audit_test_name(ent, doc)
                test_rows.append(ta)
                test_audit_by_key[(ent.file, ent.start, ent.end)] = ta
            elif ent.type == TYPE_RESULT:
                ra = audit_test_result(ent, doc)
                result_rows.append(ra)
                result_audit_by_key[(ent.file, ent.start, ent.end)] = ra
            elif ent.type == TYPE_DRUG:
                da = audit_drug(ent, doc)
                drug_rows.append(da)
                drug_audit_by_key[(ent.file, ent.start, ent.end)] = da
                tty = ""
                level = ""
                # heuristic from candidate presence only (offline)
                drug_cand_rows.append(
                    {
                        "file": ent.file,
                        "text": ent.text,
                        "position": f"{ent.start}-{ent.end}",
                        "candidates": "|".join(ent.candidates),
                        "candidate_count": len(ent.candidates),
                        "candidate_tty": tty,
                        "ingredient_vs_clinical": level,
                        "strength_aware": bool(
                            re.search(r"\d+\s*(mg|mcg|ml)", _fold(ent.text))
                        ),
                        "brand_aware": False,
                        "unlinked": len(ent.candidates) == 0,
                        "source_component": ent.source_component,
                        "drug_similarity": ent.flags.get("drug_similarity", ""),
                    }
                )
            elif ent.type == TYPE_SYMPTOM:
                sa = audit_symptom(ent, doc)
                symptom_rows.append(sa)
                symptom_audit_by_key[(ent.file, ent.start, ent.end)] = sa
            elif ent.type == TYPE_DIAG:
                dga = audit_diagnosis(ent, doc)
                diag_rows.append(dga)
                diag_audit_by_key[(ent.file, ent.start, ent.end)] = dga
                alts = lexical_icd_alternatives(ent.text, ent.candidates, icd_rows)
                sibs: list[str] = []
                for c in ent.candidates:
                    sibs.extend(sibling_unspecified_pairs(c, icd_ids))
                # unique
                seen_s: set[str] = set()
                sibs_u = []
                for s in sibs:
                    if s not in seen_s:
                        seen_s.add(s)
                        sibs_u.append(s)
                support = "one_exact_code"
                near = [a for a in alts if not a["is_current"] and a["similarity"] >= 0.75]
                if len(near) >= 2:
                    support = "multiple_sibling_or_alternate"
                elif any(
                    a["id_display"].endswith(".9") or a["id"].endswith("9") for a in near
                ):
                    support = "unspecified_plus_specified"
                elif sibs_u:
                    support = "parent_child_alternatives"
                diag_cand_rows.append(
                    {
                        "file": ent.file,
                        "entity_text": ent.text,
                        "position": f"{ent.start}-{ent.end}",
                        "current_candidates": "|".join(ent.candidates),
                        "current_candidate_count": len(ent.candidates),
                        "candidate_terms": "|".join(
                            a.get("name_vi", "") for a in alts if a.get("is_current")
                        ),
                        "candidate_hierarchy": "|".join(format_icd_display(s) for s in sibs_u[:8]),
                        "top_local_icd_alternatives": json.dumps(
                            [
                                {
                                    "id": a["id_display"],
                                    "sim": a["similarity"],
                                    "name": a["name_vi"],
                                }
                                for a in alts[:5]
                            ],
                            ensure_ascii=False,
                        ),
                        "similarity_values": json.dumps(
                            [a["similarity"] for a in alts[:5]]
                        ),
                        "section": ent.section,
                        "local_support": support,
                        "trace_diagnosis_similarity": ent.flags.get(
                            "diagnosis_similarity", ""
                        ),
                        "source_component": ent.source_component,
                    }
                )
                # multi-icd shortlist score
                multi_score = 0
                if support != "one_exact_code":
                    multi_score += 3
                if len(near) >= 1:
                    multi_score += 2
                if any(
                    "không biệt" in _fold(a["name_vi"])
                    or "unspecified" in _fold(a["name_en"])
                    or a["id"].endswith("9")
                    for a in alts[:5]
                ):
                    multi_score += 2
                # near-equal top sims
                sims = [a["similarity"] for a in alts[:3]]
                if len(sims) >= 2 and abs(sims[0] - sims[1]) <= 0.05:
                    multi_score += 3
                multi_icd_rows.append(
                    {
                        "file": ent.file,
                        "entity_text": ent.text,
                        "position": f"{ent.start}-{ent.end}",
                        "current_candidates": "|".join(
                            format_icd_display(c) for c in ent.candidates
                        ),
                        "multi_score": multi_score,
                        "local_support": support,
                        "top_local_icd_alternatives": json.dumps(
                            [
                                {
                                    "id": a["id_display"],
                                    "sim": a["similarity"],
                                    "name": a["name_vi"],
                                }
                                for a in alts[:5]
                            ],
                            ensure_ascii=False,
                        ),
                        "section": ent.section,
                        "reason": support,
                    }
                )

            if ent.type in {TYPE_SYMPTOM, TYPE_DIAG, TYPE_DRUG}:
                aa = audit_assertions(ent, doc)
                aa["_start"] = ent.start
                aa["_end"] = ent.end
                assertion_rows.append(aa)
                assertion_audit_by_key[(ent.file, ent.start, ent.end)] = aa

            entities.append(ent)

    # collisions
    collision_rows = find_type_collisions(entities)
    collision_keys: set[tuple[str, int, int]] = set()
    for r in collision_rows:
        if r["file"] == "*":
            continue
        if r["span_a"]:
            a0, a1 = map(int, r["span_a"].split("-"))
            collision_keys.add((r["file"], a0, a1))
        if r["span_b"]:
            b0, b1 = map(int, r["span_b"].split("-"))
            collision_keys.add((r["file"], b0, b1))

    # risk scoring
    for ent in entities:
        k = (ent.file, ent.start, ent.end)
        score_entity_risk(
            ent,
            test_audit_by_key.get(k),
            result_audit_by_key.get(k),
            drug_audit_by_key.get(k),
            symptom_audit_by_key.get(k),
            diag_audit_by_key.get(k),
            assertion_audit_by_key.get(k),
            k in collision_keys,
        )
        if ent.risk_score >= 3:
            source_flagged[ent.source_component] += 1
        inventory_rows.append(
            {
                "file": ent.file,
                "start": ent.start,
                "end": ent.end,
                "text": ent.text,
                "type": ent.type,
                "assertions": "|".join(ent.assertions),
                "candidates": "|".join(ent.candidates),
                "candidate_count": len(ent.candidates),
                "section": ent.section,
                "source_component": ent.source_component,
                "trace_provenance": ent.trace_provenance,
                "length_characters": ent.length_characters,
                "length_words": ent.length_words,
                "contains_newline": ent.contains_newline,
            }
        )

    # write inventory
    _write_tsv(
        out_dir / "entity_inventory.tsv",
        inventory_rows,
        [
            "file",
            "start",
            "end",
            "text",
            "type",
            "assertions",
            "candidates",
            "candidate_count",
            "section",
            "source_component",
            "trace_provenance",
            "length_characters",
            "length_words",
            "contains_newline",
        ],
    )

    # density report
    per_doc = Counter(e.file for e in entities)
    counts = sorted(per_doc.values())
    by_type_docs: dict[str, set[str]] = defaultdict(set)
    by_type_lens: dict[str, list[int]] = defaultdict(list)
    by_type_per_doc: dict[str, Counter[str]] = defaultdict(Counter)
    for e in entities:
        by_type_docs[e.type].add(e.file)
        by_type_lens[e.type].append(e.length_characters)
        by_type_per_doc[e.type][e.file] += 1

    density_lines = [
        "# Entity density",
        "",
        f"- Total entities (base-v7 snapshot): **{len(entities)}**",
        f"- Documents: **{len(per_doc)}**",
        f"- Min / median / mean / max per document: "
        f"**{min(counts)} / {statistics.median(counts)} / {statistics.mean(counts):.2f} / {max(counts)}**",
        "",
        "Note: ~3,236 entities / 100 docs is high relative to typical clinical notes, "
        "but density alone is not proof of over-extraction — see type audits.",
        "",
        "## By type",
        "",
        "| Type | Count | Docs containing | Mean/doc | Median/doc | Len p50 | Len p90 |",
        "|------|------:|----------------:|---------:|-----------:|-------:|-------:|",
    ]
    for t in sorted(by_type_docs.keys()):
        per = list(by_type_per_doc[t].values())
        # include zeros for docs without type? use only docs containing for median of positive,
        # but mean per doc over 100
        mean_all = type_counter[t] / 100.0
        med_pos = statistics.median(per) if per else 0
        lens = sorted(by_type_lens[t])
        density_lines.append(
            f"| {t} | {type_counter[t]} | {len(by_type_docs[t])} | {mean_all:.2f} | "
            f"{med_pos} | {_percentile(lens, 0.5):.0f} | {_percentile(lens, 0.9):.0f} |"
        )
    (out_dir / "entity_density.md").write_text("\n".join(density_lines) + "\n", encoding="utf-8")

    # provenance summary
    prov_rows = []
    for src in sorted(set(introduced) | set(surviving) | {"UNRESOLVED"}):
        lenses = source_lens.get(src, [])
        cov = source_cand_cov.get(src, [])
        prov_rows.append(
            {
                "source_component": src,
                "entities_introduced": introduced.get(src, 0),
                "entities_surviving_final": surviving.get(src, 0),
                "type_distribution": json.dumps(dict(source_types.get(src, {})), ensure_ascii=False),
                "mean_span_length": round(statistics.mean(lenses), 2) if lenses else "",
                "assertion_distribution": json.dumps(
                    dict(source_assertions.get(src, {})), ensure_ascii=False
                ),
                "candidate_coverage_rate": round(statistics.mean(cov), 3) if cov else "",
                "flagged_by_schema_checks": source_flagged.get(src, 0),
            }
        )
    _write_tsv(
        out_dir / "provenance_summary.tsv",
        prov_rows,
        [
            "source_component",
            "entities_introduced",
            "entities_surviving_final",
            "type_distribution",
            "mean_span_length",
            "assertion_distribution",
            "candidate_coverage_rate",
            "flagged_by_schema_checks",
        ],
    )

    _write_tsv(
        out_dir / "test_name_audit.tsv",
        test_rows,
        [
            "file",
            "text",
            "position",
            "section",
            "left_context",
            "right_context",
            "source_component",
            "procedure_cues",
            "test_cues",
            "risk_status",
            "risk_reasons",
        ],
    )
    _write_tsv(
        out_dir / "test_result_audit.tsv",
        result_rows,
        [
            "file",
            "text",
            "position",
            "section",
            "left_context",
            "right_context",
            "source_component",
            "result_class",
            "contains_test_name_cue",
        ],
    )
    _write_tsv(
        out_dir / "drug_span_audit.tsv",
        drug_rows,
        [
            "file",
            "text",
            "position",
            "section",
            "left_context",
            "right_context",
            "source_component",
            "has_strength",
            "has_dose",
            "has_route",
            "has_frequency",
            "has_prn",
            "has_dose_form",
            "details_available_nearby",
            "span_class",
            "candidates",
            "candidate_count",
        ],
    )
    _write_tsv(
        out_dir / "symptom_span_audit.tsv",
        symptom_rows,
        [
            "file",
            "text",
            "position",
            "section",
            "left_context",
            "right_context",
            "source_component",
            "span_class",
            "reasons",
            "assertions",
            "length_words",
        ],
    )
    _write_tsv(
        out_dir / "diagnosis_span_audit.tsv",
        diag_rows,
        [
            "file",
            "text",
            "position",
            "section",
            "section_origin",
            "left_context",
            "right_context",
            "source_component",
            "flags",
            "candidates",
            "candidate_count",
        ],
    )
    _write_tsv(
        out_dir / "type_collisions.tsv",
        collision_rows,
        [
            "file",
            "kind",
            "text_a",
            "type_a",
            "span_a",
            "text_b",
            "type_b",
            "span_b",
            "pair",
        ],
    )
    # strip helper keys for assertion tsv
    assertion_out = []
    for r in assertion_rows:
        assertion_out.append({k: v for k, v in r.items() if not k.startswith("_")})
    _write_tsv(
        out_dir / "assertion_audit.tsv",
        assertion_out,
        [
            "file",
            "text",
            "type",
            "section",
            "local_sentence",
            "assertions",
            "negation_cue",
            "family_cue",
            "history_cue",
            "temporal_cue",
            "assertion_risk",
            "source_component",
        ],
    )
    _write_tsv(
        out_dir / "diagnosis_candidate_audit.tsv",
        diag_cand_rows,
        [
            "file",
            "entity_text",
            "position",
            "current_candidates",
            "current_candidate_count",
            "candidate_terms",
            "candidate_hierarchy",
            "top_local_icd_alternatives",
            "similarity_values",
            "section",
            "local_support",
            "trace_diagnosis_similarity",
            "source_component",
        ],
    )
    multi_icd_rows.sort(key=lambda r: (-int(r["multi_score"]), r["file"]))
    multi_short = multi_icd_rows[:100]
    _write_tsv(
        out_dir / "multi_icd_candidate_review.tsv",
        multi_short,
        [
            "file",
            "entity_text",
            "position",
            "current_candidates",
            "multi_score",
            "local_support",
            "top_local_icd_alternatives",
            "section",
            "reason",
        ],
    )
    _write_tsv(
        out_dir / "drug_candidate_audit.tsv",
        drug_cand_rows,
        [
            "file",
            "text",
            "position",
            "candidates",
            "candidate_count",
            "candidate_tty",
            "ingredient_vs_clinical",
            "strength_aware",
            "brand_aware",
            "unlinked",
            "source_component",
            "drug_similarity",
        ],
    )

    risk_rows = []
    for ent in sorted(entities, key=lambda e: (-e.risk_score, e.file, e.start)):
        risk_rows.append(
            {
                "file": ent.file,
                "start": ent.start,
                "end": ent.end,
                "text": ent.text,
                "type": ent.type,
                "source_component": ent.source_component,
                "risk_score": ent.risk_score,
                "risk_reasons": "|".join(ent.risk_reasons),
                "assertions": "|".join(ent.assertions),
                "candidates": "|".join(ent.candidates),
                "section": ent.section,
            }
        )
    _write_tsv(
        out_dir / "entity_risk_ranking.tsv",
        risk_rows,
        [
            "file",
            "start",
            "end",
            "text",
            "type",
            "source_component",
            "risk_score",
            "risk_reasons",
            "assertions",
            "candidates",
            "section",
        ],
    )

    pool = build_annotation_pool(
        entities,
        test_rows,
        result_rows,
        symptom_rows,
        diag_rows,
        drug_rows,
        assertion_rows,
        multi_short,
        v10_repl_keys,
        docs,
    )
    _write_csv(
        out_dir / "annotation_pool.csv",
        pool,
        [
            "item_id",
            "file",
            "full_context",
            "current_text",
            "current_start",
            "current_end",
            "current_type",
            "current_assertions",
            "current_candidates",
            "source_component",
            "risk_categories",
            "risk_score",
            "human_keep",
            "human_corrected_text",
            "human_corrected_start",
            "human_corrected_end",
            "human_corrected_type",
            "human_corrected_assertions",
            "human_corrected_candidates",
            "human_notes",
        ],
    )

    # summary json for downstream report builders
    def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
        return dict(Counter(str(r.get(key, "")) for r in rows))

    summary = {
        "total_entities": len(entities),
        "per_doc": {
            "min": min(counts),
            "median": statistics.median(counts),
            "mean": statistics.mean(counts),
            "max": max(counts),
        },
        "type_counts": dict(type_counter),
        "provenance_surviving": dict(surviving),
        "provenance_flagged": dict(source_flagged),
        "test_name_status": count_by(test_rows, "risk_status"),
        "test_result_class": count_by(result_rows, "result_class"),
        "drug_span_class": count_by(drug_rows, "span_class"),
        "symptom_span_class": count_by(symptom_rows, "span_class"),
        "diagnosis_flags": count_by(diag_rows, "flags"),
        "collision_kinds": count_by(collision_rows, "kind"),
        "collision_pairs": count_by(
            [r for r in collision_rows if r["file"] != "*"], "pair"
        ),
        "assertion_risk": count_by(assertion_rows, "assertion_risk"),
        "isFamily_count": sum(1 for e in entities if "isFamily" in e.assertions),
        "isFamily_with_evidence": sum(
            1
            for r in assertion_rows
            if "isFamily" in str(r.get("assertions", "")) and r.get("family_cue")
        ),
        "diag_candidate_count_dist": dict(
            Counter(len(e.candidates) for e in entities if e.type == TYPE_DIAG)
        ),
        "drug_candidate_count_dist": dict(
            Counter(len(e.candidates) for e in entities if e.type == TYPE_DRUG)
        ),
        "multi_icd_shortlist": len(multi_short),
        "annotation_pool_rows": len(pool),
        "annotation_pool_categories": dict(
            Counter(
                c
                for r in pool
                for c in str(r.get("risk_categories", "")).split("|")
                if c
            )
        ),
        "top_risk": risk_rows[:100],
        "unresolved_surviving": surviving.get("UNRESOLVED", 0),
    }
    (out_dir / "_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: summary[k] for k in summary if k != "top_risk"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
