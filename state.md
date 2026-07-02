# Master Project State & Specification: Vietnamese Clinical NER

This document serves as the single source of truth for the project's requirements, current state, and the execution plan. Any AI agent reading this should be able to fully understand the project constraints and goals without further user explanation.

## 1. Project Goal & Core Requirements
The objective is to process raw Vietnamese clinical notes (unstructured text) and extract specific medical entities, map them to international ontologies, and identify contextual assertions.

### 1.1 The 5 Required Entity Labels
The pipeline MUST output exactly these 5 labels (no broad English categories are allowed in the final output):
1.  **`CHẨN_ĐOÁN`** (Diagnosis)
2.  **`THUỐC`** (Medication/Drug)
3.  **`TÊN_XÉT_NGHIỆM`** (Procedure/Test Name)
4.  **`TRIỆU_CHỨNG`** (Symptom/Phenotype)
5.  **`KẾT_QUẢ_XÉT_NGHIỆM`** (Test/Lab Result)

### 1.2 Ontology Standardization (Strict Requirements)
Extracted entities for specific labels MUST be mapped to their standardized IDs (returned in the `candidates` array):
*   **`CHẨN_ĐOÁN`** ➡️ MUST be mapped to **ICD-10**. 
    *   *Reference File:* `data\viettel\combine\diagnosis_10.csv`
*   **`THUỐC`** ➡️ MUST be mapped to **RxNorm**.
    *   *Raw Data Source:* `F:\Din\Study\Education\Projects\Thesis\data\mapping\mapping\RxNorm`
    *   *Task:* A `drug_rxnorm.csv` term-ID mapping file must be created to facilitate this.

### 1.3 Contextual Assertions (Modifiers)
We must detect contextual states for the entities.
*   **Valid Flags:** `isNegated`, `isFamily`, `isHistorical`
*   **Applicable Labels:** These assertions are ONLY evaluated for `CHẨN_ĐOÁN`, `THUỐC`, and `TRIỆU_CHỨNG`.
*   *If an entity has no modifiers, its assertions list must be empty `[]`.*

---

## 2. Target Output & Submission Format
The final pipeline must produce predictions for the final test set.

*   **Test Set Location:** `VAR\data\var` (contains `1.txt`, `2.txt`, etc.)
*   **Output Location:** Must be saved in an `output/` directory.
*   **File Structure:** 1-to-1 mapping. `output/1.json` corresponds to the predictions for `VAR\data\var\1.txt`.

### 2.1 JSON Schema Requirement
Each `.json` file must contain a JSON array of dictionaries. Each dictionary represents one extracted entity and MUST match this exact schema:

```json
[
  {
    "text": "amlodipine 10 mg po daily",
    "type": "THUỐC",
    "candidates": ["308135"],
    "assertions": ["isHistorical"],
    "position": [58, 83]
  },
  {
    "text": "ho",
    "type": "TRIỆU_CHỨNG",
    "candidates": [],
    "assertions": [],
    "position": [196, 198]
  }
]
```
**Schema Details:**
*   `text` (String): The exact matched substring from the raw text.
*   `type` (String): One of the 5 required labels.
*   `candidates` (List[String]): The mapped Ontology ID (e.g., RxNorm ID or ICD-10 code). Empty array `[]` if no mapping is found or required.
*   `assertions` (List[String]): The contextual flags. Empty array `[]` if none apply.
*   `position` (List[Int]): Exactly two integers `[start, end]` representing the **character-level** index mapped to the original `.txt` string.

---

## 3. Current Execution Plan

To reach the target output format, the execution is divided into three phases:

### Phase 1: NER Post-Processing & Knowledge Graph Mapping
We will NOT retrain the base Vietnamese NER model (which currently outputs `Disease/Symptom`, `Procedure`, `Drug`). Instead, we will apply post-processing:
*   **`Disease/Symptom` ➡️ `CHẨN_ĐOÁN`** (Derived from ICD-10).
*   **`Drug` ➡️ `THUỐC`**.
*   **`Procedure` ➡️ `TÊN_XÉT_NGHIỆM`**.
*   **Missing Labels Extraction:**
    *   **`TRIỆU_CHỨNG`:** Extract by querying the Knowledge Graph (`data\viettel\mapping\external_kg.parquet`) for `Disease` or `Phenotype` relationships.
    *   **`KẾT_QUẢ_XÉT_NGHIỆM`:** We will evaluate translating the English `MIMIC-IV Radiology Note` dataset to train a specialized extractor for diagnostic and lab results.

