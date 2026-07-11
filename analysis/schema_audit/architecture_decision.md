# Architecture decision (schema-first audit)

Date: 2026-07-11  
Evidence base: `analysis/schema_audit/*` over frozen `output/v10_llm_conflict_resolution/base_v7_snapshot/` (3236 entities / 100 docs).  
This is **not** a new model version. No leaderboard submission.

---

## Measured findings that drive the decision

| Finding | Evidence |
|---------|----------|
| Procedure forced into test-name | **159 / 696** `TÊN_XÉT_NGHIỆM` flagged `LIKELY_PROCEDURE_NOT_TEST` (22.8%); required example `đặt shunt dẫn lưu tĩnh mạch cửa qua da` flagged |
| Symptom ↔ diagnosis type collisions | **84** overlap/containment pairs `CHẨN_ĐOÁN ↔ TRIỆU_CHỨNG` |
| Symptom over-span / mislabel | 327/1920 non-minimal classes (OVERLONG/MERGED/LIKELY_DIAGNOSIS/NEGATION/GENERIC/…) |
| ICD candidates almost always singleton | **215 / 215** diagnoses have exactly **1** candidate; official example needs multi-label (`K21.0`,`K21.9`) |
| isFamily absent | **0** `isFamily` predictions |
| Errors distributed, not one recall bug | ViHealthBERT introduces most entities (2446 surviving) and most absolute flags (300); section-aware recall has high flag **rate** (113/316 ≈ 36%); ontology diagnosis recall 30/76 ≈ 39% |
| Precision-first pruning helps but is insufficient | Offline high-confidence removals: **168 / 3236** (5.2%) — mostly procedure-as-test; leaves ~3068 entities |

Decision-rule application:

- Procedure/test confusion is **widespread** → dedicated test extractor + NONE/procedure rejection is required.
- Symptom/diagnosis collisions **dominate type collisions** → need task-specific five-label (+ NONE) typing, not Disease/Procedure remapping.
- Span-boundary failures are common (section-aware overlong symptoms, drug junk, overlong results) → span model preferred over BIO + ordered postprocessors alone.
- Assertion scope failures exist (220 risk-flagged assertion rows; 0 family) but are secondary to type/span schema mismatch.
- Candidate-set failure for ICD is **systematic** (always one code).
- Errors are **distributed across components** (NER + multiple recalls), not fixable by pruning one postprocessor.

---

## Primary recommendation

**Replace v7 as the main extractor with a task-specific span model trained for the official five-type schema (+ explicit NONE / procedure rejection), using v7 / Qwen / rules / ontologies only as weak supervision or teacher signals.**

Concrete target architecture:

1. **Span proposal + five-label classifier with NONE**  
   Labels: `TRIỆU_CHỨNG | TÊN_XÉT_NGHIỆM | KẾT_QUẢ_XÉT_NGHIỆM | CHẨN_ĐOÁN | THUỐC | NONE`  
   `NONE` absorbs procedures, demographics, anatomy-alone, generic status, headings.

2. **Dedicated lab segmentation head (or constrained decoder)**  
   Jointly emit test-name / test-result pairs; forbid procedure lexicon into test-name.

3. **Joint or second-stage assertion classifier**  
   Context window around the span; do not inherit section-wide historical flags blindly; implement real `isFamily`.

4. **Multi-label ICD candidate-set ranker**  
   Return top-*k* sibling/specified–unspecified sets when similarities are close (official multi-code pattern).

5. **Drug span + RxNorm linker as separate modules**  
   Keep prior probe conclusion: no global ingredient-first hedging.

Weak supervision sources (teachers, not the competition path):

- Frozen v7 spans/types (noisy)
- Qwen cache proposals (already local)
- Ontology lexical hits
- Human annotation pool (`annotation_pool.csv`)

---

## Fallback recommendation

If annotation volume is initially too small for a full span model:

**Precision-first pruning of current v7** before any new architecture:

1. Hard-reject procedure-like `TÊN_XÉT_NGHIỆM` (lexicon + procedure sections).
2. Drop generic-status `TRIỆU_CHỨNG`.
3. Cap / shrink section-aware recall spans (largest high-rate FP source among recalls).
4. Keep ViHealthBERT core but stop mapping raw `Procedure/Treatment` → `TÊN_XÉT_NGHIỆM` without a test-cue gate.

This is a **bridge**, not the end state — measured high-confidence removals only cut ~5% of entities; schema mismatch remains.

---

## What not to do next

- Do not build v11 as another additive LLM/rule stack on the same Procedure→test remap.
- Do not submit precision-first preview.
- Do not globally switch RxNorm to ingredient-first.
- Do not treat singleton ICD linking as finished.
