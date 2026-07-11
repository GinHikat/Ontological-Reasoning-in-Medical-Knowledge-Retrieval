# CURRENT_WORK.md

> **Single active long-run handoff.** Rewrite (do not append) when a long job starts, changes, or finishes.
> User resume prompt: `continue from CURRENT_WORK.md`

---

## Active long run

| Field | Value |
|-------|-------|
| **Status** | `DONE` — Phase B + diagnostics complete |
| **Updated** | 2026-07-11 15:58 +0700 |
| **Host** | `ict14` |
| **Experiment** | `v9_llm_recall` |
| **Decision** | **`READY FOR MANUAL REVIEW`** |

### Outputs

| Path | Count |
|------|------:|
| `output/v9_llm_recall/submission/` | 100 |
| `output/v9_llm_recall/base_v7_snapshot/` | 100 |
| `output/v9_llm_recall/trace/` (enriched) | 100 non-empty |
| `cache/v9_llm_recall/*.json` | 100 |

### Key metrics

- Frozen v7 invariants: removed/text/pos/type/cand/assert = **all 0**; invalid spans **0**
- Final LLM additions: **34** (CHẨN_ĐOÁN 14, TRIỆU_CHỨNG 12, THUỐC 8)
- All new CD linked (ICD); all new TH linked (RxNorm)
- Report: `analysis/v9_llm_recall_report.md`
- Manual review extract: `analysis/v9_manual_review.md`
- TSVs under `analysis/v9_*.tsv`

### Next (user)

1. Manually review the 34 additions (esp. suspicious/weak: generic `thuốc an thần`, `nac`, `ntg`/`asa`, ECG/imaging phrases).
2. If OK: explicitly ask to package Viettel ZIP (do **not** auto-submit).
3. Do not invent a leaderboard score in `state.md` until scored.

## Do not

- Auto-submit / auto-commit / restart full cache with `--force` without reason
