# PLAN — active experiment: `v10_llm_conflict_resolution`

Last updated: 2026-07-11

## Goal

```text
same-execution frozen v7
  +
deterministic high-confidence LLM overlap replacements
```

Use cached LLM proposals to **repair** selected imperfect v7 spans/types — not to add unrelated new entities.

## Prior result (closed)

| Pipeline | Score | Verdict |
|----------|------:|---------|
| `v7_structured` | **24.79660** | canonical baseline — keep |
| `v9_llm_recall` | 23.84290 | **NEGATIVE** additive recall — do not resubmit / do not loosen |

v9 showed ~97% of verifier accepts were duplicates/overlaps; only 34 additive entities. Primary LLM value is in the **322 overlaps**, not the 34 additions.

## Hard constraints

| Must | Must not |
|------|----------|
| Reuse `cache/v9_llm_recall/` (no new Phase A unless prompted) | External LLM APIs |
| Newest v7 once → freeze → replace only | Free-form additive LLM entities (first v10) |
| Exact original-text offsets | Whole-sentence replacement |
| Clear **one-to-one** LLM↔v7 replacement | One LLM span replacing multiple v7 entities |
| Re-link + re-assert **only** replacements | Candidate changes without span/type justification |
| Preserve unrelated v7 entities exactly | Investigate SapBERT nondeterminism |
| Target ~10–50 replacements | Loosen proposer merely to get more entities |

Replacement categories (deterministic):

| Cat | Rule |
|-----|------|
| **A** | Drug junk boundary: LLM ⊂ v7, leftover is glued/punct/`thuốci`/`để` |
| **B** | Leading negation trim: `Không/Chưa` + clinical phrase → re-assert `isNegated` |
| **C** | Diagnosis expand: same-start v7 ⊂ LLM, length/specificity gates, ICD required |
| **D** | Type upgrade TC→CD with trailing punct / leading junk cleanup |

Post-link hard gates: non-empty ICD/RxNorm; lexical consistency vs ontology labels; category B must yield `isNegated`.

## Architecture

```text
Phase A: (reuse) cache/v9_llm_recall/<doc_sha256>.json

Phase B: run_pipeline.py --pipeline v10_llm_conflict_resolution
         newest v7 → freeze → classify overlaps → link/assert replacements
         → survivors + replacements → sort
```

Same-run outputs:

```text
output/v10_llm_conflict_resolution/
  submission/
  base_v7_snapshot/
  trace/
```

Causal compare: `base_v7_snapshot` vs `submission` from the **same** run.

## Phase checklist

- [x] Record v9 leaderboard negative + strategic pivot
- [x] Conflict classifiers A–D (`llm_conflict_resolution.py`)
- [x] `LLMConflictResolutionPipeline` + factory `v10_llm_conflict_resolution`
- [x] `run_pipeline` base_v7_snapshot for v10
- [x] Offline preview analyzer (`analyze_v10_llm_conflict.py`)
- [x] Offline preview on 100 docs (v9 snapshot + cache)
- [x] Smoke: `--samples 1`
- [ ] Full Phase B run (same-env) → diagnostics → manual review
- [ ] Leaderboard only after review (user decision)

## Environments

| Role | Conda env (ict14) | Notes |
|------|-------------------|-------|
| Competition pipeline | `nanachi` | NER/SapBERT |
| Local Qwen (only if regenerating cache) | `v9_vllm` | not needed for first v10 |

## Key paths

| Path | Purpose |
|------|---------|
| `modules/components/postprocessing/llm_conflict_resolution.py` | A–D rules + lexical gates |
| `modules/pipelines/v10.py` | freeze + replace pipeline |
| `modules/evaluation/analyze_v10_llm_conflict.py` | offline preview |
| `cache/v9_llm_recall/` | reused LLM cache |
| `analysis/v9_overlap_rejections.tsv` | mining source (322 overlaps) |

## Decision gate

`NOT READY` if: replacements ≫ 50 without review; multi-v7 replaces slip through; category B lacks `isNegated`; empty/mismatched ICD/RxNorm on CD/TH replacements; unrelated v7 entities mutated.
