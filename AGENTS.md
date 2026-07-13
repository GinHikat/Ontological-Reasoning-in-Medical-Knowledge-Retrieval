# AGENTS.md

Instructions for coding agents working in this repository.

## Project

Vietnamese clinical NER + ontology linking for a competition submission pipeline.

**Three active tracks only:**

| Track | Name | Role |
|-------|------|------|
| Baseline | `baseline_hybrid` | Frozen reference (ex-`v7_structured`, 24.79660) |
| NER | `ner` | Task-specific five-label + NONE |
| LLM | `llm` | Schema-aware extraction + local linking |

Historical `v5`–`v10` and one-off probes live under `archives/` — not factory/CLI options.

## Machine-local config

Host-specific hardware, absolute paths, disk pressure, and GPU quirks live in
**`CURRENT_MACHINE.md`** (gitignored).

1. At session start, read `CURRENT_MACHINE.md` if present.
2. If missing, create it from live specs (`hostname`, `lscpu`, `free -h`, `nvidia-smi`, `df -h`, conda envs).
3. Keep durable project rules here; keep host facts in `CURRENT_MACHINE.md`.

## Environments

| Task | Conda env |
|------|-----------|
| NER / SapBERT / baseline | `nanachi` |
| Local Qwen / vLLM server | `v9_vllm` (separate; do not break `nanachi`) |

Do not use env `tung` for the main pipeline (missing sklearn).

```bash
source /home/student10/miniforge3/etc/profile.d/conda.sh
conda activate nanachi
```

## Common commands

```bash
python scripts/run_baseline.py
python scripts/run_ner.py --train-notes
python scripts/run_llm.py --mode diagnostic --benchmark-10
python scripts/run_llm.py --mode competition

python -c "from modules.pipelines.factory import available_pipelines; print(available_pipelines())"
```

Data / weights: `v_dataset/`. NER weights: `v_dataset/statedict/ner/`.

## Architecture conventions

- Active experiments go under `modules/pipelines/{baseline,ner,llm}/`.
- Shared ICD/RxNorm / validation / writer: `modules/common/`.
- Prefer additive work on NER or LLM tracks; **do not** modify frozen baseline rules.
- Competition JSON must not expose internal metadata.
- Historical builders: `archives/legacy_pipelines/source/` only.

## Active experiment handoff

| File | Role |
|------|------|
| **`CURRENT_WORK.md`** | NER + LLM next steps only (rewriteable) |
| **`WORKLOG.md`** | Append-only chronological log (`tail` only) |
| **`PLAN.md`** | Phase checklist + hard constraints |
| **`CURRENT_MACHINE.md`** | Host paths / GPU / disk (gitignored) |
| **`state.md`** | Three-track results table |

### Resume order

1. Read **`CURRENT_WORK.md`** first.
2. `tail -n 80 WORKLOG.md`.
3. Read `PLAN.md`.
4. Read or create `CURRENT_MACHINE.md`.
5. Verify processes/logs on disk — do not trust chat history.

### Long runs (tmux)

Rewrite `CURRENT_WORK.md` with Status + exact commands; append a short `WORKLOG.md` entry in the same turn.

## Hard boundaries

- **No external LLM APIs** for competition inference. Localhost only for submissions.
- OpenRouter / diagnostic LLM outputs are proof only — mark clearly; never submit as final.
- Do **not** investigate or “fix” SapBERT nondeterminism; do not change seeds / CUDA / precision for that.
- Do **not** commit or push unless the user asks.
- Do **not** package / submit Viettel ZIPs unless the user explicitly decides after review.
- Do not invent leaderboard scores in `state.md` until an actual submission is scored.
- Large caches stay on `/storage/...`; keep `/home` light.

## Code style

- Match existing modules: dataclasses, typed paths via `ProjectPaths`.
- Prefer small, focused diffs; no drive-by refactors or unsolicited markdown docs.
- Analysis artifacts under `analysis/`; pipeline outputs under `output/` (gitignored).
