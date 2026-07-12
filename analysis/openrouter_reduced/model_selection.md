# Reduced pipeline model selection

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`  
**Date:** 2026-07-13  
**API catalog query:** not required (explicit free_first IDs already validated in archived run)

## Primary extractor

| Field | Value |
|-------|-------|
| Model ID | `tencent/hy3:free` |
| Role | Extractor A (standalone primary) |
| Context length | 262144 |
| Structured outputs | True (archived metadata) |
| Known parameter count | not published in local metadata |
| Selection mode | offline ablation vs archived frontier gold |

### Ablation evidence (see `extractor_ablation.md`)

| Config | Exact recall | Overlap recall | Type agree | Proc-as-test survival |
|--------|-------------:|---------------:|-----------:|----------------------:|
| **A_only (hy3)** | **0.711** | **0.823** | **0.986** | **10/159** |
| B_only (nemotron) | 0.363 | — | 0.979 | 14/159 |
| C_only (laguna) | 0.581 | — | 0.965 | 18/159 |

Selection priority applied: exact/type agreement with archived final output, procedure rejection, span-policy proxies, then stability. **Largest model was not chosen as extractor.**

## Judge (largest configured model)

| Field | Value |
|-------|-------|
| Model ID | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| Role | Ambiguous-candidate judge + high-risk document judge |
| Context length | 1000000 |
| Structured outputs | unknown / prompt-JSON fallback |
| Known parameter count | **550B** (MoE; largest among configured free_first IDs) |
| Selection mode | largest/highest-capability among configured models |

### Selection policy applied

1. `OPENROUTER_REDUCED_JUDGE_MODEL` / `OPENROUTER_JUDGE_MODEL` — unset at selection time.
2. Among configured free_first models, prefer largest known parameter count → Nemotron Ultra 550B.
3. Do not use auto-router aliases.
4. If this model is unavailable at runtime, stop with a clear error (no silent smaller fallback unless `OPENROUTER_REDUCED_JUDGE_FALLBACK_MODEL` is explicitly set).

### Configured set considered

| Model | Params (known) | Prior ensemble role |
|-------|----------------|---------------------|
| `tencent/hy3:free` | n/a | extractor A + old judge |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | **550B** | extractor B |
| `poolside/laguna-m.1:free` | n/a | extractor C |

## Reduced env defaults

```bash
OPENROUTER_REDUCED_EXTRACTOR_MODEL=tencent/hy3:free
OPENROUTER_REDUCED_JUDGE_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
```

## Judge usage (only when needed)

- Batch ambiguous ICD/RxNorm cases across documents
- Review/correct only high-risk documents (`risk_score >=` threshold)
