# CURRENT_WORK.md

> **Single active long-run handoff.** Rewrite (do not append) when a long job starts, changes, or finishes.
> User resume prompt: `continue from CURRENT_WORK.md`

---

## Active work

| Field | Value |
|-------|-------|
| **Status** | `IDLE` — reduced pipeline implemented; benchmark gates **FAILED** |
| **Updated** | 2026-07-13 00:55 +0700 |
| **Host** | `ict14` |
| **Verdict** | `REDUCED_PIPELINE_TOO_AGGRESSIVE` |

### Done

- Implemented `openrouter_schema_teacher_reduced` (one extractor + conditional largest-model judge).
- Offline ablation → extractor `tencent/hy3:free`; judge `nvidia/nemotron-3-ultra-550b-a55b:free`.
- 10-doc benchmark: **19** requests (1.9/doc), 0×429, overlap vs archive **0.665** (need ≥0.90).
- Full 100 **not started** (per success gates).

### Reports

- `analysis/openrouter_reduced/final_report.md`
- `analysis/openrouter_reduced/benchmark_10_docs.md`
- Archive gold reference: `archives/openrouter_schema_teacher_free_2026-07-12/` (35.72280 / ~786 req)

### Next (human / next session)

1. Fix extractor prompt drift vs ablation A outputs; lower doc-judge rate.
2. Re-run: `PYTHONUNBUFFERED=1 python scripts/run_openrouter_reduced.py --benchmark-10`
3. Only if gates pass: full 100.

### Do not

- Commit / push / submit automatically
- Delete caches or archive
- Modify v7 / v9 / v10
- Call this v11
