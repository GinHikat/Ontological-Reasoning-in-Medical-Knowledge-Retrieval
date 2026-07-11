# PLAN — schema-first audit complete; annotation next

Last updated: 2026-07-11

## Closed experiments (leaderboard)

| Experiment | Score | Verdict |
|------------|------:|---------|
| `v7_structured` | **24.79660** | **Best current reference** — keep as main submission |
| `v9_llm_recall` (additive) | 23.84290 | **NEGATIVE** |
| `v10_llm_conflict_resolution` | 24.04370 | Better than v9; **still below v7** — closed |

### Completed checklist

- [x] v9 additive recall experiment (scored negative)
- [x] v10 conflict-resolution experiment (scored; closed)
- [x] Record official v10 leaderboard + project verdicts
- [x] **Schema-first principles audit** (`schema_first_principles_audit`) completed
- [x] Annotation pool created (`analysis/schema_audit/annotation_pool.csv`)

## Active goal

```text
v7–v10 model iteration paused.

Do not build v11 yet.

Next: human annotation + local evaluation guided by schema audit.
```

### Audit root-cause verdict

```text
WRONG_TYPE_SCHEMA
WRONG_SPAN_POLICY
OVER_EXTRACTION
CANDIDATE_SET_FAILURE
DISTRIBUTED_PIPELINE_FAILURE
(+ ASSERTION_SCOPE_FAILURE secondary)
```

### Recommended architecture (from evidence)

**Primary:** task-specific span model (5 labels + NONE), dedicated lab name/result segmentation, contextual assertions, multi-label ICD candidate-set ranker; use v7/Qwen/rules/ontologies as weak supervision only.

**Fallback:** precision-first gates on v7 while annotation proceeds (not a submission).

Details: `analysis/schema_audit/architecture_decision.md`, `final_report.md`.

## Suggested next work items

1. Annotate `analysis/schema_audit/annotation_pool.csv` (415 rows; human_* empty).
2. Prioritize procedure-as-test + symptom/diagnosis collisions.
3. Build local scorer (WER / J_assertion / J_candidates) on annotated gold.
4. Prototype NONE-aware type/span classifier; compare to frozen base-v7 locally.
5. Only then design the next extractor (not additive v11).

## Hard constraints (still in force)

| Must | Must not |
|------|----------|
| Keep v7 as canonical leaderboard reference | Build / submit v11 without annotation evidence |
| Reuse frozen outputs for analysis | External LLM APIs for competition inference |
| Annotate before redesigning conflict rules | Investigate SapBERT nondeterminism |
| Treat precision-first preview as offline only | Submit schema-audit preview ZIP |

## Reference paths

| Path | Purpose |
|------|---------|
| `output/v10_llm_conflict_resolution/base_v7_snapshot/` | Frozen base inventory |
| `analysis/schema_audit/` | Full audit deliverables |
| `output/schema_audit/precision_first_preview/` | Offline removals preview |
