# Comparison full — deferred

**Status:** Full 100-document reduced run was **not** executed.

Reason: 10-doc benchmark failed success gate

```text
≥90% exact-or-overlap entity agreement with archived frontier gold
```

Observed overlap recall on benchmark: **0.6646**.

Use `benchmark_10_docs.md` / `.tsv` for the available comparison against
`archives/openrouter_schema_teacher_free_2026-07-12/diagnostic_pseudo_gold/`
(user-stated frontier score **35.72280**, ~786 requests).

Re-run full comparison via:

```bash
python -m modules.evaluation.compare_reduced_teacher --stem comparison_full
```

only after a passing benchmark and completed 100-doc reduced finals.
