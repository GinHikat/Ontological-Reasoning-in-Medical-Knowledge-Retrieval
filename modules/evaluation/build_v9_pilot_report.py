from __future__ import annotations

"""Build analysis/v9_pilot_report.md from LLM cache for pilot file stems."""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.components.postprocessing.llm_recall import document_sha256

DEFAULT_PILOT = [3, 13, 20, 41, 48, 70, 87, 89, 91, 93, 96, 100]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", type=Path, default=PROJECT_ROOT / "v_dataset" / "var" / "test")
    p.add_argument("--cache-dir", type=Path, default=PROJECT_ROOT / "cache" / "v9_llm_recall")
    p.add_argument("--analysis-dir", type=Path, default=PROJECT_ROOT / "analysis")
    p.add_argument(
        "--files",
        type=str,
        default=",".join(str(x) for x in DEFAULT_PILOT),
    )
    args = p.parse_args()
    args.analysis_dir.mkdir(parents=True, exist_ok=True)

    stems = [x.strip() for x in args.files.split(",") if x.strip()]
    totals = {
        "raw": 0,
        "aligned": 0,
        "align_fail": 0,
        "verifier_accepted": 0,
        "verifier_rejected": 0,
        "final_cache_accepted": 0,
    }
    all_final: list[dict] = []
    sections: list[str] = []

    for stem in stems:
        path = args.input_dir / f"{stem}.txt"
        sections.append(f"## File {stem}")
        if not path.exists():
            sections.append("MISSING INPUT")
            sections.append("")
            continue
        text = path.read_text(encoding="utf-8")
        sha = document_sha256(text)
        cache_path = args.cache_dir / f"{sha}.json"
        sections.append(f"- sha256: `{sha}`")
        if not cache_path.exists():
            sections.append("- cache: MISSING")
            sections.append("")
            continue
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        raw = cache.get("parsed_proposals") or []
        alignments = cache.get("alignment_results") or []
        aligned = [a for a in alignments if a.get("status") == "aligned"]
        align_fail = [a for a in alignments if a.get("status") != "aligned"]
        decisions = cache.get("verifier_decisions") or []
        accepted_dec = [d for d in decisions if d.get("accept")]
        rejected_dec = [d for d in decisions if not d.get("accept")]
        finals = cache.get("final_accepted_candidates") or []
        type_dis = (cache.get("diagnostics") or {}).get("type_disagreements") or []

        totals["raw"] += len(raw)
        totals["aligned"] += len(aligned)
        totals["align_fail"] += len(align_fail)
        totals["verifier_accepted"] += len(accepted_dec)
        totals["verifier_rejected"] += len(rejected_dec)
        totals["final_cache_accepted"] += len(finals)

        sections.append(f"- raw proposals: {len(raw)}")
        sections.append(f"- aligned: {len(aligned)}")
        sections.append(f"- alignment failures: {len(align_fail)}")
        sections.append(f"- verifier accept decisions: {len(accepted_dec)}")
        sections.append(f"- verifier reject decisions: {len(rejected_dec)}")
        sections.append(f"- type disagreements: {len(type_dis)}")
        sections.append(f"- final cache accepted: {len(finals)}")
        sections.append(f"- parse_failures: {cache.get('parse_failures')}")
        sections.append(f"- repair_used: {cache.get('repair_used')}")
        if align_fail:
            sections.append("- alignment failure detail:")
            for a in align_fail:
                sections.append(
                    f"  - {a.get('status')} L={a.get('line_id')} "
                    f"type={a.get('type')} text={a.get('text')!r} detail={a.get('detail')}"
                )
        sections.append("- final accepted candidates:")
        if not finals:
            sections.append("  - (none)")
        for c in finals:
            snippet = text[max(0, c["start"] - 40) : c["end"] + 40].replace("\n", " ")
            sections.append(
                f"  - [{c['start']}:{c['end']}] {c['type']}: `{c['text']}` "
                f"(line {c.get('line_id')}) ctx=`{snippet}`"
            )
            all_final.append({"file": stem, **c})
        sections.append("")

    body = [
        "# v9 pilot report",
        "",
        f"Pilot files: {', '.join(stems)}",
        "",
        "## Totals",
        f"- raw proposals: {totals['raw']}",
        f"- aligned proposals: {totals['aligned']}",
        f"- alignment failures: {totals['align_fail']}",
        f"- verifier accepted (raw decisions): {totals['verifier_accepted']}",
        f"- verifier rejected: {totals['verifier_rejected']}",
        f"- final cache accepted: {totals['final_cache_accepted']}",
        "",
        "## Manual review checklist",
        "Check especially for:",
        "- anatomy extracted as disease",
        "- procedures extracted as diagnosis",
        "- test names extracted as symptoms",
        "- whole sentences",
        "- leading negation",
        "- drug false positives",
        "",
        "## Every final addition",
    ]
    if not all_final:
        body.append("(none yet)")
    for c in all_final:
        body.append(
            f"- file {c['file']} [{c['start']}:{c['end']}] {c['type']}: `{c['text']}`"
        )
    body.append("")
    body.append("## Per-file detail")
    body.append("")
    body.extend(sections)

    out = args.analysis_dir / "v9_pilot_report.md"
    out.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
