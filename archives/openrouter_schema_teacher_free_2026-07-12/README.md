# Archive — `openrouter_schema_teacher` / `free_first` (2026-07-12)

**Permanent snapshot of a long, non-reproducible OpenRouter free-tier teacher run.**

| Field | Value |
|-------|-------|
| Compliance | `EXTERNAL_API_DIAGNOSTIC_ONLY` |
| Reproducible | **No** — free models / 429 / JSON flake; do not expect bit-identical reruns |
| Docs / entities | **100 / 2213** |
| Verdict | `FREE_ENSEMBLE_PARTIALLY_CORRECT_SCHEMA` |
| Gold manifest SHA256 | `c601c9f66d4e49d107c975aa74cc59c40d0f0802456c3201c5eafe6693de8aaf` |

## Why this archive exists

`output/` and `cache/` are gitignored. Free OpenRouter runs are long and not reliably reproducible.
This directory is the **git-tracked** permanent record of:

1. Final diagnostic pseudo-gold (`diagnostic_pseudo_gold/`)
2. Comparison + report (`analysis/`)
3. Run logs / usage (`logs/`)
4. Integrity + handoff (`meta/`)

Live working copies may still exist under `output/openrouter_schema_teacher_free/` and
`analysis/openrouter_teacher_free/`; **this archive wins** if they diverge.

## Layout

```text
archives/openrouter_schema_teacher_free_2026-07-12/
  README.md                          ← this file
  diagnostic_pseudo_gold/{1..100}.json
  analysis/                          ← final_report, schema_metrics, comparison TSV
  logs/                              ← full_results, pilot_*, full_only.log, 29_error
  meta/
    archive_manifest.json
    gold_sha256.txt                  ← per-file SHA256
    CURRENT_WORK_at_archive.md       ← handoff frozen at archive time
    EXTERNAL_API_DIAGNOSTIC_ONLY.md
```

## Models (all $0 at run time)

| Role | Model |
|------|-------|
| A | `tencent/hy3:free` |
| B | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| C | `poolside/laguna-m.1:free` |
| Judge | `tencent/hy3:free` |

## Do not

- Submit these entities as a competition ZIP
- Train a final competition model on them without organizer confirmation
- Treat a re-run as a replacement unless intentionally regenerating a **new** dated archive

## Read first

- `analysis/final_report.md`
- `meta/archive_manifest.json`
- `meta/CURRENT_WORK_at_archive.md`
