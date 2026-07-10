# Refactor Architecture for Iterative Pipeline Refinement

This refactor introduces a versioned, OOP-oriented architecture while preserving the current working V5 code.

## Goals

1. Keep old working code available for rollback and regression comparison.
2. Make each metric-sensitive subsystem replaceable independently.
3. Support iterative versions such as `legacy_v5`, `v5_refactored`, `v6_refined`, `v7_structured`, `v8_*`, and future ablations.
4. Avoid editing one large monolithic script for every experiment.

## Key Design Choice

Use composition for full pipelines and inheritance for small component contracts.

Good inheritance targets:

- `BaseNERExtractor`
- `BaseMentionPostProcessor`
- `BaseEntityClassifier`
- `BaseEntityLinker`
- `BaseAssertionDetector`
- `BaseOutputFormatter`

Avoid inheriting from the old monolithic `EntityExtractor` or `test_sample_pipeline.py` logic for new experiments. They are preserved under `modules/legacy` instead.

## New Structure

```text
modules/
├── legacy/
│   ├── utils_legacy.py
│   └── test_sample_pipeline_legacy.py
├── core/
│   ├── schemas.py
│   ├── constants.py
│   └── config.py
├── components/
│   ├── ner/
│   ├── normalization/
│   ├── postprocessing/
│   ├── classification/
│   ├── linking/
│   ├── assertions/
│   ├── structure/
│   └── formatting/
├── pipelines/
│   ├── base.py
│   ├── clinical.py
│   ├── legacy_adapter.py
│   ├── v5.py
│   ├── v6.py
│   ├── v7.py
│   ├── v8.py
│   └── factory.py
└── evaluation/
    └── run_pipeline.py
```

## Current Pipeline Versions

| Pipeline | Purpose |
|---|---|
| `legacy_v5` | Adapter around the frozen V5 helper logic. Useful for regression checks. |
| `v5_refactored` | Same main behavior rebuilt from composable classes. |
| `v6_refined` | Type correction, test/result recall, precision filtering, overlap dedup. |
| `v7_structured` | Section-aware + ontology lexical recall on top of V6. **Current best scored** (24.79660). |
| `v8_candidate_integrity` | Ablation: unconditional unambiguous RxCUI preset override (negative / not for submission). |
| `v8_candidate_rescue` | Ablation: rescue-only linking for unlinked drugs + provenance transfer (no-op in same-env test). |

Run any version with:

```bash
python modules/evaluation/run_pipeline.py --pipeline v7_structured
python modules/evaluation/run_pipeline.py --pipeline v6_refined
python modules/evaluation/run_pipeline.py --pipeline v5_refactored
python modules/evaluation/run_pipeline.py --pipeline legacy_v5
```

For a quick smoke test:

```bash
python modules/evaluation/run_pipeline.py --pipeline v7_structured --samples 1 --output-dir output_smoke
```

Note: local NER weights under `v_dataset/statedict/ner/...` must be present for a full run (legacy fallback: `modules/model/statedict/ner/...`).

## Pipeline Flow

```text
Document
  -> Normalizer
  -> NER extractor
  -> Pre-classification mention postprocessors
  -> Label classifier
  -> Post-classification mention postprocessors
       - ClinicalTypeCorrectionPostProcessor
       - DrugBoundaryPostProcessor
       - [V7+] SectionAware / LabPair / Ontology drug+diagnosis recall
       - ClinicalRecallPostProcessor
       - [V7+] CandidateMergePostProcessor
       - [V8 rescue] DrugOntologyProvenanceTransferPostProcessor
       - ClinicalPrecisionFilterPostProcessor
       - OverlapDedupPostProcessor
  -> Entity linker
  -> Assertion detector (restricts assertions to competition labels)
  -> Competition JSON formatter
```

## Implemented V6 Postprocessors

1.  **`ClinicalTypeCorrectionPostProcessor`**: Corrects systematic classification errors, e.g., mapping symptom phrases away from diagnosis tags and restoring drug mentions mislabeled as procedures.
2.  **`DrugBoundaryPostProcessor`**: Scans for dosage and frequency context around drug names using regex and expands the span.
3.  **`ClinicalRecallPostProcessor`**: Recalls high-value missed tests (e.g. `ECG`, `CEA`), symptoms (`ho`, `sốt`, `khó thở`), and automatically parses numeric lab results (e.g. `glucose 6.8`) from note sections.
4.  **`ClinicalPrecisionFilterPostProcessor`**: Removes common noise terms (e.g. "nhẹ", "nặng", "bệnh lý") and standalone dosage tokens (e.g. "po", "bid", "mg").
5.  **`OverlapDedupPostProcessor`**: Resolves nesting and duplicate conflicts in the final prediction list.

## Implemented V7+ Components

1.  **`VietnameseClinicalSectionParser`**: Shared section boundaries with original character offsets.
2.  **`SectionAwareRecallPostProcessor`**: Symptom bullets / short reason-for-admission phrases.
3.  **`LabPairRecallPostProcessor`**: Lab name/result pairs from structured note text.
4.  **`OntologyDrugRecallPostProcessor` / `OntologyDiagnosisRecallPostProcessor`**: Lexical ontology recovery.
5.  **`CandidateMergePostProcessor`**: Deterministic conflict resolution by evidence source.
6.  **`DrugOntologyProvenanceTransferPostProcessor`** (V8 rescue): Transfer unambiguous RxCUI provenance to expanded drug spans.

## Future Improvement Ideas

1.  **Upgrade the Drug Dictionary (RxNorm Expansion)**: Update dictionary construction to include a larger database of RxNorm codes to improve matching accuracy.
2.  **AbbreviationNormalizer**: Add component to resolve clinical abbreviations (`THA` -> `tăng huyết áp`, `ĐTĐ` -> `đái tháo đường`) prior to NER or linking.
3.  **Context-Aware Classifier**: Integrate a cross-encoder model to dynamically resolve ambiguous entities based on neighboring text window content.
4.  **Reduce nested/overlapping spans** and block embedded drug aliases inside symptom phrases (see `state.md` remaining ideas).
