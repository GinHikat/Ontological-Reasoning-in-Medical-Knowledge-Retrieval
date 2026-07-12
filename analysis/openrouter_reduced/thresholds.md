# Deterministic candidate thresholds

Chosen from offline score distributions in
`output/openrouter_schema_teacher_free/ontology_candidates/` (100 docs).

| Knob | Value | Rationale |
|------|------:|-----------|
| `OPENROUTER_REDUCED_DIAGNOSIS_TOP_THRESHOLD` | 0.85 | ~median combined score |
| `OPENROUTER_REDUCED_DIAGNOSIS_MARGIN_THRESHOLD` | 0.08 | requires clear gap vs #2 |
| `OPENROUTER_REDUCED_DRUG_TOP_THRESHOLD` | 0.95 | drugs often exact/near-exact |
| `OPENROUTER_REDUCED_DRUG_MARGIN_THRESHOLD` | 0.08 | typical margin when top≈1.0 is ~0.12 |

Plus non-threshold rules: unique exact alias, single surviving candidate, dominant lexical match.
Does **not** hedge with sibling ICD or ingredient RxCUIs.
