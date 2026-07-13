# CURRENT_WORK.md

> Active handoff only. Rewrite (do not append) when focus changes.
> Resume prompt: `continue from CURRENT_WORK.md`

---

## NER

| Field | Value |
|-------|-------|
| **Status** | Scaffolded — no trained five-label + NONE model yet |
| **Next** | Build training data with direct competition labels + explicit NONE (no Procedure→test remap); pick backend (token / span / GLiNER); train; wire `modules/pipelines/ner/inference.py` |
| **Command** | `python scripts/run_ner.py --train-notes` |

Weak-label sources: frozen `baseline_hybrid` outputs; optional diagnostic gold under `archives/openrouter_schema_teacher_free_2026-07-12/`.

---

## LLM

| Field | Value |
|-------|-------|
| **Status** | Diagnostic path runnable (reduced OpenRouter); competition localhost backend not wired |
| **Diagnostic proof** | OpenRouter ensemble **35.72280** (archived); reduced 1-extractor gates previously FAILED (overlap 0.665) |
| **Next** | Wire competition mode: same prompts/schemas as diagnostic, localhost model ≤9B, shared `modules/common/ontology`; then smoke → full 100 |
| **Commands** | `python scripts/run_llm.py --mode diagnostic --benchmark-10` · `python scripts/run_llm.py --mode competition` |

Do **not** treat the 786-call ensemble as the main implementation. Do **not** submit OpenRouter outputs.

---

## Baseline

Frozen as `baseline_hybrid` (24.79660). Do not add rules.
