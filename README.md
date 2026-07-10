# Vietnamese Clinical NER & Entity Linking Pipeline

This repository is dedicated to processing unstructured Vietnamese clinical notes to extract medical entities, map them to international standard ontologies (ICD-10 for Diagnosis, RxNorm for Drugs), and identify contextual assertions (e.g., negation, family history).

## Core Architecture Overview

The system strictly adheres to extracting 5 core labels:
1. `CHẨN_ĐOÁN` (Diagnosis) -> Mapped to ICD-10
2. `THUỐC` (Medication/Drug) -> Mapped to RxNorm
3. `TÊN_XÉT_NGHIỆM` (Procedure/Test Name)
4. `TRIỆU_CHỨNG` (Symptom/Phenotype)
5. `KẾT_QUẢ_XÉT_NGHIỆM` (Test/Lab Result)

The pipeline utilizes a BERT-based NER model to locate entity boundaries within the text and relies on SapBERT (English & Vietnamese variants) to perform zero-shot cosine similarity mapping against massive standardized dictionaries for entity linking.

---

## Repository Structure

```text
VAR/
├── .env.example             # Template for environment variables
├── README.md                # This file
├── requirements.txt         # Python dependencies
├── state.md                 # Master project state & requirements definition
├── data/                    # Clinical notes and ontology databases
│   ├── var/test/            # 100 sample text files containing raw clinical notes
│   └── viettel/             # Dictionaries and datasets for mapping
│       ├── base/            # Extracted CSV and optimized .npy embedding dictionaries
│       ├── combine/         # Processed mapping dictionaries (e.g., RxNorm)
│       └── mapping/         # Raw source data for ontologies (RxNorm RRF files)
├── modules/                 # Core python codebase
│   ├── utils.py             # Main EntityExtractor class tying the pipeline together
│   ├── dataset/             # Scripts for preprocessing and running tests
│   │   ├── dataset_processing/  # Script to parse raw RxNorm RRFs -> short_drug.csv
│   │   ├── evaluation/          # The test pipeline (test_sample_pipeline.py)
│   │   └── preprocessing/       # Embeddings generator (generate_embeddings.py)
│   └── model/               # Inference algorithms and local model weights
│       ├── inference/       # NER inference class (inference_ner.py)
│       └── statedict/       # Hugging Face tokenizers/weights for NER & SapBERT
└── output/                  # Generated JSON outputs from test evaluation
```

---

## Getting Started

### 0. Read first 
Check the current state in state.md

### 1. Clone the Repository

```bash
git clone https://github.com/GinHikat/Ontological-Reasoning-in-Medical-Knowledge-Retrieval.git
cd Ontological-Reasoning-in-Medical-Knowledge-Retrieval
```

### 2. Set Up Environment Variables

Copy the example `.env` file and customize the variables to match your system paths and credentials:

```bash
cp .env.example .env
```

Ensure you provide the correct paths to the raw data files, specifically:
- Ensure the `RXNORM_RRF_PATH` is correctly configured in your environment if required for rebuilding base mappings.

### 3. Install Python Dependencies

For hyper-fast, reliable installation, it is recommended to use [`uv`](https://github.com/astral-sh/uv):

```bash
# Install uv locally
pip install uv

# Sync environment dependencies
uv pip install -r requirements.txt
```

*Or standard pip:*

```bash
pip install -r requirements.txt
```

---

## How to Run the System

### Step 1: Build the Dictionary Base
Download the mapping data from Huggingface for this project, place it in the data folder. Place the statedict folder to its correct path in modules/model

```bash
mkdir data
cd data

git clone https://huggingface.co/datasets/zinzinmit/v_dataset .

# Move statedict folder to its correct path
move statedict ../modules/model/

# or this in Linux 
mv statedict ../modules/model/
```

### Step 2: Run a Versioned Pipeline
The recommended runner is now the versioned pipeline entrypoint. It lets you compare old and new implementations without editing the core scripts.

```bash
# Refactored V5 — saves to output/v5_refactored/runN/{submission,trace}/
python modules/evaluation/run_pipeline.py --pipeline v5_refactored

# Refined V6 — saves to output/v6_refined/runN/{submission,trace}/
python modules/evaluation/run_pipeline.py --pipeline v6_refined

# Structured V7 — saves to output/v7_structured/runN/{submission,trace}/
python modules/evaluation/run_pipeline.py --pipeline v7_structured

# Quick smoke test on one note
# Saves to output/v6_refined/samples_1/{submission,trace}/
python modules/evaluation/run_pipeline.py --pipeline v6_refined --samples 1

# Optional flat export for submission/evaluator compatibility
python modules/evaluation/run_pipeline.py --pipeline v6_refined --output-dir output_submission
```

By default, each run is saved under `output/<version>/runN/` where `<version>` defaults to the `--pipeline` name (override with `--version-name`). Inside each run:

- `submission/` — competition JSON files (`1.json`, `2.json`, …)
- `trace/` — step-by-step trace logs (`1_trace.txt`, …)

New runs auto-increment (`run1`, `run2`, …).

The original monolithic runner is still available for rollback/reference:

```bash
python modules/evaluation/test_sample_pipeline.py
```

---

## Using the `EntityExtractor` Class in Code

The `EntityExtractor` class in `modules/utils.py` acts as the base utility for the system. Note that it returns a raw Pandas DataFrame.

```python
from VAR.modules.utils import EntityExtractor

# Initialize the extractor
extractor = EntityExtractor(mode="ner + retrieval")

clinical_note = "Bệnh nhân bị u ác đại tràng, uống paracetamol."

# Extract raw entities (returns a pandas DataFrame)
df_results = extractor.extract(clinical_note)

print(df_results.head())
```

**Note on strict JSON formatting:**
The strict JSON schema (with `type`, `candidates`, `assertions`, and `position`) is now handled by `modules/components/formatting/competition_json.py` when using `modules/evaluation/run_pipeline.py`. The legacy `test_sample_pipeline.py` script still contains its original inline formatting logic for rollback/reference.
