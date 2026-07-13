# Experiment reports (archived)

Pointers to preserved analysis — not active architecture.

| Experiment | Report / notes | Short verdict |
|------------|----------------|---------------|
| Schema audit (procedure-as-test, collisions) | `analysis/schema_audit/` | Motivates task-specific NER + schema LLM |
| OpenRouter 3-extractor ensemble | `archives/openrouter_schema_teacher_free_2026-07-12/` + `analysis/openrouter_teacher_free/` | Proof schema direction works (35.72280); ~786 calls; diagnostic only |
| OpenRouter reduced (1 extractor + judge) | `analysis/openrouter_reduced/` | Too aggressive vs archive gold (overlap 0.665 < 0.90); not promoted |
| Precision-first preview | `analysis/schema_audit/` + `output/schema_audit/precision_first_preview/` | Preview only |
| RxNorm policy probes | `analysis/rxnorm_probe_*.md` | Closed; keep single canonical RxCUI |
| v8 candidate integrity/rescue | `analysis/v7_vs_v8_*.md`, `analysis/v8_*.md` | Closed |
| v9 additive recall | `analysis/v9_llm_recall_report.md`, `analysis/v9_manual_review.md` | Negative vs baseline |
| v10 conflict resolution | `analysis/v10_leaderboard_result.md`, `analysis/v10_llm_conflict_report.md` | Negative vs baseline |
| Pre-consolidation `state.md` | `state_md_pre_consolidation_2026-07-13.md` | Historical changelog |

Live scored summary: repo-root `state.md` (three-track table only).
