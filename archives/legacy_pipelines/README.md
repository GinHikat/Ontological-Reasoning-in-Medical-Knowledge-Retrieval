# Archived legacy pipelines

These versioned builders are **evidence only** — not registered in
`modules/pipelines/factory.py` and not available via CLI.

## Source snapshot

Frozen builders live under `source/`:

| Historical name | Role | Verdict |
|-----------------|------|---------|
| `legacy_v5` / `v5_refactored` | Early refactor | Superseded |
| `v6_refined` | Postprocessor stack | Superseded by baseline |
| `v7_structured` | Strongest non-LLM | **Promoted → `baseline_hybrid` (24.79660)** |
| `v8_candidate_integrity` / `v8_candidate_rescue` | RxNorm linking ablations | Closed; not better than baseline |
| `v9_llm_recall` | Additive local-LLM recall | **Negative** vs baseline (23.84290) |
| `v10_llm_conflict_resolution` | Overlap conflict repair | **Negative** vs baseline (24.04370) |

Active rename: use `baseline_hybrid` (see `modules/pipelines/baseline/`).

## Do not

- Re-register these in the factory
- Add new rules on top of archived builders
- Treat OpenRouter / v9 / v10 ZIPs as competition submissions without review

## Related archives

- Leaderboard ZIPs / hashes: `../leaderboard_submissions/`
- Experiment reports: `../experiment_reports/`
- Frontier OpenRouter gold: `../openrouter_schema_teacher_free_2026-07-12/`
