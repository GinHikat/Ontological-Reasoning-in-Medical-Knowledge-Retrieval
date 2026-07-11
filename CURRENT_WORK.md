# CURRENT_WORK.md

> **Single active long-run handoff.** Rewrite (do not append) when a long job starts, changes, or finishes.
> User resume prompt: `continue from CURRENT_WORK.md`

---

## Active long run

| Field | Value |
|-------|-------|
| **Status** | `RUNNING` — v10 full 100-doc Phase B |
| **Updated** | 2026-07-11 17:12 +0700 |
| **Host** | `ict14` |
| **Experiment** | `v10_llm_conflict_resolution` |
| **Device** | CPU (`CUDA_VISIBLE_DEVICES=`) |
| **PID** | `906235` |
| **HEAD** | `baa37fe` (v10 code is **uncommitted** working tree) |

### Log / output

| Path | Role |
|------|------|
| `analysis/v10_phase_b_log.txt` | live log |
| `output/v10_llm_conflict_resolution/` | submission + base_v7_snapshot + trace |
| `analysis/v10_full_run_starting_state.md` | Phase 0 snapshot |
| `analysis/v10_smoke_validation.md` | Phase 1 smoke OK |

### Exact command (running)

```bash
source /home/student10/miniforge3/etc/profile.d/conda.sh
conda activate nanachi
cd /storage/student10/tungnl/Ontological-Reasoning-in-Medical-Knowledge-Retrieval
export CUDA_VISIBLE_DEVICES=
python modules/evaluation/run_pipeline.py \
  --pipeline v10_llm_conflict_resolution \
  --output-dir output/v10_llm_conflict_resolution \
  --trace \
  2>&1 | tee analysis/v10_phase_b_log.txt
```

### Next after finish

1. Structural validation + base↔v10 compare
2. Replacement TSVs / annotation packet / report
3. Package diagnostic + competition ZIPs
4. Update PLAN / state / WORKLOG; decision `READY FOR MANUAL REVIEW` or `NOT READY`

## Do not

- Kill mid-run / edit JSON while running
- `--force` cache / rerun Qwen
- Change conflict rules mid-run
- Auto-commit / auto-submit
