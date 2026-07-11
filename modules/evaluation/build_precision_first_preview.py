#!/usr/bin/env python3
"""Offline precision-first preview (NOT a pipeline / NOT for submission).

Starts from frozen base-v7 snapshot and removes only extremely high-confidence
schema violations. Does not change types, candidates, or assertions.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

TYPE_TEST = "TÊN_XÉT_NGHIỆM"
TYPE_SYMPTOM = "TRIỆU_CHỨNG"

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
    "ghép",
    "nạo",
    "chọc",
    "cắt",
    "shunt",
    "stent",
    "catheter",
    "sonde",
]
GENERIC_STATUS = [
    "bệnh nhân tỉnh",
    "tiếp xúc tốt",
    "tỉnh táo",
    "da niêm mạc hồng",
    "toàn trạng ổn",
    "ổn định",
]
SECTION_HEADING_LIKE = re.compile(
    r"^(tiền sử|bệnh sử|khám|chẩn đoán|điều trị|xử trí|thuốc|"
    r"các xét nghiệm|kết quả|diễn biến|tóm tắt|các thủ thuật)",
    re.I,
)


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"\s+", " ", s).strip()


def _context(text: str, start: int, end: int, window: int = 50) -> str:
    left = text[max(0, start - window) : start]
    right = text[end : min(len(text), end + window)]
    return (left + "⟦" + text[start:end] + "⟧" + right).replace("\n", " ")


def load_provenance(inventory: Path) -> dict[tuple[str, int, int], str]:
    if not inventory.exists():
        return {}
    out: dict[tuple[str, int, int], str] = {}
    with inventory.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            try:
                key = (row["file"], int(row["start"]), int(row["end"]))
            except Exception:
                continue
            out[key] = row.get("source_component", "UNRESOLVED")
    return out


def removal_reason(ent: dict[str, Any], doc: str) -> tuple[str, str] | None:
    """Return (reason, rule) or None if keep."""
    text = str(ent.get("text", ""))
    typ = str(ent.get("type", ""))
    start, end = int(ent["position"][0]), int(ent["position"][1])
    text_f = _fold(text)

    if end <= start or not text.strip():
        return "empty_or_malformed_entity", "invalid_span"
    if doc and (start < 0 or end > len(doc) or doc[start:end] != text):
        # only flag when doc available and mismatch is clear
        if start < 0 or end > len(doc):
            return "invalid_span", "offset_out_of_bounds"
        if doc[start:end] != text:
            return "invalid_span", "text_offset_mismatch"

    if typ == TYPE_TEST:
        if "đặt shunt dẫn lưu tĩnh mạch cửa qua da" in text_f:
            return "procedure-like phrase typed as TÊN_XÉT_NGHIỆM", "required_procedure_example"
        cue_hits = [c for c in PROCEDURE_CUES if c in text_f]
        # high-confidence: procedure cue present and no obvious lab token
        labish = any(
            k in text_f
            for k in ["xét nghiệm", "wbc", "creatinin", "kali", "inr", "ecg", "mri"]
        )
        if cue_hits and not labish:
            # require strong cues (not bare 'cắt' in unrelated words unless multiword)
            strong = [
                c
                for c in cue_hits
                if c
                in {
                    "đặt stent",
                    "đặt shunt",
                    "đặt catheter",
                    "đặt sonde",
                    "đặt ống",
                    "phẫu thuật",
                    "dẫn lưu",
                    "can thiệp",
                    "ghép",
                    "thay van",
                    "shunt",
                    "stent",
                    "catheter",
                    "sonde",
                }
                or text_f.startswith(c + " ")
                or text_f.startswith(c)
            ]
            if strong:
                return (
                    "procedure-like phrase typed as TÊN_XÉT_NGHIỆM",
                    "procedure_cue:" + "|".join(strong),
                )

    if typ == TYPE_SYMPTOM:
        if any(g == text_f or g in text_f for g in GENERIC_STATUS):
            if len(text.split()) <= 6:
                return "generic patient status typed as TRIỆU_CHỨNG", "generic_status"

    if SECTION_HEADING_LIKE.search(text.strip()) and len(text.split()) <= 5:
        # only if looks like a heading (short, no digits/units)
        if not re.search(r"\d", text):
            return "obvious section heading", "section_heading_like"

    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--base-dir",
        type=Path,
        default=ROOT / "output/v10_llm_conflict_resolution/base_v7_snapshot",
    )
    ap.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "v_dataset/var/test",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "output/schema_audit/precision_first_preview",
    )
    ap.add_argument(
        "--analysis-dir",
        type=Path,
        default=ROOT / "analysis/schema_audit",
    )
    args = ap.parse_args()

    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    provenance = load_provenance(args.analysis_dir / "entity_inventory.tsv")
    docs = {
        p.stem: p.read_text(encoding="utf-8")
        for p in args.input_dir.glob("*.txt")
    }

    removals: list[dict[str, Any]] = []
    base_total = 0
    remain_total = 0
    rem_by_type: Counter[str] = Counter()
    rem_by_src: Counter[str] = Counter()
    rem_by_section: Counter[str] = Counter()

    for path in sorted(args.base_dir.glob("*.json"), key=lambda p: int(p.stem)):
        file_id = path.stem
        doc = docs.get(file_id, "")
        ents = json.loads(path.read_text(encoding="utf-8"))
        base_total += len(ents)
        kept: list[dict[str, Any]] = []
        for ent in ents:
            start, end = int(ent["position"][0]), int(ent["position"][1])
            reason = removal_reason(ent, doc)
            if reason is None:
                kept.append(ent)
                continue
            why, rule = reason
            src = provenance.get((file_id, start, end), "UNRESOLVED")
            # section guess
            section = ""
            prefix = doc[:start]
            for line in reversed(prefix.split("\n")):
                s = line.strip()
                if s and (s.endswith(":") or len(s) <= 80):
                    section = s[:120]
                    break
            rem_by_type[str(ent.get("type", ""))] += 1
            rem_by_src[src] += 1
            rem_by_section[section or "(none)"] += 1
            removals.append(
                {
                    "file": file_id,
                    "text": ent.get("text", ""),
                    "type": ent.get("type", ""),
                    "start": start,
                    "end": end,
                    "context": _context(doc, start, end) if doc else "",
                    "reason": why,
                    "rule": rule,
                    "source_component": src,
                    "section": section,
                }
            )
        remain_total += len(kept)
        (args.out_dir / f"{file_id}.json").write_text(
            json.dumps(kept, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    rem_path = args.analysis_dir / "precision_first_removals.tsv"
    args.analysis_dir.mkdir(parents=True, exist_ok=True)
    with rem_path.open("w", encoding="utf-8", newline="") as f:
        fields = [
            "file",
            "text",
            "type",
            "start",
            "end",
            "context",
            "reason",
            "rule",
            "source_component",
            "section",
        ]
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        for row in removals:
            w.writerow({k: row.get(k, "") for k in fields})

    summary = {
        "base_entity_count": base_total,
        "removed_entity_count": len(removals),
        "remaining_entity_count": remain_total,
        "removals_by_type": dict(rem_by_type),
        "removals_by_source_component": dict(rem_by_src),
        "removals_by_section_top": dict(rem_by_section.most_common(30)),
        "output_dir": str(args.out_dir),
        "removals_tsv": str(rem_path),
    }
    (args.analysis_dir / "precision_first_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
