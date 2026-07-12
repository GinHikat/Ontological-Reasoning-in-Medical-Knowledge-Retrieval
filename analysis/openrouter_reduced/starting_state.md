# Starting state — openrouter_schema_teacher_reduced

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`  
**Inspection time:** 2026-07-13 00:24 +0700  
**Host:** `ict14`  
**API calls during Phase 0:** none

## Git

| Field | Value |
|-------|-------|
| Branch | `tung` |
| Commit | `7b3e4da9dd9e39e4b4b664488d8718dcbc2c58f6` |
| Message | Archive free OpenRouter schema-teacher run as permanent diagnostic artifact. |
| Dirty files | none (clean working tree) |
| Tracking | up to date with `origin/tung` |

## Current ensemble (reference frontier run)

| Role | Model ID |
|------|----------|
| Extractor A | `tencent/hy3:free` |
| Extractor B | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| Extractor C | `poolside/laguna-m.1:free` |
| Judge (ensemble) | `tencent/hy3:free` |

Configured via `--profile free_first` in `modules/external/teacher_pipeline.py`  
(`OPENROUTER_EXTRACTOR_MODELS` / `OPENROUTER_JUDGE_MODEL` currently empty in `.env`).

## Request count from previous run

| Metric | Value |
|--------|------:|
| Total requests | **786** |
| Cached hits | 0 |
| Uncached | 786 |
| Parse OK | 754 / 786 (~95.9%) |
| Input tokens | 2,862,959 |
| Output tokens | 3,491,088 |
| Estimated spend | $0.00 |

Source: `archives/openrouter_schema_teacher_free_2026-07-12/logs/full_results.json` → `usage`.

## Cache locations

| Path | Role |
|------|------|
| `cache/openrouter_schema_teacher_free/` | Free ensemble request cache (gitignored; **do not delete**) |
| `cache/openrouter_schema_teacher/` | Paid/partial diagnostic cache (gitignored; **do not delete**) |

## Final 100-document artifact

| Path | Notes |
|------|-------|
| `archives/openrouter_schema_teacher_free_2026-07-12/diagnostic_pseudo_gold/` | **Canonical** 100-doc frontier gold (git-tracked) |
| Entities | 2213 |
| Gold SHA256 manifest | `c601c9f66d4e49d107c975aa74cc59c40d0f0802456c3201c5eafe6693de8aaf` |
| Live mirror | `output/openrouter_schema_teacher_free/diagnostic_pseudo_gold/` |

### User-stated leaderboard reference (frontier teacher)

```text
Score:         35.72280
WER:           54.9016
J_assertion:   43.9687
J_candidates:  22.5066
Documents:     100
```

(Recorded from user brief; not yet mirrored into `state.md` at inspection time.)

## Aligned extractor coverage (for offline ablation)

| Model dir | Aligned docs | Missing vs gold |
|-----------|-------------:|-----------------|
| `tencent_hy3_free` | 99 | `5` |
| `nvidia_nemotron-3-ultra-550b-a55b_free` | 98 | `56`, `95` |
| `poolside_laguna-m.1_free` | 99 | `75` |

Raw: `output/openrouter_schema_teacher_free/raw/{model}/`  
Aligned: `output/openrouter_schema_teacher_free/aligned/{model}/`

## Unconditional stages to remove in reduced design

```text
three extractors for every document
separate cluster adjudication for every document
separate omission-recovery call
critic call for every document
separate critic adjudication call
candidate-selection call for every document
```

## Largest configured model (judge candidate)

Among free_first configured IDs, largest known parameter count:

`nvidia/nemotron-3-ultra-550b-a55b:free` (550B MoE) — reserved primarily for judging in the reduced pipeline (not as default sole extractor unless ablation selects it).
