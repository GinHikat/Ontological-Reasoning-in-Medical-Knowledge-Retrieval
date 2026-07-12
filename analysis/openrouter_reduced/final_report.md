# Final report — openrouter_schema_teacher_reduced

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`  
**Date:** 2026-07-13  
**Host:** `ict14`

## Verdict

```text
REDUCED_PIPELINE_TOO_AGGRESSIVE
```

Ten-document benchmark **failed** the ≥90% exact-or-overlap agreement gate vs the archived frontier ensemble (overlap recall **0.665**). Full 100-document run was **not** started.

---

## 1. Starting repository state

| Field | Value |
|-------|-------|
| Branch | `tung` |
| Commit | `7b3e4da9dd9e39e4b4b664488d8718dcbc2c58f6` |
| Dirty at start | clean |

See `starting_state.md`.

## 2. Existing ensemble cost

| Metric | Value |
|--------|------:|
| Requests | **786** |
| Docs | 100 |
| Req / doc | 7.86 |
| Parse OK | 754/786 |
| Archived gold entities | 2213 |
| User-stated leaderboard | **35.72280** |

## 3. Offline extractor ablation

See `extractor_ablation.md` / `.tsv`. Standalone A (`tencent/hy3:free`) dominated exact recall (0.711) and procedure rejection (10/159 survival).

## 4. Selected primary extractor

`tencent/hy3:free`

## 5. Selected largest judge model

`nvidia/nemotron-3-ultra-550b-a55b:free` (550B; largest configured free_first model)

## 6. Reduced architecture

```text
document → one extractor → exact-span align → local ICD/RxNorm
→ deterministic candidate accept → batch ambiguous candidate judge
→ deterministic risk → conditional document judge → final JSON
```

Removed unconditional ensemble stages (3 extractors, cluster adj, omission, critic×2, per-doc candidate calls).

## 7. Rate-limit scheduler

`modules/external/rate_limit_scheduler.py` — global/per-model concurrency 1, min interval 3s + jitter, Retry-After aware.

## 8. Ten-document benchmark

Docs: `55 31 3 41 75 2 36 37 20 24`

| Metric | Value |
|--------|------:|
| Wall-clock | ~1044 s (~17.4 min) |
| API requests | **19** |
| Req / doc | **1.9** |
| Extraction | 10 |
| Candidate batches | 3 |
| Documents judged | 6 |
| 429 | 0 |
| Retries | 0 |
| Parse failures | 0 |
| Exact span agreement | 0.514 |
| Overlap agreement | **0.665** (gate ≥0.90 **FAIL**) |
| Type agreement | 0.962 |
| Assertion agreement | 0.741 |
| Candidate agreement | 0.667 |

## 9. Full-run request count

**Not run** (benchmark gate failure).

Estimated if run with similar rates: ~100 extract + ~15–30 cand batches + ~40–60 doc judges ≈ **155–190** (would likely exceed 140 target unless risk/candidate thresholds tightened). Prefer fixing quality first.

## 10. Wall-clock time

Benchmark only: ~17.4 minutes for 10 docs.

## 11. 429 and retry statistics

429: **0**; retries: **0** (benchmark).

## 12–14. Extraction / assertion / candidate agreement

See §8 and `benchmark_10_docs.md`.

## 15. Largest-model judge intervention rate

6 / 10 documents (60%) triggered document judge (`risk_score >= 3`).

## 16. Candidate batch statistics

3 batches (batch size 15) for ambiguous ontology items.

## 17. Comparison with archived 35.72280 output

Benchmark-only comparison against archived frontier gold. Full corpus comparison deferred.

Reduced is sparser (251 vs 319 ents on the 10 docs) with good type agreement on overlaps but insufficient span recall vs the ensemble teacher.

## 18. Remaining risks

- New extractor prompt ≠ archived Extractor-A outputs; offline ablation overestimates live reduced recall.
- Document judge rate still high (60% of docs) → request budget pressure on full run.
- Free-model latency dominates wall-clock.
- Candidate agreement only ~67% on overlapping diagnosis/drug entities.

## 19. Recommended production configuration

Do **not** promote reduced outputs. Next iterations:

1. Reuse archived Extractor-A prompt text (or warm-start from aligned A cache) before changing checklist wording.
2. Raise risk threshold / shrink risk signals to cut doc-judge rate toward ≤25%.
3. Increase deterministic candidate acceptance slightly to cut cand batches.
4. Keep judge = Nemotron Ultra; extractor = hy3 unless a new ablation on the **live** prompt says otherwise.
5. Re-run 10-doc gates before any 100-doc attempt.

---

### Required project note

The full 100-document frontier pipeline scored **35.72280** (user-stated) at ~**786** API requests. A reduced one-extractor pipeline was implemented; the largest configured model is used only as ambiguous-candidate judge and high-risk document judge. Target 65–140 requests remains unmet pending quality fixes.