### Phase 2: Contextual Assertion Detection
*   **Strategy:** Explore the candidate dataset [PeterPaker123/mimic-iv-clinical-ner](https://huggingface.co/datasets/PeterPaker123/mimic-iv-clinical-ner) on HuggingFace.
*   **Action:** Evaluate translating this English dataset into Vietnamese to fine-tune a localized assertion classifier, or utilize zero-shot cross-lingual transfer methods.

### Phase 3: Dictionary Standardization & Term-ID Mapping (Immediate Next Step)
*   **Action:** Inspect the raw RxNorm dataset available at `F:\Din\Study\Education\Projects\Thesis\data\mapping\mapping\RxNorm`.
*   **Goal:** Write a script to process `rxnorm_terms.csv` (and any related `rrf` files) to create a structured `term-ID` CSV file (`drug_rxnorm.csv`). This file must be formatted similarly to `diagnosis_10.csv` to serve as the unified dictionary lookup for resolving `THUỐC` candidates.

---

## 4. What has been done

We have implemented the initial end-to-end evaluation script (`modules/evaluation/test_sample_pipeline.py`). For a given input sentence (chunked by the test script), the pipeline currently follows these steps:

1.  **NER Extraction:** The text is passed through the base NER model, which extracts entities using its original, pre-trained classes (`Disease`, `Drug`, and `Procedure`).
2.  **Label Mapping:** These original classes are explicitly mapped to our standardized target labels:
    *   `Disease` (and variants) ➡️ `CHẨN_ĐOÁN`
    *   `Drug` (and variants) ➡️ `THUỐC`
    *   `Procedure` (and variants) ➡️ `TÊN_XÉT_NGHIỆM`
    > [!WARNING]
    > **Missing Classes:** Currently, **2 required classes are missing entirely** (`TRIỆU_CHỨNG` and `KẾT_QUẢ_XÉT_NGHIỆM`) because the base model does not predict them.
3.  **Knowledge Graph Retrieval:** For the mapped entities, we run dense retrieval (SapBERT) against our mapping datasets to fetch standard IDs:
    *   **Diagnoses (`CHẨN_ĐOÁN`):** Queried against `data/viettel/base/short_diagnosis.csv` to retrieve the **ICD-10 ID**.
    *   **Drugs (`THUỐC`):** Queried against `data/viettel/base/short_drug.csv` to retrieve the **RxNorm ID**.
4.  **Target Output Formatter:** Predictions are formatted into the exact JSON schema and saved in the `output/` directory. Assertions are defaulted to an empty list `[]`.

### Current Accomplishments & Limitations

> [!NOTE]
> **Accomplishment:** We successfully established an end-to-end inference and evaluation pipeline that reads raw inputs, extracts core medical entities, retrieves standard dictionary IDs, and structures the final output. This gives us our baseline evaluation score.

> [!IMPORTANT]
> **Limitations to Address:**
> 1.  **Missing Entity Types:** The system cannot detect Symptoms (`TRIỆU_CHỨNG`) or Lab Results (`KẾT_QUẢ_XÉT_NGHIỆM`).
> 2.  **Missing Contextual Assertions:** All modifiers (`isNegated`, `isFamily`, `isHistorical`) default to empty arrays; Phase 2 needs to be implemented.
> 3.  **Low ID Retrieval Accuracy:** The `J_candidates` score is quite low (`3.7516`), indicating that retrieval against the current short base dictionaries struggles to find correct IDs.

**Current Evaluation Results (1st Run):**
*   **Score (Điểm):** 8.33930
*   **WER:** 85.948
*   **J_assertion:** 8.7434
*   **J_candidates:** 3.7516
*   **Records Scored:** 100
