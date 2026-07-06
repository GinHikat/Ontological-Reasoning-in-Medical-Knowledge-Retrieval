# Refactor Architecture for Iterative Pipeline Refinement

This refactor introduces a versioned, OOP-oriented architecture while preserving the current working V5 code.

## Goals

1. Keep old working code available for rollback and regression comparison.
2. Make each metric-sensitive subsystem replaceable independently.
3. Support iterative versions such as `legacy_v5`, `v5_refactored`, `v6_lab_results`, `v6_thresholds`, and future reranker/ensemble versions.
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
│   └── formatting/
├── pipelines/
│   ├── base.py
│   ├── clinical.py
│   ├── legacy_adapter.py
│   ├── v5.py
│   └── factory.py
└── evaluation/
    └── run_pipeline.py
```

## Current Pipeline Versions

| Pipeline | Purpose |
|---|---|
| `legacy_v5` | Adapter around the frozen V5 helper logic. Useful for regression checks. |
| `v5_refactored` | Same main behavior rebuilt from composable classes. Default for future work. |

Run either version with:

```bash
python modules/evaluation/run_pipeline.py --pipeline v5_refactored
python modules/evaluation/run_pipeline.py --pipeline legacy_v5
```

For a quick smoke test:

```bash
python modules/evaluation/run_pipeline.py --pipeline v5_refactored --samples 1 --output-dir output_smoke
```

Note: the local model weights under `modules/model/statedict/ner/...` must be present for a full run.

## Pipeline Flow

```text
Document
  -> Normalizer
  -> NER extractor
  -> Pre-classification mention postprocessors
  -> Label classifier
  -> Post-classification mention postprocessors
  -> Entity linker
  -> Assertion detector
  -> Competition JSON formatter
```

## How to Add V6 Improvements

Create a new builder, for example `modules/pipelines/v6.py`, and register it in `modules/pipelines/factory.py`.

Suggested next components:

1. `LabResultPostProcessor` for `KẾT_QUẢ_XÉT_NGHIỆM` recall.
2. `AbbreviationNormalizer` for `THA`, `ĐTĐ`, `NMCT`, `XN`, `CTM`, etc.
3. `PerTypeThresholdHybridLinker` extending `HybridEntityLinker`.
4. `ContextAwareDiseaseSymptomClassifier` extending the current label mapper/retrieval split.
5. `OverlapDedupPostProcessor` for final duplicate cleanup.

Each component should be tested by registering a new pipeline version instead of mutating the current best pipeline directly.
