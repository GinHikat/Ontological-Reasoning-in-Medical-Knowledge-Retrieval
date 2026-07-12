# Final report — openrouter_schema_teacher (`free_first`)

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`

Do **not** use these outputs in a competition submission.
Do **not** train a final competition model on them unless organizers confirm
external-API offline training data is allowed.

Frozen **v7_structured (24.79660)** remains the canonical leaderboard reference.

---

## 1. Models (all $0)

| Role | Model ID |
|------|----------|
| Extractor A | `tencent/hy3:free` |
| Extractor B | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| Extractor C | `poolside/laguna-m.1:free` |
| Judge / critic | `tencent/hy3:free` |

See `model_selection.md`.

## 2. Run status

| Item | Value |
|------|------:|
| Docs with gold | **100 / 100** |
| Pilot gold | 5/5 (`75 36 20 37 51`) |
| Estimated spend | **$0.00** |
| Parse OK rate (overnight log) | ~95.9% (754/786) |
| Doc 29 | failed overnight (`KeyError: type` on hy3 entity missing `type`); fixed by skipping incomplete proposals; gold rewritten 2026-07-12 |

Outputs: `output/openrouter_schema_teacher_free/`  
Cache: `cache/openrouter_schema_teacher_free/`  
Compare: `analysis/openrouter_teacher_free/`

## 3. Density vs frozen pipelines

| Source | Entities |
|--------|---------:|
| Free teacher gold | **2213** |
| Frozen v7 snapshot | **3236** |
| Density ratio vs v7 | **0.684** |

By type (teacher → v7):

| Type | Teacher | v7 |
|------|--------:|---:|
| TRIỆU_CHỨNG | 1018 | 1920 |
| TÊN_XÉT_NGHIỆM | 352 | 696 |
| KẾT_QUẢ_XÉT_NGHIỆM | 251 | 134 |
| CHẨN_ĐOÁN | 421 | 215 |
| THUỐC | 171 | 271 |

Free ensemble is **sparser** overall (especially symptoms/tests) but **heavier on CHẨN_ĐOÁN** and lab results than v7.

## 4. Schema-sensitive metrics

| Metric | Value |
|--------|------:|
| Procedure-as-test audit spans | 159 |
| Rejected by teacher (not kept as test) | **150 / 159 (94%)** |
| Symptom↔diagnosis collisions | 1 |
| Diagnoses with multi-ICD | 4 |
| Diagnosis candidate empty | 136 / 421 |
| Drug candidate empty | 35 / 171 |
| `isFamily` count | 3 |

Strong positive signal: free teachers largely **refuse procedure-as-test** (same qualitative finding as the partial paid pilot on doc 24).

## 5. Pairwise vs frozen v7 / v10

Corpus-summed exact span+type+text agreement (not a leaderboard score):

| vs | Exact agree | Overlap agree | Teacher additions | Other removals |
|----|------------:|--------------:|------------------:|---------------:|
| v7 | 1006 | 1532 | 1207 | 2230 |
| v10 | 1033 | 1554 | 1180 | 2203 |

Exact agreement is modest; free gold is **not** a near-drop-in replacement for v7 spans. Details: `comparison_v7_v10.tsv`, `schema_metrics.json`.

## 6. Diagnostic verdict

```text
FREE_ENSEMBLE_PARTIALLY_CORRECT_SCHEMA
```

Evidence for schema understanding:

- High procedure-as-test rejection (150/159).
- Five-class outputs only; ontology IDs come from local retrieval + judge selection.
- Near-zero symptom/diagnosis collisions.

Evidence against using as distillation gold / v11:

- ~32% fewer entities than v7; large symptom/test under-extraction.
- Low exact agreement with frozen v7/v10.
- Free-model JSON flake required parse softening + proposal skip for missing `type`.
- Judge is the same free family as extractor A (weaker independence than paid design).

## 7. Recommended architecture (updated)

```text
STILL_UNCERTAIN — lean task-specific span model (5+NONE), not free-teacher distillation
```

Free teachers are useful as a **diagnostic upper-bound probe** of schema rules (especially procedure vs test), not as competition pseudo-gold.

## 8. Next options (human decision)

1. Keep free corpus as analysis-only; continue manual annotation / local scorer from schema audit.
2. If budget available: re-run **paid** `default` profile with **new** user-chosen model IDs (do not silently reuse old placeholders).
3. Do **not** submit teacher outputs; do **not** mix into Viettel ZIP.
