# Vietnamese Clinical NER & Entity Linking Pipeline

This repository processes unstructured Vietnamese clinical notes to extract medical entities, map them to international standard ontologies (ICD-10 for Diagnosis, RxNorm for Drugs), and identify contextual assertions (e.g., negation, historical).

## Core Architecture Overview

The system extracts 5 core labels:
1. `CHẨN_ĐOÁN` (Diagnosis) → Mapped to ICD-10
2. `THUỐC` (Medication/Drug) → Mapped to RxNorm
3. `TÊN_XÉT_NGHIỆM` (Procedure/Test Name)
4. `TRIỆU_CHỨNG` (Symptom/Phenotype)
5. `KẾT_QUẢ_XÉT_NGHIỆM` (Test/Lab Result)

The pipeline uses a BERT-based NER model for entity boundaries and SapBERT (English & Vietnamese variants) for zero-shot cosine similarity linking against standardized dictionaries.

**Current best scored pipeline:** `v7_structured` (leaderboard **24.79660**). See `state.md` for full changelog and scores.

---

## Repository Structure

```text
Ontological-Reasoning-in-Medical-Knowledge-Retrieval/
├── .env.example             # Template for environment variables
├── README.md                # This file
├── requirements.txt         # Python dependencies
├── state.md                 # Master project state, requirements & changelog
├── v_dataset/               # Clinical notes, ontologies, and model weights
│   ├── var/test/            # 100 sample clinical note .txt files
│   ├── statedict/           # Local NER weights (e.g. statedict/ner/vihealthbert)
│   └── viettel/             # Dictionaries and datasets for mapping
│       ├── base/            # CSV + .npy embedding dictionaries
│       └── mapping/         # Raw ontology sources (RxNorm, KG, etc.)
├── modules/                 # Core Python codebase (OOP components)
│   ├── core/                # Config, constants, Pydantic schemas
│   ├── components/          # NER, linking, postprocessing, assertions, formatting
│   ├── pipelines/           # Versioned pipeline builders (v5–v8)
│   ├── evaluation/          # run_pipeline.py and analysis scripts
│   ├── legacy/              # Frozen monolithic V5 rollback copies
│   ├── dataset/             # Dictionary preprocessing & embedding scripts
│   ├── model/               # NER inference / training helpers
│   └── utils.py             # Legacy EntityExtractor (DataFrame API)
├── docs/                    # Technical documentation
├── analysis/                # Experiment notes and ablation reports
└── output/                  # Versioned JSON submissions + traces
```

---

## Getting Started

### 0. Read first
Check the current state in [`state.md`](state.md).

### 1. Clone the Repository

```bash
git clone https://github.com/GinHikat/Ontological-Reasoning-in-Medical-Knowledge-Retrieval.git
cd Ontological-Reasoning-in-Medical-Knowledge-Retrieval
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
```

### 3. Install Python Dependencies

For fast installs, use [`uv`](https://github.com/astral-sh/uv):

```bash
pip install uv
uv pip install -r requirements.txt
```

*Or standard pip:*

```bash
pip install -r requirements.txt
```

---

## How to Run the System

### Step 1: Build the Dictionary Base
Download the mapping data from Hugging Face for this project and place it under `v_dataset/`. NER weights should live at `v_dataset/statedict/` (the inference code also falls back to legacy `modules/model/statedict/` if present).

```bash
mkdir -p v_dataset
cd v_dataset

git clone https://huggingface.co/datasets/zinzinmit/v_dataset .

# If the clone puts statedict at the repo root of the dataset, keep it under v_dataset/statedict
# (preferred). Older docs that moved it to modules/model/statedict are obsolete.
```

Ensure LFS objects are pulled for `statedict` and `viettel/base` dictionaries.

### Step 2: Run a Versioned Pipeline
The recommended entrypoint is `modules/evaluation/run_pipeline.py`:

```bash
# Canonical best scored run — output/v7_structured/runN/{submission,trace}/
python modules/evaluation/run_pipeline.py --pipeline v7_structured

# Refined V6 — output/v6_refined/runN/{submission,trace}/
python modules/evaluation/run_pipeline.py --pipeline v6_refined

# Refactored V5 — output/v5_refactored/runN/{submission,trace}/
python modules/evaluation/run_pipeline.py --pipeline v5_refactored

# V8 ablations (not submission candidates; see state.md)
python modules/evaluation/run_pipeline.py --pipeline v8_candidate_integrity
python modules/evaluation/run_pipeline.py --pipeline v8_candidate_rescue

# Quick smoke test on one note
python modules/evaluation/run_pipeline.py --pipeline v7_structured --samples 1

# Optional flat export for submission/evaluator compatibility
python modules/evaluation/run_pipeline.py --pipeline v7_structured --output-dir output_submission
```

Available pipelines: `legacy_v5`, `v5_refactored`, `v6_refined`, `v7_structured`, `v8_candidate_integrity`, `v8_candidate_rescue`.

By default, each run is saved under `output/<version>/runN/` where `<version>` defaults to the `--pipeline` name (override with `--version-name`). Inside each run:

- `submission/` — competition JSON files (`1.json`, `2.json`, …)
- `trace/` — step-by-step trace logs (`1_trace.txt`, …)

New runs auto-increment (`run1`, `run2`, …). Use `--no-trace` to disable traces.

The original monolithic runner remains available for rollback/reference:

```bash
python modules/evaluation/test_sample_pipeline.py
```

---

## Using the `EntityExtractor` Class in Code

The legacy `EntityExtractor` in `modules/utils.py` returns a raw Pandas DataFrame. Prefer the versioned pipelines above for competition JSON output.

```python
from modules.utils import EntityExtractor

extractor = EntityExtractor(mode="ner + retrieval")
clinical_note = "Bệnh nhân bị u ác đại tràng, uống paracetamol."
df_results = extractor.extract(clinical_note)
print(df_results.head())
```

**Strict JSON formatting** (`type`, `candidates`, `assertions`, `position`) is handled by `modules/components/formatting/competition_json.py` when using `modules/evaluation/run_pipeline.py`.
