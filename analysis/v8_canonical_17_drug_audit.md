# Canonical 17 Unlinked Drugs — Observational Audit

Canonical scored artifact `output/v7_structured/run1/submission` is **not present** on disk
(`output/` is gitignored; `run1/submission` exists but is empty). Leaderboard reference remains:

```text
Score 24.79660 | drugs 259/276 linked | 17 unlinked
```

## Same-environment causal result (this experiment)

Fresh same-env v7 vs v8_candidate_rescue:

| Metric | Value |
|---|---|
| Total THUỐC | 271 |
| v7 unlinked | 1 |
| v8 newly rescued | **0** |
| Existing candidates changed | **0** |
| Hard invariants | PASS |

### The single same-env unlinked drug

| Field | Value |
|---|---|
| file | `4` |
| span | [59, 64] |
| text | `NSAID` |
| v7 candidate | `[]` |
| v8 candidate | `[]` |
| rescued? | no |
| reason | `NO_ONTOLOGY_EVIDENCE` |

No ontology donor overlap; rescue correctly left it unlinked.

## Why the previous “17” are not all present same-env

Prior `v8_candidate_integrity` notes (`analysis/v7_vs_v8_candidate_integrity.md`) already
recorded that under same-env SapBERT numerics only **2** drugs were unlinked (most of the
canonical 17 were already linked). This fresh run has **1** unlinked drug.

Do **not** treat canonical↔same-env candidate differences as a reason to change model infra.

## al pain / alpain

Under rescue-only mode, existing v7 candidates are preserved. Trace counts show
`v7_candidate_preserved=270` and `existing_changed=0`, so the old override false-positive
cannot recur as a candidate swap. See `analysis/embedded_drug_false_positives.md`.
