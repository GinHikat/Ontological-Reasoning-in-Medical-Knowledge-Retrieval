# v10 full-run starting state

Recorded: 2026-07-11 ~17:05 +0700  
Host: `ict14`

## Git

| Field | Value |
|-------|-------|
| **branch** | `tung` (tracks `origin/tung`) |
| **HEAD** | `baa37fe4235e8ec12e3955d4ece44ad198854344` |
| **HEAD subject** | feat: v9 truncated-JSON salvage, parse-failure raw retention, output-dir layout fix, and prompt injection hardening |

**Note:** HEAD does **not** contain the v10 implementation. v10 lives in the **working tree** (uncommitted). Full run uses this working-tree code.

### Dirty / untracked (at start of full run)

**Modified:**

- `AGENTS.md`
- `CURRENT_WORK.md`
- `PLAN.md`
- `WORKLOG.md`
- `modules/evaluation/run_pipeline.py`
- `modules/pipelines/factory.py`
- `state.md`

**Untracked (v10 implementation + preview):**

- `modules/components/postprocessing/llm_conflict_resolution.py`
- `modules/pipelines/v10.py`
- `modules/evaluation/analyze_v10_llm_conflict.py`
- `analysis/v10_conflict_preview_report.md`
- `analysis/v10_replacement_preview.tsv`
- `analysis/v10_smoke_log.txt`

### Newest commit (`baa37fe`) files (v9 salvage / docs — not v10)

See `git show --stat HEAD`: response_parser salvage, generate/salvage scripts, v9 analysis TSVs, serve/bench scripts, PLAN/CURRENT_WORK/WORKLOG/state updates.

## Offline preview (pre-run)

```text
40 proposed replacements
A=7 B=3 C=18 D=12
exact-span type-only D: disabled
```

## Smoke artifact

```text
output/v10_llm_conflict_resolution_smoke/
```

## Exact full-run commands (from CURRENT_WORK.md)

```bash
source /home/student10/miniforge3/etc/profile.d/conda.sh
conda activate nanachi
cd /storage/student10/tungnl/Ontological-Reasoning-in-Medical-Knowledge-Retrieval

export CUDA_VISIBLE_DEVICES=

mkdir -p analysis
python modules/evaluation/run_pipeline.py \
  --pipeline v10_llm_conflict_resolution \
  --output-dir output/v10_llm_conflict_resolution \
  --trace \
  2>&1 | tee analysis/v10_phase_b_log.txt
```

## Constraints for this run

- Do not regenerate `cache/v9_llm_recall/`
- Do not rerun Qwen
- Do not change conflict rules mid-run
- Do not investigate neural nondeterminism
- Do not create duplicate v10 modules
