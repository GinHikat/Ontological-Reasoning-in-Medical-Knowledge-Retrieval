# PLAN — openrouter_schema_teacher_reduced active; frontier archive frozen

Last updated: 2026-07-13

## Closed / frozen references

| Artifact | Score / note |
|----------|----------------|
| `v7_structured` | **24.79660** canonical competition reference |
| `openrouter_schema_teacher` free ensemble (archived) | User-stated **35.72280**; ~**786** API requests; gold at `archives/openrouter_schema_teacher_free_2026-07-12/` |
| v9 / v10 | Closed below v7; do not reopen here |

## Active goal

```text
openrouter_schema_teacher_reduced — EXTERNAL_API_DIAGNOSTIC_ONLY

One primary extractor + largest model only as:
  - ambiguous candidate judge
  - high-risk document judge

Target: 65–140 requests / 100 docs while preserving most frontier quality.
```

### Status

- [x] Phase 0 inspection + `starting_state.md`
- [x] Offline extractor ablation → primary = `tencent/hy3:free`
- [x] Largest judge = `nvidia/nemotron-3-ultra-550b-a55b:free`
- [x] Reduced pipeline + runner + caches/outputs
- [x] 10-doc benchmark
- [ ] Full 100 — **blocked** (overlap agreement gate FAIL: 0.665 < 0.90)
- [ ] Full comparison / promotion — N/A until gates pass

### Benchmark gate result

```text
REDUCED_PIPELINE_TOO_AGGRESSIVE
```

Do not silently fall back to the 786-request ensemble.
Do not call this v11.
Do not modify v7/v9/v10.
Do not delete OpenRouter caches or the free archive.

### Next

1. Align live extractor prompt with ablation-measured Extractor-A behavior (or reuse A cache).
2. Reduce document-judge trigger rate (risk threshold / signals).
3. Re-run 10-doc gates; only then full 100.
