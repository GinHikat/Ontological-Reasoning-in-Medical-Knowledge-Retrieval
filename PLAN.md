# PLAN — next phase: Manual annotation and local evaluation

Last updated: 2026-07-11

## Closed experiments

| Experiment | Score | Verdict |
|------------|------:|---------|
| `v7_structured` | **24.79660** | **Best current reference** — keep as main submission |
| `v9_llm_recall` (additive) | 23.84290 | **NEGATIVE** — no more additive-v9 submissions |
| `v10_llm_conflict_resolution` | 24.04370 | Better than v9 (+0.20080); **still −0.75290 below v7** — not promoted |

### Completed checklist

- [x] v9 additive recall experiment (scored negative)
- [x] v10 conflict-resolution experiment (scored; closed as useful but insufficient)
- [x] Record official v10 leaderboard + project verdicts

## Active goal

```text
Stop leaderboard-driven model iteration temporarily.

Do not build v11 yet.

The next phase is:
manual annotation and local evaluation.
```

Primary goals:

```text
1. Create a small trusted development set.

2. Annotate exact spans, types, assertions, and candidates.

3. Measure v7, v9, and v10 locally.

4. Determine which replacement categories are actually correct.

5. Use annotation evidence before designing the next model version.
```

## Suggested next work items

1. Select representative documents.
2. Define annotation guidelines.
3. Build annotation format and tooling.
4. Annotate the first pilot subset.
5. Implement local scorer.
6. Evaluate v7 and v10 against the pilot gold.

## Hard constraints (still in force)

| Must | Must not |
|------|----------|
| Keep v7 as canonical leaderboard reference | Build / submit v11 without annotation evidence |
| Reuse existing caches / outputs for local eval | External LLM APIs for competition inference |
| Annotate before redesigning conflict rules | Investigate SapBERT nondeterminism |
| Treat categories C/D as main risk | More immediate v10 submissions |

## Accepted nondeterminism assumption

```text
Separate executions of the neural pipeline are not deterministic
on the current Mac GPU environment.

The project will not attempt to fix this.

Therefore, leaderboard differences cannot be attributed entirely
to one set of replacements.
```

Practical interpretation: v10 produced a better official result than v9, but still did not outperform the v7 reference.

## Reference paths (closed v10)

| Path | Purpose |
|------|---------|
| `output/v10_llm_conflict_resolution/` | full run submission / base_v7_snapshot / trace |
| `output/v10_llm_conflict_resolution_submission.zip` | submitted competition ZIP |
| `analysis/v10_leaderboard_result.md` | official score write-up |
| `analysis/v10_replacements.tsv` | 39 replacements (A6 B3 C18 D12) |
| `cache/v9_llm_recall/` | reused LLM cache (do not regenerate) |
