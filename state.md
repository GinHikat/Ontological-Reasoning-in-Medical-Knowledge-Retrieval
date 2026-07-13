# Project state — three active tracks

> Historical changelog (pre-consolidation): `archives/experiment_reports/state_md_pre_consolidation_2026-07-13.md`

## Research question

Can a task-specific NER model or a schema-aware self-hosted LLM reproduce the frontier teacher’s improvement over the frozen baseline?

## Results

| Track | Best score | Status |
| ----- | ---------: | ------ |
| Baseline hybrid | 24.79660 | Frozen |
| NER | Not evaluated yet | Active |
| LLM diagnostic | 35.72280 | Active, external API diagnostic |
| LLM self-hosted | Not evaluated yet | Required for compliance |

### Notes

- **Baseline hybrid** is the former `v7_structured` stack, renamed and frozen. Reference / fallback / comparison / weak labels only.
- **LLM diagnostic** OpenRouter free ensemble: Score 35.72280 / WER 54.9016 / J_assertion 43.9687 / J_candidates 22.5066. Archived under `archives/openrouter_schema_teacher_free_2026-07-12/`. Not competition-compliant.
- Closed negative experiments (v9 23.84290, v10 24.04370, RxNorm probes, reduced OpenRouter gates): see `archives/`.

## Fair comparison rule

Same input · same ontology layer · same validator · same output writer — only extraction architecture differs.
