# CURRENT_WORK.md

> **Single active long-run handoff.** Rewrite (do not append) when a long job starts, changes, or finishes.
> User resume prompt: `continue from CURRENT_WORK.md`

---

## Active long run

| Field | Value |
|-------|-------|
| **Status** | `IDLE` — Phase B + finalize DONE; **READY FOR MANUAL REVIEW** |
| **Updated** | 2026-07-11 19:02 +0700 |
| **Host** | `ict14` |
| **Experiment** | `v10_llm_conflict_resolution` |
| **HEAD** | `baa37fe` (v10 code uncommitted) |

### Finalize result

| Field | Value |
|-------|-------|
| Decision | READY FOR MANUAL REVIEW |
| Replacements | **39** (A6 B3 C18 D12) |
| Hard gates | all **0** |
| Competition ZIP | `output/v10_llm_conflict_resolution_submission.zip` (93 843 B, sha256 `05cb2caf…`) |
| Diagnostic ZIP | `output/v10_llm_conflict_resolution_full.zip` (612 247 B, sha256 `6dd235b5…`) |
| Offset mismatches / invalid types / malformed | 0 / 0 / 0 |

### Review packet

- `analysis/v10_annotation_review.md` — fill Human decision
- `analysis/v10_annotation_review.csv`
- `analysis/v10_llm_conflict_report.md`
- `analysis/v10_replacements.tsv`

### Next

1. Human review of 39 replacements (ACCEPT / REJECT / MODIFY / UNSURE)
2. Only if accepted: package/submit decision (do **not** auto-submit)
3. Optionally commit v10 code after review

## Do not

- Auto-submit Viettel ZIP
- `--force` cache / rerun Qwen
- Treat hard gates as clinical correctness
