# PLAN — openrouter_schema_teacher (diagnostic) active; v7–v10 paused

Last updated: 2026-07-12

## Closed experiments (leaderboard)

| Experiment | Score | Verdict |
|------------|------:|---------|
| `v7_structured` | **24.79660** | **Best current reference** — keep as main submission |
| `v9_llm_recall` (additive) | 23.84290 | **NEGATIVE** |
| `v10_llm_conflict_resolution` | 24.04370 | Better than v9; **still below v7** — closed |
| `schema_first_principles_audit` | — | Completed (analysis only) |

## Active goal

```text
openrouter_schema_teacher — EXTERNAL_API_DIAGNOSTIC_ONLY

Question: Can frontier / strong models infer the organizer schema substantially
better than frozen v7/v10?

NOT a competition pipeline. NOT v11. Do not submit teacher outputs.
Do not train on them unless organizers confirm external-API offline data is allowed.
```

### Status

- [x] Phases 0–13 implemented (client, schemas, extract/judge, align, ontology, gold)
- [x] Paid pilot attempted — **blocked** by key credit limit (partial doc 24 only)
- [x] **`free_first` full 100/100** gold + compare — **archived** at
      `archives/openrouter_schema_teacher_free_2026-07-12/` (not bit-reproducible)
- [ ] Paid `default` full run — only after user supplies **new** model IDs + budget
- [ ] Manual annotation / local scorer (schema audit path) — still open

### Diagnostic verdict (`free_first`)

```text
FREE_ENSEMBLE_PARTIALLY_CORRECT_SCHEMA
```

Evidence: 150/159 procedure-as-test rejected; density 0.68× v7; low exact agreement
with frozen v7/v10. Permanent copy: `archives/openrouter_schema_teacher_free_2026-07-12/`.
Live mirror: `analysis/openrouter_teacher_free/final_report.md`.

### Recommended compliant architecture

```text
STILL_UNCERTAIN — lean task-specific span model (5+NONE), not free-teacher distillation
```

## Hard constraints (still in force)

| Must | Must not |
|------|----------|
| Keep v7 as canonical leaderboard reference | Build / submit v11 from teacher gold |
| Mark all OpenRouter outputs EXTERNAL_API_DIAGNOSTIC_ONLY | Use OpenRouter for competition inference |
| Resume via cache without `--force` | Commit/push/submit unless explicitly asked |
| Local ICD/RxNorm retrieval only for IDs | Invent ontology IDs in model prompts |

## Reference paths

| Path | Purpose |
|------|---------|
| `modules/external/` | Teacher ensemble implementation |
| `archives/openrouter_schema_teacher_free_2026-07-12/` | **Permanent** free gold + report (git-tracked) |
| `output/openrouter_schema_teacher_free/` | Live free outputs (gitignored; may be deleted) |
| `analysis/openrouter_teacher_free/` | Live free reports / metrics |
| `cache/openrouter_schema_teacher_free/` | Free request cache (gitignored; not archived) |
| `output/openrouter_schema_teacher/` | Paid diagnostic outputs (partial) |
| `analysis/openrouter_teacher/` | Paid reports |
| `output/v10_llm_conflict_resolution/base_v7_snapshot/` | Frozen v7 |
| `output/v10_llm_conflict_resolution/submission/` | Frozen v10 |
| `analysis/schema_audit/` | Schema-first audit |
