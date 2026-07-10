# CURRENT_WORK.md

> **Single active long-run handoff.** Rewrite (do not append) when a long job starts, changes, or finishes.
> User resume prompt: `continue from CURRENT_WORK.md`
> Agents: read **this file first**, then `tail -n 80 WORKLOG.md`, then `PLAN.md` / `CURRENT_MACHINE.md` as needed.
> Chronological detail stays in `WORKLOG.md`; this file stays short and actionable.

---

## How to use (human)

1. Agent writes the **exact** tmux-ready commands below.
2. You run them in `tmux` / `screen` so SSH/Cursor disconnect does not kill the job.
3. When the job finishes (or you want to resume), prompt: **`continue from CURRENT_WORK.md`**.
4. Agent updates this file after each meaningful step / when the run ends.

## How to use (agent)

When user says continue from this file (or after network loss mid-run):

1. Read `CURRENT_WORK.md` (this file) — follow **Status** / **Next after finish**.
2. `tail -n 80 WORKLOG.md` for recent context.
3. Verify on disk: `hostname`, PIDs, log tail, cache counts — do not trust chat.
4. After meaningful steps: **rewrite** this file + **append** a short `WORKLOG.md` entry.

---

## Active long run

| Field | Value |
|-------|-------|
| **Status** | `RUNNING` (pilot LLM cache; mostly timing out on CPU) |
| **Updated** | 2026-07-11 ~02:40 +07 |
| **Host** | `ict14` (verify with `hostname`) |
| **Experiment** | `v9_llm_recall` Phase A — pilot 12-doc cache |
| **Goal** | Fill `cache/v9_llm_recall/<sha>.json` for pilot stems; then pilot report / quality gate |
| **Depends on** | Local Qwen on `http://127.0.0.1:8000/v1` (CPU fallback) |

### Live processes (as of last write)

```text
serve:     python scripts/serve_v9_qwen_cpu.py          (PID ~213051, env v9_vllm)
generate:  python modules/evaluation/generate_v9_llm_cache.py ... --force  (PID ~216836, env nanachi)
```

Check:

```bash
hostname
pgrep -af 'serve_v9_qwen|generate_v9_llm_cache'
curl -s http://127.0.0.1:8000/v1/models | head -c 200; echo
tail -n 30 analysis/v9_pilot_cache_log.txt
ls cache/v9_llm_recall/*.json 2>/dev/null | wc -l
```

### Progress snapshot

- Pilot files: `3,13,20,41,48,70,87,89,91,93,96,100`
- Log: ~3/12 tqdm steps, each ~3600s → **proposer timeouts**
- Usable cache entries: **0** (doc `20` written but `proposer_failed` / empty accepted)
- Quarantine (old stubs): `cache/v9_llm_recall/_quarantine/`
- Log path: `analysis/v9_pilot_cache_log.txt`

**Issue:** CPU Qwen on this host is too slow for `--timeout 3600` / `--max-tokens 1536`. Expect more timeout stubs unless timeout is raised or a faster backend is used. Do **not** switch model id.

---

## Exact commands (tmux)

Repo root:

```bash
cd /storage/student10/tungnl/Ontological-Reasoning-in-Medical-Knowledge-Retrieval
```

### Pane A — Qwen CPU server (keep up for whole Phase A)

```bash
source /home/student10/miniforge3/etc/profile.d/conda.sh
conda activate v9_vllm   # on ict14; if missing, use nanachi + same script
export HF_HOME=/storage/student10/tungnl/cache/huggingface
export V9_MODEL=Qwen/Qwen3.5-9B
export V9_MODEL_PATH=/storage/student10/tungnl/cache/huggingface/hub/models--Qwen--Qwen3.5-9B/manual
export V9_HOST=127.0.0.1
export V9_PORT=8000
python scripts/serve_v9_qwen_cpu.py
```

Health: `curl -s http://127.0.0.1:8000/v1/models`

### Pane B — pilot cache (long; detach tmux)

**If current job still running:** do not start a second generator. Wait or kill intentionally, then resume **without** `--force` so finished SHA keys are skipped.

```bash
source /home/student10/miniforge3/etc/profile.d/conda.sh
conda activate nanachi
cd /storage/student10/tungnl/Ontological-Reasoning-in-Medical-Knowledge-Retrieval
mkdir -p cache/v9_llm_recall analysis

# Resume-safe (preferred after interrupt): omit --force
python modules/evaluation/generate_v9_llm_cache.py \
  --files 3,13,20,41,48,70,87,89,91,93,96,100 \
  --timeout 7200 \
  --max-tokens 1536 \
  2>&1 | tee -a analysis/v9_pilot_cache_log.txt
```

Only use `--force` when deliberately regenerating (e.g. after quarantining timeout stubs).

### After pilot cache looks healthy

```bash
# (agent will refine once cache has non-empty accepted candidates)
python modules/evaluation/build_v9_pilot_report.py
# then Phase B NER on GPU env when ready — see PLAN.md / CURRENT_MACHINE.md
```

---

## Next after finish

1. Inspect cache: count JSON files; reject / quarantine entries with `proposer_failed` or empty `final_accepted_candidates` if they block resume.
2. If mostly timeouts → raise timeout further, smoke one short doc, or move Qwen to a host/GPU that can actually serve; **do not** change model name.
3. If pilot OK → write `analysis/v9_pilot_report.md` + quality gate → full 100-doc cache (no `--force`) → unload Qwen → Phase B `v9_llm_recall` on NER GPU env.
4. Set **Status** in this file to `IDLE` or `DONE` and point **Next** at the concrete follow-up command.

---

## Do not

- External LLM APIs
- `--force` on resume unless regenerating bad stubs
- Auto-submit Viettel ZIP / auto-commit / push
- Investigate SapBERT nondeterminism
- Replace `v7_structured` leaderboard artifact
- Silent model switch away from `Qwen/Qwen3.5-9B`
