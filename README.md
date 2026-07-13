# Vietnamese Clinical NER & Entity Linking

Extract five competition labels from Vietnamese clinical notes, attach assertions, and link diagnoses/drugs to local ICD-10 / RxNorm dictionaries.

## Research question

> Can a task-specific NER model or a schema-aware self-hosted LLM reproduce the frontier teacher’s improvement over the frozen baseline?

## Active tracks

| Track | Purpose | CLI |
|-------|---------|-----|
| **Baseline** (`baseline_hybrid`) | Frozen reference / fallback | `python scripts/run_baseline.py` |
| **NER** | Direct five-label + NONE extraction | `python scripts/run_ner.py` |
| **LLM** | One-pass schema extraction + local linking | `python scripts/run_llm.py` |

Historical `v5`–`v10` pipelines are archived evidence under `archives/` — not CLI options.

---

## 1. Problem

Competition output labels:

1. `CHẨN_ĐOÁN` → ICD-10 candidates  
2. `THUỐC` → RxNorm candidates  
3. `TÊN_XÉT_NGHIỆM`  
4. `TRIỆU_CHỨNG`  
5. `KẾT_QUẢ_XÉT_NGHIỆM`  

Plus assertions (`isNegated`, `isHistorical`, `isFamily`) where eligible.

---

## 2. Installation

```bash
git clone <repo-url>
cd Ontological-Reasoning-in-Medical-Knowledge-Retrieval
cp .env.example .env

# NER / baseline (conda env nanachi on lab hosts — see CURRENT_MACHINE.md)
source /home/student10/miniforge3/etc/profile.d/conda.sh
conda activate nanachi
# or: pip install -r requirements.txt
```

Data and weights live under `v_dataset/` (notes, dictionaries, NER statedicts).

---

## 3. Baseline

Frozen hybrid stack (formerly scored as `v7_structured`):

```text
generic Vietnamese medical NER
  → deterministic span cleanup
  → assertion rules
  → local ICD / RxNorm retrieval
  → competition JSON
```

```bash
python scripts/run_baseline.py
python scripts/run_baseline.py --samples 1 --output-dir output/smoke_baseline
```

**Leaderboard reference: 24.79660.** Do not keep adding rules to this track.

---

## 4. NER direction

Task-specific extractor with an explicit `NONE` class — no Procedure→test remapping:

```text
document → five-label (+NONE) spans → assertions → shared ICD/RxNorm → JSON
```

```bash
python scripts/run_ner.py --train-notes   # design constraints
python scripts/run_ner.py                # runs once a model is wired
```

Backends (common interface): GLiNER / span classifier / token classifier / small clinical LM.

---

## 5. LLM direction

```text
document
  → one schema-aware LLM extraction call
  → exact-span validation
  → local ICD/RxNorm retrieval
  → optional judge only for risky cases
  → JSON
```

Two modes, **same** prompts / schemas / alignment / ontology / writer:

| Mode | Backend | Compliance |
|------|---------|------------|
| `diagnostic` | OpenRouter frontier | External API — proof only |
| `competition` | Self-hosted ≤9B localhost | Required for submission |

```bash
python scripts/run_llm.py --mode diagnostic --benchmark-10
python scripts/run_llm.py --mode competition   # localhost ≤9B (wiring in progress)
```

OpenRouter diagnostic score **35.72280** (WER 54.9016 / J_assertion 43.9687 / J_candidates 22.5066) proves the schema direction; it is **not** competition-compliant.

---

## 6. Evaluation

```bash
# Shared writer / ontology used by active tracks
python -c "from modules.pipelines.factory import available_pipelines; print(available_pipelines())"

# Compare two submission directories
python modules/evaluation/compare_outputs.py --help
```

Prefer fair comparisons: same input, same ontology layer, same validator, same output writer — only the extractor differs.

---

## 7. Competition compliance

- No external LLM APIs for final inference (OpenAI / Anthropic / Gemini / DashScope / OpenRouter).
- Localhost-only self-hosted models for the competition LLM track.
- Competition JSON must not expose internal metadata.
- Do not package / submit Viettel ZIPs unless explicitly decided after review.

---

## 8. Archived experiments

See `archives/`:

- `legacy_pipelines/` — v5–v10 builders + old unit tests  
- `leaderboard_submissions/` — scores / ZIP hashes  
- `experiment_reports/` — pointers to analysis verdicts  
- `openrouter_schema_teacher_free_2026-07-12/` — frontier diagnostic gold  

Live handoff: `CURRENT_WORK.md`. Scored summary: `state.md`.

---

## Repository layout (active)

```text
modules/
  common/           # shared schema, spans, assertions, ontology, writer
  pipelines/
    baseline/       # baseline_hybrid (frozen)
    ner/            # task-specific NER track
    llm/            # schema-aware LLM track
  evaluation/       # runners + metrics helpers
scripts/
  run_baseline.py
  run_ner.py
  run_llm.py
archives/           # evidence only
```
