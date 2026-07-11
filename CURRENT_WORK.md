# CURRENT_WORK.md

> **Single active long-run handoff.** Rewrite (do not append) when a long job starts, changes, or finishes.
> User resume prompt: `continue from CURRENT_WORK.md`

---

## Active work

| Field | Value |
|-------|-------|
| **Status** | `IDLE` — v10 officially scored; experiment closed |
| **Updated** | 2026-07-11 19:17 +0700 |
| **Host** | `ict14` |
| **Experiment** | `v10_llm_conflict_resolution` (closed) |
| **Next phase** | Manual annotation and local evaluation |

### Current status

```text
Current status:
v10 full run completed and officially submitted.

Official score:
24.04370

Current task:
design the annotation workflow.
```

### Official leaderboard

| Metric | Value |
|--------|------:|
| Score | **24.04370** |
| WER | 72.4852 |
| J_assertion | 30.0917 |
| J_candidates | 16.9044 |
| vs v9 | **+0.20080** |
| vs v7 | **−0.75290** |

**Decision:** better than v9, not promoted over v7. No more immediate v10 submissions. Do not build v11 yet.

### Consolidated scores

| Version                 |    Score |     WER | J_assertion | J_candidates | Decision                 |
| ----------------------- | -------: | ------: | ----------: | -----------: | ------------------------ |
| v7 reference            | 24.79660 | 72.0039 |     31.3672 |      17.4691 | Best current reference   |
| v9 additive recall      | 23.84290 | 72.7861 |     29.7128 |      16.9122 | Negative                 |
| v10 conflict resolution | 24.04370 | 72.4852 |     30.0917 |      16.9044 | Better than v9, below v7 |

### Next

1. Design annotation workflow / guidelines
2. Select representative documents for a trusted development set
3. Annotate pilot subset; implement local scorer
4. Evaluate v7 / v9 / v10 against pilot gold before any next model version

## Historical commands (completed — do not re-run)

<details>
<summary>v10 Phase B + finalize (DONE 2026-07-11)</summary>

```bash
# Phase B (parallel CPU) — COMPLETED
source /home/student10/miniforge3/etc/profile.d/conda.sh
conda activate nanachi
cd /storage/student10/tungnl/Ontological-Reasoning-in-Medical-Knowledge-Retrieval
CUDA_VISIBLE_DEVICES= python modules/evaluation/run_pipeline_parallel.py \
  --pipeline v10_llm_conflict_resolution \
  --output-dir output/v10_llm_conflict_resolution \
  --workers 10 --threads-per-worker 6
# log: analysis/v10_phase_b_log.txt

# Finalize — COMPLETED
python modules/evaluation/finalize_v10_llm_conflict.py
```

Artifacts (keep):
- Competition ZIP: `output/v10_llm_conflict_resolution_submission.zip` (sha256 `05cb2caf…`)
- Diagnostic ZIP: `output/v10_llm_conflict_resolution_full.zip` (sha256 `6dd235b5…`)
- Review packet: `analysis/v10_annotation_review.md`, `.csv`, `v10_replacements.tsv`
- Leaderboard write-up: `analysis/v10_leaderboard_result.md`

</details>

## Do not

- Rerun v7 / v9 / v10 / Qwen / caches for this closure
- Build v11 yet
- Auto-submit Viettel ZIP
- Investigate SapBERT / neural nondeterminism
- Treat v10 as replacement for v7 reference
