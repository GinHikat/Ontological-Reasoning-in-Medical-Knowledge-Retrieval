# PLAN — three-track consolidation

Last updated: 2026-07-13

## Decision

```text
Baseline: freeze and stop modifying (baseline_hybrid)
NER:      build direct five-label + NONE model
LLM:      one-pass schema extractor + local ontology (self-hosted for competition)
Else:     archive and deprecate
```

## Checklist

- [x] Archive v5–v10 builders under `archives/legacy_pipelines/`
- [x] Factory exposes only `baseline_hybrid` / `ner` / `llm`
- [x] CLI: `scripts/run_{baseline,ner,llm}.py`
- [x] Shared `modules/common/` ontology / writer / validation
- [x] Docs: README / CURRENT_WORK / state / AGENTS
- [ ] NER: train + wire five-label model
- [ ] LLM competition: localhost ≤9B backend using shared prompts
- [ ] Fair NER vs LLM eval on same ontology layer

## Hard constraints

- No external LLM APIs for competition inference
- Do not add rules to baseline_hybrid
- Do not resurrect 786-call ensemble as main path
- Do not delete archive reports / gold / ZIP evidence
