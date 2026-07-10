from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.components.postprocessing.ontology_drug_recall import (  # noqa: E402
    compact_with_map,
    normalize_with_map,
)
from modules.core.config import ProjectPaths  # noqa: E402
from modules.core.ids import normalize_rxcui  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Audit RxNorm short_drug.csv alias→RxCUI ambiguity."
    )
    p.add_argument(
        "--dictionary",
        type=Path,
        default=ProjectPaths().viettel_base_dir / "short_drug.csv",
    )
    p.add_argument(
        "--analysis-dir",
        type=Path,
        default=PROJECT_ROOT / "analysis",
    )
    return p.parse_args()


def audit(dictionary_path: Path, analysis_dir: Path) -> dict:
    analysis_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(
        dictionary_path,
        dtype=str,
        keep_default_na=False,
        usecols=lambda c: c in {"term", "rxcui", "tty"},
    )
    if "tty" not in df.columns:
        df["tty"] = ""

    total_rows = len(df)
    unique_raw_terms: set[str] = set()
    unique_rxcuis: set[str] = set()

    # alias -> sets
    norm_to_rxcuis: dict[str, set[str]] = defaultdict(set)
    compact_to_rxcuis: dict[str, set[str]] = defaultdict(set)
    norm_to_ttys: dict[str, set[str]] = defaultdict(set)
    compact_to_ttys: dict[str, set[str]] = defaultdict(set)
    norm_to_terms: dict[str, set[str]] = defaultdict(set)
    compact_to_terms: dict[str, set[str]] = defaultdict(set)
    # for TSV we also want compact of each norm alias
    norm_to_compact: dict[str, str] = {}

    tty_ambiguity: dict[str, dict[str, int]] = defaultdict(
        lambda: {"unique_aliases": 0, "unambiguous": 0, "ambiguous": 0}
    )
    # per-tty: alias(norm) -> rxcuis
    tty_norm_to_rxcuis: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )

    for row in df.itertuples(index=False):
        term = str(getattr(row, "term", "") or "").strip()
        rxcui = normalize_rxcui(getattr(row, "rxcui", ""))
        tty = str(getattr(row, "tty", "") or "").strip()
        if not term or term.lower() == "nan" or rxcui is None:
            continue
        unique_raw_terms.add(term)
        unique_rxcuis.add(rxcui)

        norm, nmap = normalize_with_map(term)
        if not norm:
            continue
        compact, _ = compact_with_map(norm, nmap if nmap else list(range(len(norm))))
        if not compact:
            compact = norm.replace(" ", "")

        norm_to_rxcuis[norm].add(rxcui)
        compact_to_rxcuis[compact].add(rxcui)
        norm_to_ttys[norm].add(tty)
        compact_to_ttys[compact].add(tty)
        norm_to_terms[norm].add(term)
        compact_to_terms[compact].add(term)
        norm_to_compact[norm] = compact
        tty_norm_to_rxcuis[tty or "(missing)"][norm].add(rxcui)

    unique_normalized = len(norm_to_rxcuis)
    unique_compact = len(compact_to_rxcuis)

    norm_unambiguous = sum(1 for s in norm_to_rxcuis.values() if len(s) == 1)
    norm_ambiguous = sum(1 for s in norm_to_rxcuis.values() if len(s) > 1)
    compact_unambiguous = sum(1 for s in compact_to_rxcuis.values() if len(s) == 1)
    compact_ambiguous = sum(1 for s in compact_to_rxcuis.values() if len(s) > 1)

    for tty, alias_map in tty_norm_to_rxcuis.items():
        tty_ambiguity[tty]["unique_aliases"] = len(alias_map)
        tty_ambiguity[tty]["unambiguous"] = sum(
            1 for s in alias_map.values() if len(s) == 1
        )
        tty_ambiguity[tty]["ambiguous"] = sum(
            1 for s in alias_map.values() if len(s) > 1
        )

    # Ambiguous TSV: prefer compact-level ambiguity (matching index uses compact
    # dedup), but also include normalized aliases that map to >1 RxCUI.
    ambiguous_rows: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()

    for compact, rxcuis in compact_to_rxcuis.items():
        if len(rxcuis) <= 1:
            continue
        # pick a representative normalized alias if any maps to this compact
        norm_alias = ""
        for n, c in norm_to_compact.items():
            if c == compact:
                norm_alias = n
                break
        key = (norm_alias or compact, compact)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        ambiguous_rows.append(
            {
                "alias": sorted(compact_to_terms[compact])[0]
                if compact_to_terms[compact]
                else compact,
                "normalized_alias": norm_alias,
                "compact_alias": compact,
                "rxcui_count": len(rxcuis),
                "rxcuis": "|".join(sorted(rxcuis)),
                "ttys": "|".join(sorted(t for t in compact_to_ttys[compact] if t)),
                "original_terms": "|".join(sorted(compact_to_terms[compact])),
            }
        )

    for norm, rxcuis in norm_to_rxcuis.items():
        if len(rxcuis) <= 1:
            continue
        compact = norm_to_compact.get(norm, norm.replace(" ", ""))
        key = (norm, compact)
        if key in seen_keys:
            continue
        # only add if not already covered via compact ambiguity with same IDs
        seen_keys.add(key)
        ambiguous_rows.append(
            {
                "alias": sorted(norm_to_terms[norm])[0] if norm_to_terms[norm] else norm,
                "normalized_alias": norm,
                "compact_alias": compact,
                "rxcui_count": len(rxcuis),
                "rxcuis": "|".join(sorted(rxcuis)),
                "ttys": "|".join(sorted(t for t in norm_to_ttys[norm] if t)),
                "original_terms": "|".join(sorted(norm_to_terms[norm])),
            }
        )

    ambiguous_rows.sort(key=lambda r: (-int(r["rxcui_count"]), r["compact_alias"]))

    tsv_path = analysis_dir / "ambiguous_drug_aliases.tsv"
    headers = [
        "alias",
        "normalized_alias",
        "compact_alias",
        "rxcui_count",
        "rxcuis",
        "ttys",
        "original_terms",
    ]
    with tsv_path.open("w", encoding="utf-8") as f:
        f.write("\t".join(headers) + "\n")
        for row in ambiguous_rows:
            f.write(
                "\t".join(
                    str(row[h]).replace("\t", " ").replace("\n", " ") for h in headers
                )
                + "\n"
            )

    report = {
        "dictionary": str(dictionary_path),
        "total_rows": total_rows,
        "unique_raw_terms": len(unique_raw_terms),
        "unique_normalized_aliases": unique_normalized,
        "unique_compact_aliases": unique_compact,
        "unique_rxcuis": len(unique_rxcuis),
        "normalized_aliases_mapping_to_exactly_1_rxcui": norm_unambiguous,
        "normalized_aliases_mapping_to_gt1_rxcui": norm_ambiguous,
        "compact_aliases_mapping_to_exactly_1_rxcui": compact_unambiguous,
        "compact_aliases_mapping_to_gt1_rxcui": compact_ambiguous,
        "ambiguity_by_tty": dict(tty_ambiguity),
        "ambiguous_alias_count_exported": len(ambiguous_rows),
        "examples": {
            "alias_to_one_rxcui": [],
            "alias_to_multiple_rxcuis": [],
        },
    }

    # examples
    for norm, rxcuis in sorted(norm_to_rxcuis.items(), key=lambda x: x[0]):
        if len(rxcuis) == 1 and len(report["examples"]["alias_to_one_rxcui"]) < 5:
            report["examples"]["alias_to_one_rxcui"].append(
                {"alias": norm, "rxcuis": sorted(rxcuis)}
            )
        if len(rxcuis) > 1 and len(report["examples"]["alias_to_multiple_rxcuis"]) < 5:
            report["examples"]["alias_to_multiple_rxcuis"].append(
                {"alias": norm, "rxcuis": sorted(rxcuis)}
            )
        if (
            len(report["examples"]["alias_to_one_rxcui"]) >= 5
            and len(report["examples"]["alias_to_multiple_rxcuis"]) >= 5
        ):
            break

    json_path = analysis_dir / "drug_alias_audit.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {tsv_path} ({len(ambiguous_rows)} rows)")
    return report


def main() -> None:
    args = parse_args()
    audit(args.dictionary, args.analysis_dir)


if __name__ == "__main__":
    main()
