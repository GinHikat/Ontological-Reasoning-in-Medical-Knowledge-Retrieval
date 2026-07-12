# Schema metrics — openrouter_schema_teacher

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`

```json
{
  "n_files": 1,
  "teacher_total_entities": 22,
  "v7_total_entities": 32,
  "density_ratio_vs_v7": 0.6875,
  "by_type": {
    "CHẨN_ĐOÁN": 2,
    "TRIỆU_CHỨNG": 17,
    "THUỐC": 3
  },
  "procedure_as_test_total_audit": 159,
  "procedure_as_test_rejected": 7,
  "test_name_count": 0,
  "paired_test_name_result": 0,
  "overlong_result_spans": 0,
  "symptom_diagnosis_collisions": 0,
  "symptoms_with_negation_cue_inside": 0,
  "drugs_maximal_proxy": 0,
  "diagnoses_multi_icd": 0,
  "isFamily_count": 0,
  "diagnosis_candidate_count_distribution": {
    "0": 2
  },
  "drug_candidate_count_distribution": {
    "0": 1,
    "1": 2
  },
  "pairwise_summary_v7": {
    "exact_agreement_sum": 11,
    "overlap_agreement_sum": 19,
    "additions_sum": 11,
    "removals_sum": 21
  },
  "pairwise_summary_v10": {
    "exact_agreement_sum": 12,
    "overlap_agreement_sum": 20,
    "additions_sum": 10,
    "removals_sum": 20
  }
}
```
