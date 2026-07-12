# Schema metrics — openrouter_schema_teacher (free_first)

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`

```json
{
  "n_files": 100,
  "teacher_total_entities": 2213,
  "v7_total_entities": 3236,
  "density_ratio_vs_v7": 0.6838689740420272,
  "by_type": {
    "THUỐC": 171,
    "TRIỆU_CHỨNG": 1018,
    "TÊN_XÉT_NGHIỆM": 352,
    "KẾT_QUẢ_XÉT_NGHIỆM": 251,
    "CHẨN_ĐOÁN": 421
  },
  "procedure_as_test_total_audit": 159,
  "procedure_as_test_rejected": 150,
  "test_name_count": 352,
  "paired_test_name_result": 253,
  "overlong_result_spans": 13,
  "symptom_diagnosis_collisions": 1,
  "symptoms_with_negation_cue_inside": 21,
  "drugs_maximal_proxy": 43,
  "diagnoses_multi_icd": 4,
  "isFamily_count": 3,
  "diagnosis_candidate_count_distribution": {
    "0": 136,
    "1": 281,
    "2": 3,
    "3": 1
  },
  "drug_candidate_count_distribution": {
    "0": 35,
    "1": 136
  },
  "pairwise_summary_v7": {
    "exact_agreement_sum": 1006,
    "overlap_agreement_sum": 1532,
    "additions_sum": 1207,
    "removals_sum": 2230
  },
  "pairwise_summary_v10": {
    "exact_agreement_sum": 1033,
    "overlap_agreement_sum": 1554,
    "additions_sum": 1180,
    "removals_sum": 2203
  }
}
```
