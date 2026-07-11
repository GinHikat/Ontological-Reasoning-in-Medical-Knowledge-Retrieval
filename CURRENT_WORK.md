# CURRENT_WORK.md

> **Single active long-run handoff.** Rewrite (do not append) when a long job starts, changes, or finishes.
> User resume prompt: `continue from CURRENT_WORK.md`

---

## Active work

| Field | Value |
|-------|-------|
| **Status** | `DONE` — schema-first principles audit completed |
| **Updated** | 2026-07-11 20:55 +0700 |
| **Host** | `ict14` |
| **Experiment** | `schema_first_principles_audit` (analysis only; **not** a model version) |
| **Next phase** | Human annotation of `analysis/schema_audit/annotation_pool.csv` + local scorer |

### Current status

```text
v7–v10 model iteration PAUSED.

Schema-first audit STARTED and COMPLETED.
No leaderboard submission used.
No Qwen / v7 / v9 / v10 reruns.

Root-cause verdict:
WRONG_TYPE_SCHEMA + WRONG_SPAN_POLICY + OVER_EXTRACTION
(+ CANDIDATE_SET_FAILURE + DISTRIBUTED_PIPELINE_FAILURE;
 ASSERTION_SCOPE_FAILURE secondary)

Recommended architecture (primary):
task-specific span model with 5 labels + NONE,
dedicated lab name/result segmentation,
contextual assertions, multi-label ICD ranker;
v7/Qwen/rules/ontologies as weak supervision only.
```

### Key artifacts

| Path | Role |
|------|------|
| `analysis/schema_audit/final_report.md` | Full audit report |
| `analysis/schema_audit/architecture_decision.md` | Primary + fallback architecture |
| `analysis/schema_audit/annotation_pool.csv` | 415-row annotation pool (human_* empty) |
| `analysis/schema_audit/entity_inventory.tsv` | 3236-entity inventory |
| `output/schema_audit/precision_first_preview/` | Offline preview (not for submit) |
| `modules/evaluation/analyze_schema_alignment.py` | Audit runner |
| `modules/evaluation/build_precision_first_preview.py` | Precision preview builder |

### Headline numbers

| Metric | Value |
|--------|------:|
| Base entities | 3236 |
| Procedure-as-test | 159 |
| Symptom↔diagnosis collisions | 84 |
| Assertion-risk rows | 220 |
| ICD candidate dist | 215× single code |
| Precision-first removals | 168 → 3068 remain |
| Annotation pool rows | 415 |

### Next

1. Annotate `analysis/schema_audit/annotation_pool.csv` (start with `procedure_as_test` + type collisions)
2. Implement local scorer on annotated subset
3. Prototype NONE-aware type/span classifier; evaluate vs frozen base-v7 locally
4. Do **not** build additive v11 / do **not** submit precision-first preview

## Do not

- Rerun v7 / v9 / v10 / Qwen for this audit
- Build v11 additive conflict/recall stacks yet
- Auto-submit Viettel ZIP
- Investigate SapBERT / neural nondeterminism
- Commit/push unless explicitly asked
