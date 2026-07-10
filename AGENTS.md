# AGENTS.md

Instructions for coding agents working in this repository.

## Project

Vietnamese clinical NER + ontology linking for a competition submission pipeline.

- Pipelines are versioned: `v5_refactored`, `v6_refined`, `v7_structured`, `v8_*`, `v9_llm_recall`, …
- Canonical scored baseline: **`v7_structured` (24.79660)**. Do not replace this leaderboard artifact.
- Competition JSON is produced by the deterministic pipeline only (offsets, ICD/RxNorm, assertions).

## Machine-local config

Host-specific hardware, absolute paths, disk pressure, and GPU quirks live in
**`CURRENT_MACHINE.md`** (gitignored).

1. At session start, read `CURRENT_MACHINE.md` if present.
2. If it is **missing** (new machine / fresh clone), create it from live specs
   (`hostname`, `lscpu`, `free -h`, `nvidia-smi`, `df -h`, conda envs) and
   record paths/quirks that agents must respect on that host. Do not invent
   GPUs, free disk, or conda prefixes.
3. Keep durable project rules here; keep host facts in `CURRENT_MACHINE.md`.

## Environments

| Task | Conda env |
|------|-----------|
| NER / SapBERT / `run_pipeline.py` | `nanachi` |
| Local Qwen / vLLM server | `v9_vllm` (separate; do not break `nanachi`) |

Do not use env `tung` for the main pipeline (missing sklearn).

Conda activate path is machine-local (see `CURRENT_MACHINE.md`). On this lab host:

```bash
source /home/student10/miniforge3/etc/profile.d/conda.sh
conda activate nanachi
```

## Common commands

```bash
# List pipelines
python -c "from modules.pipelines.factory import available_pipelines; print(available_pipelines())"

# Full run (writes submission + traces under output/<pipeline>/runN/ unless --output-dir)
python modules/evaluation/run_pipeline.py --pipeline v7_structured
python modules/evaluation/run_pipeline.py --pipeline v9_llm_recall --output-dir output/v9_llm_recall

# Smoke
python modules/evaluation/run_pipeline.py --pipeline v7_structured --samples 1 --output-dir output_smoke
```

Data / weights live under `v_dataset/` (renamed from `data/`). NER weights: `v_dataset/statedict/ner/`.

## Architecture conventions

- New experiments get a **new pipeline builder** (`modules/pipelines/vN.py`) registered in `modules/pipelines/factory.py`.
- Prefer additive postprocessors over rewriting shared v7 defaults.
- Do not build new experiments on abandoned ablations unless explicitly requested.
- Traces may include diagnostics; **competition JSON must not** expose internal metadata.

## Active experiment handoff (session recovery)

Live progress is **not** maintained in this file. `WORKLOG.md` is an **append-only** log (grows forever).

1. **Read** latest state only: `tail -n 80 WORKLOG.md` (do not load the whole file). Follow **Next** in the last entry.
2. Read `PLAN.md` for phase checklist + hard constraints.
3. Read or create `CURRENT_MACHINE.md` (host paths / GPU / disk quirks).
4. Use `state.md` for historical scores / conclusions only.

After meaningful steps, **append** to `WORKLOG.md` via bash heredoc in the same turn (`cat >> WORKLOG.md <<'EOF' ... EOF`). Include **Status** + **Next** so the next `tail` is enough to resume.

## Hard boundaries

- **No external LLM APIs** for competition inference (OpenAI/Anthropic/Gemini/DashScope/…). Localhost only.
- Do **not** investigate or “fix” SapBERT nondeterminism; do not change seeds / CUDA / precision for that.
- Do **not** commit or push unless the user asks.
- Do **not** package / submit Viettel ZIPs unless the user explicitly decides after review.
- Do not invent leaderboard scores in `state.md` until an actual submission is scored.
- Large caches (`cache/`, HF weights) stay on `/storage/...`; keep `/home` light.

## Code style

- Match existing modules: dataclasses, `BaseMentionPostProcessor`, typed paths via `ProjectPaths`.
- Prefer small, focused diffs; no drive-by refactors or unsolicited markdown docs.
- Analysis artifacts go under `analysis/`; pipeline outputs under `output/` (gitignored).
