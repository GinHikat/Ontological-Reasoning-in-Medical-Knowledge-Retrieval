from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.evaluation.analyze_outputs import analyze_run, resolve_submission_dir

CONTEXT = 50


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compare two pipeline output folders.")
    p.add_argument("--input-dir", type=Path, default=PROJECT_ROOT / "v_dataset" / "var" / "test")
    p.add_argument("--v6-dir", type=Path, required=True)
    p.add_argument("--v7-dir", type=Path, required=True)
    p.add_argument("--analysis-dir", type=Path, default=PROJECT_ROOT / "analysis")
    p.add_argument("--v6-name", type=str, default="v6_refined")
    p.add_argument("--v7-name", type=str, default="v7_structured")
    p.add_argument(
        "--focus-files",
        type=str,
        default="87,88,89,90,91,92,93,94,96,97,99,100",
    )
    return p.parse_args()


def _load_map(output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    result = {}
    submission_dir = resolve_submission_dir(output_dir)
    for path in sorted(submission_dir.glob("*.json")):
        result[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _key(ent: dict[str, Any]) -> tuple:
    pos = ent.get("position") or [None, None]
    return (pos[0], pos[1], ent.get("text", ""), ent.get("type", ""))


def _span_key(ent: dict[str, Any]) -> tuple:
    pos = ent.get("position") or [None, None]
    return (pos[0], pos[1])


def _ctx(text: str, start: int, end: int) -> str:
    left = text[max(0, start - CONTEXT) : start].replace("\n", " ")
    right = text[end : min(len(text), end + CONTEXT)].replace("\n", " ")
    return f"...{left}[{text[start:end]}]{right}..."


def _write_tsv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write("\t".join(headers) + "\n")
        for row in rows:
            f.write(
                "\t".join(
                    str(row.get(h, "")).replace("\t", " ").replace("\n", " ")
                    for h in headers
                )
                + "\n"
            )


def compare(args: argparse.Namespace) -> None:
    analysis_dir = args.analysis_dir
    analysis_dir.mkdir(parents=True, exist_ok=True)

    s6 = analyze_run(args.input_dir, args.v6_dir, analysis_dir, args.v6_name)
    s7 = analyze_run(args.input_dir, args.v7_dir, analysis_dir, args.v7_name)

    m6 = _load_map(args.v6_dir)
    m7 = _load_map(args.v7_dir)
    files = sorted(set(m6) | set(m7))

    new_rows = []
    removed_rows = []
    changed_rows = []

    stats = {
        "new_entities_only_in_v7": 0,
        "entities_removed_from_v6": 0,
        "same_spans_changed_labels": 0,
        "same_spans_changed_candidates": 0,
        "same_spans_changed_assertions": 0,
    }

    for stem in files:
        text_path = args.input_dir / f"{stem}.txt"
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        e6 = m6.get(stem, [])
        e7 = m7.get(stem, [])
        map6 = {_span_key(e): e for e in e6}
        map7 = {_span_key(e): e for e in e7}
        # For duplicates keep last
        for e in e6:
            map6[_span_key(e)] = e
        for e in e7:
            map7[_span_key(e)] = e

        keys6 = set(map6)
        keys7 = set(map7)

        for k in keys7 - keys6:
            e = map7[k]
            start, end = k
            stats["new_entities_only_in_v7"] += 1
            new_rows.append(
                {
                    "file": stem,
                    "start": start,
                    "end": end,
                    "text": e.get("text", ""),
                    "type": e.get("type", ""),
                    "candidates": "|".join(e.get("candidates") or []),
                    "assertions": "|".join(e.get("assertions") or []),
                    "context": _ctx(text, int(start or 0), int(end or 0))
                    if start is not None and end is not None
                    else "",
                }
            )

        for k in keys6 - keys7:
            e = map6[k]
            start, end = k
            stats["entities_removed_from_v6"] += 1
            removed_rows.append(
                {
                    "file": stem,
                    "start": start,
                    "end": end,
                    "text": e.get("text", ""),
                    "type": e.get("type", ""),
                    "candidates": "|".join(e.get("candidates") or []),
                    "assertions": "|".join(e.get("assertions") or []),
                    "context": _ctx(text, int(start or 0), int(end or 0))
                    if start is not None and end is not None
                    else "",
                }
            )

        for k in keys6 & keys7:
            a, b = map6[k], map7[k]
            changes = []
            if a.get("type") != b.get("type"):
                stats["same_spans_changed_labels"] += 1
                changes.append(f"type:{a.get('type')}->{b.get('type')}")
            if (a.get("candidates") or []) != (b.get("candidates") or []):
                stats["same_spans_changed_candidates"] += 1
                changes.append(
                    f"candidates:{a.get('candidates')}->{b.get('candidates')}"
                )
            if (a.get("assertions") or []) != (b.get("assertions") or []):
                stats["same_spans_changed_assertions"] += 1
                changes.append(
                    f"assertions:{a.get('assertions')}->{b.get('assertions')}"
                )
            if changes:
                start, end = k
                changed_rows.append(
                    {
                        "file": stem,
                        "start": start,
                        "end": end,
                        "text": b.get("text", a.get("text", "")),
                        "v6_type": a.get("type", ""),
                        "v7_type": b.get("type", ""),
                        "v6_candidates": "|".join(a.get("candidates") or []),
                        "v7_candidates": "|".join(b.get("candidates") or []),
                        "v6_assertions": "|".join(a.get("assertions") or []),
                        "v7_assertions": "|".join(b.get("assertions") or []),
                        "changes": ";".join(changes),
                        "context": _ctx(text, int(start or 0), int(end or 0))
                        if start is not None and end is not None
                        else "",
                    }
                )

    headers_new = [
        "file",
        "start",
        "end",
        "text",
        "type",
        "candidates",
        "assertions",
        "context",
    ]
    _write_tsv(analysis_dir / "v7_new_entities.tsv", new_rows, headers_new)
    _write_tsv(analysis_dir / "v7_removed_entities.tsv", removed_rows, headers_new)
    _write_tsv(
        analysis_dir / "v7_changed_entities.tsv",
        changed_rows,
        [
            "file",
            "start",
            "end",
            "text",
            "v6_type",
            "v7_type",
            "v6_candidates",
            "v7_candidates",
            "v6_assertions",
            "v7_assertions",
            "changes",
            "context",
        ],
    )

    report = []
    report.append("# v6 vs v7 diagnostic comparison\n")
    report.append("## Totals\n")
    report.append("| Metric | v6_refined | v7_structured |")
    report.append("|---|---:|---:|")
    report.append(
        f"| total entities | {s6['total_entities']} | {s7['total_entities']} |"
    )
    for t, c6 in s6["count_by_type"].items():
        report.append(f"| {t} | {c6} | {s7['count_by_type'].get(t, 0)} |")
    report.append(
        f"| diagnosis with candidates | {s6['diagnosis']['with_candidates']} | {s7['diagnosis']['with_candidates']} |"
    )
    report.append(
        f"| diagnosis without candidates | {s6['diagnosis']['without_candidates']} | {s7['diagnosis']['without_candidates']} |"
    )
    report.append(
        f"| drug with candidates | {s6['drug']['with_candidates']} | {s7['drug']['with_candidates']} |"
    )
    report.append(
        f"| drug without candidates | {s6['drug']['without_candidates']} | {s7['drug']['without_candidates']} |"
    )
    for a in ("isHistorical", "isNegated", "isFamily"):
        report.append(
            f"| assertion {a} | {s6['assertions'][a]} | {s7['assertions'][a]} |"
        )
    for k in (
        "text_mismatch",
        "invalid_start_end",
        "zero_length",
        "duplicate_exact_spans",
        "overlapping_spans",
        "nested_spans",
    ):
        report.append(
            f"| span {k} | {s6['span_quality'][k]} | {s7['span_quality'][k]} |"
        )

    report.append("\n## v7 relative to v6\n")
    for k, v in stats.items():
        report.append(f"- **{k}**: {v}")

    report_path = analysis_dir / "v6_vs_v7.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(report_path.read_text(encoding="utf-8"))

    # Focus sanity report
    focus = [x.strip() for x in args.focus_files.split(",") if x.strip()]
    focus_lines = ["# Focus file sanity inspection\n"]
    for stem in focus:
        text_path = args.input_dir / f"{stem}.txt"
        if not text_path.exists():
            continue
        text = text_path.read_text(encoding="utf-8")
        e6 = m6.get(stem, [])
        e7 = m7.get(stem, [])
        map6 = {_span_key(e): e for e in e6}
        map7 = {_span_key(e): e for e in e7}
        for e in e6:
            map6[_span_key(e)] = e
        for e in e7:
            map7[_span_key(e)] = e
        keys6, keys7 = set(map6), set(map7)
        focus_lines.append(f"## File {stem}\n")
        focus_lines.append("### Original text\n")
        focus_lines.append("```")
        focus_lines.append(text)
        focus_lines.append("```\n")
        focus_lines.append("### v6 predictions\n")
        for e in e6:
            focus_lines.append(
                f"- `{e.get('text')}` [{e.get('position')}] {e.get('type')} "
                f"cand={e.get('candidates')} asrt={e.get('assertions')}"
            )
        focus_lines.append("\n### v7 predictions\n")
        for e in e7:
            focus_lines.append(
                f"- `{e.get('text')}` [{e.get('position')}] {e.get('type')} "
                f"cand={e.get('candidates')} asrt={e.get('assertions')}"
            )
        focus_lines.append("\n### New in v7\n")
        for k in keys7 - keys6:
            e = map7[k]
            focus_lines.append(
                f"- `{e.get('text')}` [{e.get('position')}] {e.get('type')} "
                f"cand={e.get('candidates')} asrt={e.get('assertions')}"
            )
        focus_lines.append("\n### Removed from v6\n")
        for k in keys6 - keys7:
            e = map6[k]
            focus_lines.append(
                f"- `{e.get('text')}` [{e.get('position')}] {e.get('type')}"
            )
        focus_lines.append("\n### Changed\n")
        for k in keys6 & keys7:
            a, b = map6[k], map7[k]
            if (
                a.get("type") != b.get("type")
                or (a.get("candidates") or []) != (b.get("candidates") or [])
                or (a.get("assertions") or []) != (b.get("assertions") or [])
            ):
                focus_lines.append(
                    f"- `{b.get('text')}` type {a.get('type')}->{b.get('type')}; "
                    f"cand {a.get('candidates')}->{b.get('candidates')}; "
                    f"asrt {a.get('assertions')}->{b.get('assertions')}"
                )
        focus_lines.append("")

    focus_path = analysis_dir / "v6_vs_v7_focus.md"
    focus_path.write_text("\n".join(focus_lines) + "\n", encoding="utf-8")
    print(f"Wrote {focus_path}")


def main() -> None:
    compare(parse_args())


if __name__ == "__main__":
    main()
