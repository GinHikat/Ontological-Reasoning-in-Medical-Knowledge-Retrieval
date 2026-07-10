# WORKLOG — live session state

> **Agents: read this first, then `PLAN.md`.** Update this file after every meaningful step.

Last updated: 2026-07-10 23:47 +07

## Status

```text
ACTIVE EXPERIMENT: v9_llm_recall
PHASE: P20 pilot cache generation (in progress on CPU)
DECISION: not yet
```

## Next action

1. Wait for pilot cache (`3,13,20,41,48,70,87,89,91,93,96,100`) to finish **or** resume without `--force` if SSH died mid-run.
2. Build pilot report:
   ```bash
   conda activate nanachi
   python modules/evaluation/build_v9_pilot_report.py
   ```
3. Fix only systemic prompt/parser bugs if obvious; then full 100-doc cache (no `--files` filter).
4. Stop/unload Qwen server.
5. Same-env pipeline runs (nanachi):
   ```bash
   python modules/evaluation/run_pipeline.py --pipeline v7_structured --output-dir output/v7_v9_same_env
   python modules/evaluation/run_pipeline.py --pipeline v9_llm_recall --output-dir output/v9_llm_recall
   ```
6. Analyze + enrich traces + update `state.md` + final report sections in PLAN/WORKLOG.

## Running processes (as of last update)

| What | How to check / restart |
|------|------------------------|
| Qwen CPU server | `ss -ltnp \| grep 8000` — expect `python … serve_v9_qwen_cpu.py` |
| Pilot cache gen | `pgrep -af generate_v9_llm_cache` |
| Log | `analysis/v9_pilot_cache_log.txt` |
| Server log | Cursor terminal for `serve_v9_qwen_cpu.py` (look for `generate start/done`) |

Restart server if dead:

```bash
source /home/student10/miniforge3/etc/profile.d/conda.sh
conda activate v9_vllm
export V9_MODEL=Qwen/Qwen3.5-9B
export V9_MODEL_PATH=/storage/student10/tungnl/cache/huggingface/hub/models--Qwen--Qwen3.5-9B/manual
export HF_HOME=/storage/student10/tungnl/cache/huggingface
export V9_HOST=127.0.0.1 V9_PORT=8000
cd /storage/student10/tungnl/Ontological-Reasoning-in-Medical-Knowledge-Retrieval
python scripts/serve_v9_qwen_cpu.py
```

Resume pilot (skip completed caches — **omit `--force`**):

```bash
conda activate nanachi
python modules/evaluation/generate_v9_llm_cache.py \
  --files 3,13,20,41,48,70,87,89,91,93,96,100 \
  --timeout 3600 --max-tokens 1536
```

## Done this session

- [x] Repo hygiene → `analysis/v9_starting_state.txt`
- [x] NER path audit (filesystem fix only; keep)
- [x] Implemented LLM stack + prompts + v9 pipeline + analysis scripts
- [x] Separate conda env `v9_vllm` + vLLM 0.24.0 installed
- [x] GPU vLLM attempted → OOM / no free VRAM → `analysis/v9_gpu_serve_failure.txt`
- [x] Downloaded full `Qwen/Qwen3.5-9B` weights via curl → `…/manual/` (~19G)
- [x] CPU OpenAI-compatible server works (smoke: 7 tokens ≈ 105s)
- [x] Killed orphaned duplicate CPU server that wasted ~37GB RAM
- [ ] Pilot 12-doc cache complete
- [ ] Pilot report
- [ ] Full 100 cache + v7/v9 same-env + diagnostics

## Uncommitted work (do not auto-commit)

```text
Modified: .gitignore, clinical.py (LLM trace section), factory.py, state.md
New: modules/components/llm/*, llm_recall.py, v9.py, generate/analyze/enrich/pilot scripts,
     prompts/, scripts/serve_*, download_*, setup_v9_vllm_env.sh, analysis/v9_*
```

Branch: `tung` @ `5b45f37` (+ local changes)

## Pitfalls already hit

1. **Do not `pkill -f` patterns that appear in the shell command line** — kills the launcher itself.
2. **Two CPU servers** can linger; only one binds `:8000`. Kill orphans (`kill -9`) or RAM/CPU explode.
3. **HF `snapshot_download` / XET stalled** unauthenticated; curl resume script worked.
4. **`tung` conda env lacks sklearn** — use **`nanachi`** for pipelines.
5. Home disk nearly full — keep HF/pip caches under `/storage/student10/tungnl/cache/`.
6. CPU decode is extremely slow; use `--max-tokens 1536` (capped at 2048 in server). Prefer GPU later if VRAM frees (still need quant for 8GB).
7. Cache is keyed by **document SHA256**, not file number — safe to resume; `--force` regenerates.

## Invariants to verify later

```text
existing v7 entities removed: 0
existing v7 types changed: 0
existing v7 candidates changed: 0
existing v7 assertions changed: 0
```

Only allowed delta: new `source=llm_recall` non-overlapping entities.

## Quick health commands

```bash
curl -s http://127.0.0.1:8000/v1/models
ls cache/v9_llm_recall/*.json 2>/dev/null | wc -l
nvidia-smi --query-gpu=memory.free --format=csv
conda activate nanachi && python -c "from modules.pipelines.factory import available_pipelines; print(available_pipelines())"
```
