# Schema-first principles audit — final report

Project: `schema_first_principles_audit`
Date: 2026-07-11
Branch: `tung` @ `0f7209159eeb6baa8e51034b49bec306e04e1b07`
Question: **Are we fundamentally following the wrong annotation schema?**

---

## 1. Artifact state

| Item | Value |
|------|-------|
| Base artifact | `output/v10_llm_conflict_resolution/base_v7_snapshot/` (100 JSON) |
| v10 artifact | `output/v10_llm_conflict_resolution/submission/` (100 JSON) |
| Traces | `output/v10_llm_conflict_resolution/trace/` (100 non-empty) |
| Inputs | `v_dataset/var/test/` (100 txt) |
| Base aggregate SHA256 | `faf5376280c764110013bda838c5b3a645287ebb3389400109b401c3728d18cd` |
| v10 aggregate SHA256 | `f8694c7154d86c759f70483e88f52410719ef89f106774a00c145e7c2db2f567` |
| Validation | all three 100-file checks **PASS** |
| Leaderboard used? | **No** (analysis only) |
| Pipelines rerun? | **No** |

Manifest: `analysis/schema_audit/artifact_manifest.json`.

---

## 2. Entity density

| Metric | Value |
|--------|------:|
| Total entities | **3236** |
| Documents | 100 |
| Min / median / mean / max per doc | 3 / 27.5 / 32.36 / 165 |

Density is high, but this report does **not** treat high count alone as proof of over-extraction. Audits below show a large share of schema-incompatible spans (especially procedure-as-test and overlong/mis-typed symptoms).

Full write-up: `analysis/schema_audit/entity_density.md`.

---

## 3. Entity counts by type

| Type | Count | Docs | Mean/doc |
|------|------:|-----:|---------:|
| TRIỆU_CHỨNG | 1920 | 100 | 19.20 |
| TÊN_XÉT_NGHIỆM | 696 | 96 | 6.96 |
| THUỐC | 271 | 58 | 2.71 |
| CHẨN_ĐOÁN | 215 | 66 | 2.15 |
| KẾT_QUẢ_XÉT_NGHIỆM | 134 | 44 | 1.34 |

Symptoms alone are ~59% of all entities. Test-names outnumber test-results ~5.2× (696 vs 134), inconsistent with official paired examples.

---

## 4. Provenance by component

Surviving final entities (trace first-add / span-lineage; 13 UNRESOLVED):

| Source | Surviving | Schema-flagged (risk≥3) | Flag rate |
|--------|----------:|------------------------:|----------:|
| ViHealthBERT | 2446 | 300 | 12.3% |
| section-aware recall | 316 | 113 | **35.8%** |
| lab-pair recall | 219 | 11 | 5.0% |
| clinical recall | 90 | 16 | 17.8% |
| ontology drug recall | 76 | 1 | 1.3% |
| ontology diagnosis recall | 76 | 30 | **39.5%** |
| UNRESOLVED | 13 | 0 | 0% |

**Top five suspicious sources (by absolute flagged count):**

1. ViHealthBERT (300) — also the Procedure→`TÊN_XÉT_NGHIỆM` remap root
2. section-aware recall (113) — overlong / merged symptoms
3. ontology diagnosis recall (30)
4. clinical recall (16)
5. lab-pair recall (11)

Details: `provenance_summary.tsv`.

---

## 5. Procedure-as-test findings

Among 696 `TÊN_XÉT_NGHIỆM`:

| Status | Count |
|--------|------:|
| LIKELY_GENUINE_TEST | 504 |
| LIKELY_PROCEDURE_NOT_TEST | **159** |
| AMBIGUOUS | 33 |

Required example **flagged**:

    đặt shunt dẫn lưu tĩnh mạch cửa qua da → LIKELY_PROCEDURE_NOT_TEST

This matches a foundational schema bug already documented historically in `state.md` (“Procedure renamed to XÉT_NGHIỆM”). Official schema has **no procedure class**; forcing procedures into test-name creates systematic FPs.

TSV: `test_name_audit.tsv`.

---

## 6. Test-name / test-result segmentation findings

`KẾT_QUẢ_XÉT_NGHIỆM` (134):

| Class | Count |
|-------|------:|
| VALUE_ONLY | 68 |
| QUALITATIVE_RESULT | 25 |
| OVERLONG_RESULT_CLAUSE | 31 |
| VALUE_PLUS_UNIT | 9 |
| NON_RESULT_PHRASE | 1 |

Only **9** results are clean value+unit spans; **31** are overlong clauses that likely include test names/connectors. Combined with 5.2× more test-names than results, segmentation policy is misaligned with the official example (`TWBC` / `14,43` split).

TSV: `test_result_audit.tsv`.

---

## 7. Drug-span findings

| Class | Count |
|-------|------:|
| AMBIGUOUS | 194 |
| NAME_ONLY_BUT_DETAILS_AVAILABLE | 46 |
| MAXIMAL_COMPLETE | 19 |
| TRUNCATED | 9 |
| ATTACHED_JUNK | 3 |

Known junk patterns (e.g. `atenololtrong`) appear; maximal medication expressions (official style) are rare (19/271). Drug linking is almost always singleton RxCUI (270/271 with 1 candidate; 1 unlinked).

Preserve prior probe conclusion: **do not** globally switch to ingredient-first / hedge ingredients.

TSV: `drug_span_audit.tsv`, `drug_candidate_audit.tsv`.

---

## 8. Symptom-span findings

| Class | Count |
|-------|------:|
| LIKELY_VALID_MINIMAL | 1593 |
| LIKELY_DIAGNOSIS | 135 |
| OVERLONG | 94 |
| NEGATION_INCLUDED | 44 |
| MERGED_MULTIPLE | 41 |
| GENERIC_STATUS | 9 |
| OTHER_SUSPICIOUS | 4 |

~17% of symptoms fail the “minimal complaint” hypothesis (non-minimal classes). Section-aware recall is a major producer of overlong/merged spans.

TSV: `symptom_span_audit.tsv`.

---

## 9. Diagnosis-span findings

| Flags | Count |
|-------|------:|
| ok | 196 |
| fragment | 7 |
| whole_explanatory_clause | 6 |
| symptom_mislabeled | 6 |

Most diagnosis spans look locally plausible; the larger diagnosis failure mode is **candidate-set policy** (Section 12) and **type collisions with symptoms** (Section 10), not raw span emptiness.

TSV: `diagnosis_span_audit.tsv`.

---

## 10. Type-collision findings

Overlap/containment collisions (excluding normalized-text aggregate rows):

| Pair | Count |
|------|------:|
| CHẨN_ĐOÁN ↔ TRIỆU_CHỨNG | **84** |
| TRIỆU_CHỨNG ↔ TÊN_XÉT_NGHIỆM | 31 |
| THUỐC ↔ TÊN_XÉT_NGHIỆM | 23 |
| KẾT_QUẢ_XÉT_NGHIỆM ↔ TÊN_XÉT_NGHIỆM | 12 |
| other | smaller |

Wrong-type overlaps are especially damaging under WER (FP + FN). Symptom↔diagnosis is the dominant confusion.

TSV: `type_collisions.tsv`.

---

## 11. Assertion-scope findings

Eligible entities audited: 2406 rows.

| Assertion | Count |
|-----------|------:|
| isHistorical | 686 |
| isNegated | 223 |
| isFamily | **0** |

Assertion risk flags: **220** rows ≠ `ok` (mostly `possible_missed_negation` 171, `negation_without_local_cue` 41, `negation_cue_inside_span` 7).

Family detection is effectively unimplemented in practice (0 predictions), despite detector config. Historical overreach is less dominant than negation/miss patterns in this heuristic pass, but section-based historical rules remain a structural risk for annotation review.

TSV: `assertion_audit.tsv`.

---

## 12. Diagnosis candidate-set findings

| Candidate count | Diagnoses |
|----------------:|----------:|
| 0 | 0 |
| 1 | **215** |
| 2+ | **0** |

The pipeline **always** returns a single ICD code. Official example requires multi-label (`K21.0`, `K21.9`). Offline lexical ICD alternatives support many sibling / specified–unspecified cases.

Multi-ICD review shortlist: **100** diagnoses (`multi_icd_candidate_review.tsv`).

---

## 13. Drug candidate findings

| Candidate count | Drugs |
|----------------:|------:|
| 0 | 1 |
| 1 | 270 |
| 2+ | 0 |

Almost pure singleton linking. Analysis-only; no ingredient-first global change recommended.

---

## 14. Precision-first preview

Offline only — **not** a submission:

| Metric | Count |
|--------|------:|
| Base entities | 3236 |
| Removed | **168** |
| Remaining | 3068 |

Removals by type: test-name 152, drug 7, symptom 5, result 4.
Mostly ViHealthBERT-sourced procedure-like test-names.

Paths:

- `output/schema_audit/precision_first_preview/`
- `analysis/schema_audit/precision_first_removals.tsv`

High-confidence pruning removes ~5% of entities — helpful, but **far from** closing the schema gap.

---

## 15. Top 100 highest-risk entities

Source: `entity_risk_ranking.tsv` (score ≥3: 471 entities; ≥5: 39).

| # | file | text | type | score | source | reasons |
|--:|------|------|------|------:|--------|---------|
| 1 | 15 | Điều trị chống đông | TÊN_XÉT_NGHIỆM | 7 | ViHealthBERT | procedure_as_test|ambiguous_section|section_heading_like |
| 2 | 35 | Nôn không ra máu, không ra dịch mật | TRIỆU_CHỨNG | 7 | section-aware recall | MERGED_MULTIPLE|assertion_risk:possible_missed_negation|type_collision|ambiguous |
| 3 | 46 | khó khăn với hạ huyết áp, không đặc hiệu | TRIỆU_CHỨNG | 7 | section-aware recall | MERGED_MULTIPLE|assertion_risk:possible_missed_negation|type_collision|ambiguous |
| 4 | 100 | cơn đau thắt ngực ổn định | TRIỆU_CHỨNG | 6 | ViHealthBERT | generic_status_as_symptom|type_collision|ambiguous_section |
| 5 | 15 | xuất huyết nội sọ không do chấn thương | TRIỆU_CHỨNG | 6 | section-aware recall | OVERLONG|assertion_risk:possible_missed_negation|type_collision |
| 6 | 36 | sinh thiết ghép thận | TÊN_XÉT_NGHIỆM | 6 | ViHealthBERT | procedure_as_test|type_collision|ambiguous_section |
| 7 | 36 | sinh thiết ghép thận | TÊN_XÉT_NGHIỆM | 6 | ViHealthBERT | procedure_as_test|type_collision|ambiguous_section |
| 8 | 13 | tổn thương vùng âm hộ và mông bên phải | TRIỆU_CHỨNG | 5 | section-aware recall | MERGED_MULTIPLE|type_collision|ambiguous_section |
| 9 | 13 | Thời gian: Tình trạng ngày càng nặng trong 5 ngày | TRIỆU_CHỨNG | 5 | section-aware recall | OVERLONG|type_collision|ambiguous_section |
| 10 | 14 | đau ngực trái: gián đoạn, không liên quan đến gắng sức | TRIỆU_CHỨNG | 5 | section-aware recall | MERGED_MULTIPLE|assertion_risk:possible_missed_negation|ambiguous_section |
| 11 | 15 | xuất huyết nội sọ | TRIỆU_CHỨNG | 5 | ViHealthBERT | assertion_risk:possible_missed_negation|type_collision|ambiguous_section |
| 12 | 15 | xuất huyết nội sọ không do chấn thương, không đặc hiệu | CHẨN_ĐOÁN | 5 | ontology diagnosis recall | assertion_risk:possible_missed_negation|type_collision|ambiguous_section |
| 13 | 16 | hạ huyết áp, không đặc hiệu | TRIỆU_CHỨNG | 5 | section-aware recall | MERGED_MULTIPLE|assertion_risk:possible_missed_negation|ambiguous_section |
| 14 | 16 | hạ huyết áp | TRIỆU_CHỨNG | 5 | ViHealthBERT | assertion_risk:possible_missed_negation|type_collision|ambiguous_section |
| 15 | 16 | hạ huyết áp, không đặc hiệu | CHẨN_ĐOÁN | 5 | ontology diagnosis recall | assertion_risk:possible_missed_negation|type_collision|ambiguous_section |
| 16 | 17 | Sốt | TRIỆU_CHỨNG | 5 | ViHealthBERT | assertion_risk:possible_missed_negation|type_collision|ambiguous_section |
| 17 | 24 | ban đỏ xuất hiện nhiểu ở vị trí phẫu thuật | TRIỆU_CHỨNG | 5 | section-aware recall | OVERLONG|type_collision|ambiguous_section |
| 18 | 24 | phẫu thuật | TÊN_XÉT_NGHIỆM | 5 | ViHealthBERT | procedure_as_test|type_collision |
| 19 | 26 | phẫu thuật | TÊN_XÉT_NGHIỆM | 5 | ViHealthBERT | procedure_as_test|type_collision |
| 20 | 3 | ước tính mất ý thức có thể trong 30 giây | TRIỆU_CHỨNG | 5 | section-aware recall | OVERLONG|type_collision|ambiguous_section |
| 21 | 34 | thuốc giảm đau opioid | THUỐC | 5 | ViHealthBERT | type_collision|section_heading_like |
| 22 | 34 | thuốc giảm đau opioid | THUỐC | 5 | ViHealthBERT | assertion_risk:possible_missed_negation|section_heading_like |
| 23 | 35 | Ăn uống kém, ăn vào dễ nôn | TRIỆU_CHỨNG | 5 | section-aware recall | MERGED_MULTIPLE|type_collision|ambiguous_section |
| 24 | 38 | Tăng tăng cân 3 pound trong 7 ngày qua | TRIỆU_CHỨNG | 5 | section-aware recall | OVERLONG|type_collision|ambiguous_section |
| 25 | 44 | giảm khả năng quan hệ tình dục với bạn tình | TRIỆU_CHỨNG | 5 | section-aware recall | OVERLONG|type_collision|ambiguous_section |
| 26 | 44 | từng đợt sau khi ăn trong 3 ngày qua | TRIỆU_CHỨNG | 5 | section-aware recall | OVERLONG|type_collision|ambiguous_section |
| 27 | 48 | Mức độ nghiêm trọng: Không được chỉ định | TRIỆU_CHỨNG | 5 | section-aware recall | OVERLONG|assertion_risk:possible_missed_negation|ambiguous_section |
| 28 | 48 | Các yếu tố làm trầm trọng thêm: Không được chỉ định | TRIỆU_CHỨNG | 5 | section-aware recall | OVERLONG|assertion_risk:possible_missed_negation|ambiguous_section |
| 29 | 5 | hạ huyết áp | TRIỆU_CHỨNG | 5 | ViHealthBERT | assertion_risk:possible_missed_negation|type_collision|ambiguous_section |
| 30 | 5 | hạ huyết áp, không đặc hiệu | CHẨN_ĐOÁN | 5 | ontology diagnosis recall | assertion_risk:possible_missed_negation|type_collision|ambiguous_section |
| 31 | 54 | phân và máu trong trực tràng (thỉnh thoảng) | TRIỆU_CHỨNG | 5 | section-aware recall | MERGED_MULTIPLE|type_collision|ambiguous_section |
| 32 | 54 | viêm phổi thuỳ, không đặc hiệu | TRIỆU_CHỨNG | 5 | section-aware recall | MERGED_MULTIPLE|assertion_risk:possible_missed_negation|ambiguous_section |
| 33 | 58 | chọc dò dịch não | TÊN_XÉT_NGHIỆM | 5 | ViHealthBERT | procedure_as_test|type_collision |
| 34 | 58 | Các yếu tố làm nặng thêm: Không ghi rõ | TRIỆU_CHỨNG | 5 | section-aware recall | OVERLONG|assertion_risk:possible_missed_negation|ambiguous_section |
| 35 | 58 | Các yếu tố làm giảm bớt: Không ghi rõ | TRIỆU_CHỨNG | 5 | section-aware recall | OVERLONG|assertion_risk:possible_missed_negation|ambiguous_section |
| 36 | 58 | hạ huyết áp | TRIỆU_CHỨNG | 5 | ViHealthBERT | assertion_risk:possible_missed_negation|type_collision|ambiguous_section |
| 37 | 58 | hạ huyết áp, không đặc hiệu | CHẨN_ĐOÁN | 5 | ontology diagnosis recall | assertion_risk:possible_missed_negation|type_collision|ambiguous_section |
| 38 | 64 | đi tiêu bình thường, không ra máu | TRIỆU_CHỨNG | 5 | section-aware recall | MERGED_MULTIPLE|assertion_risk:possible_missed_negation|ambiguous_section |
| 39 | 77 | ý nghĩ tự tử, có nghĩ tự bắn vào đầu | TRIỆU_CHỨNG | 5 | section-aware recall | MERGED_MULTIPLE|type_collision|ambiguous_section |
| 40 | 10 | chỉ cho thấy một u tuyến | KẾT_QUẢ_XÉT_NGHIỆM | 4 | clinical recall | OVERLONG_RESULT_CLAUSE|type_collision |
| 41 | 11 | chọc dò màng phổi 3L4 | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 42 | 11 | chọc dò dịch ổ bụng | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 43 | 12 | công thức máu (cbc) nâng cao lên 11.3 | KẾT_QUẢ_XÉT_NGHIỆM | 4 | clinical recall | OVERLONG_RESULT_CLAUSE|type_collision |
| 44 | 16 | Truyền dịch tĩnh mạch | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 45 | 17 | Dẫn lưu dịch | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 46 | 17 | Dẫn lưu dịch mủ | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 47 | 20 | ngã với gãy cổ xương đùi di lệch | TRIỆU_CHỨNG | 4 | section-aware recall | OVERLONG|type_collision |
| 48 | 20 | không thuốc cản quang cho thấy tim to | KẾT_QUẢ_XÉT_NGHIỆM | 4 | clinical recall | OVERLONG_RESULT_CLAUSE|type_collision |
| 49 | 20 | xẹp phổi | CHẨN_ĐOÁN | 4 | ontology diagnosis recall | assertion_risk:negation_without_local_cue|type_collision |
| 50 | 20 | xẹp phổi hai đáy | TRIỆU_CHỨNG | 4 | ViHealthBERT | assertion_risk:negation_without_local_cue|type_collision |
| 51 | 24 | cắt bỏ tuyến vú trái | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 52 | 26 | đến khám vì sau cân sau phẫu thuật | TRIỆU_CHỨNG | 4 | section-aware recall | OVERLONG|type_collision |
| 53 | 28 | phẫu thuật cắt bỏ tuyến tiền liệt | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 54 | 28 | sỏi | TRIỆU_CHỨNG | 4 | ViHealthBERT | assertion_risk:possible_missed_negation|type_collision |
| 55 | 28 | sỏi mật | CHẨN_ĐOÁN | 4 | ontology diagnosis recall | assertion_risk:possible_missed_negation|type_collision |
| 56 | 3 | Tỉnh dậy thấy cháu gái hét lên | TRIỆU_CHỨNG | 4 | section-aware recall | generic_status_as_symptom|ambiguous_section |
| 57 | 3 | chụp cắt lớp vi tính sọ não | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 58 | 3 | chụp cắt lớp vi tính sọ não | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 59 | 30 | Thuốc giảm đau | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | ambiguous_section|section_heading_like |
| 60 | 30 | Thuốc | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | ambiguous_section|section_heading_like |
| 61 | 30 | Thuốc giảm đau | THUỐC | 4 | ViHealthBERT | ambiguous_section|section_heading_like |
| 62 | 32 | chi trên không ghi nhận huyết khối | KẾT_QUẢ_XÉT_NGHIỆM | 4 | clinical recall | OVERLONG_RESULT_CLAUSE|type_collision |
| 63 | 32 | chi trên không ghi nhận huyết khối | KẾT_QUẢ_XÉT_NGHIỆM | 4 | clinical recall | OVERLONG_RESULT_CLAUSE|type_collision |
| 64 | 33 | tiền sử ho có đờm trắng | TRIỆU_CHỨNG | 4 | section-aware recall | ambiguous_section|section_heading_like |
| 65 | 33 | phù chi dưới (ổn định) | TRIỆU_CHỨNG | 4 | section-aware recall | generic_status_as_symptom|ambiguous_section |
| 66 | 35 | không ra dịch mật | CHẨN_ĐOÁN | 4 | ViHealthBERT | assertion_risk:negation_cue_inside_span|type_collision |
| 67 | 36 | ghép thận không có bằng chứng đào thải kháng thể hữu hình cấ | KẾT_QUẢ_XÉT_NGHIỆM | 4 | clinical recall | OVERLONG_RESULT_CLAUSE|type_collision |
| 68 | 36 | ghép thận không có bằng chứng đào thải kháng thể hữu hình cấ | KẾT_QUẢ_XÉT_NGHIỆM | 4 | clinical recall | OVERLONG_RESULT_CLAUSE|type_collision |
| 69 | 37 | xét nghiệm bất thường - tăng kali máu | TRIỆU_CHỨNG | 4 | section-aware recall | OVERLONG|type_collision |
| 70 | 38 | (ure) 3 | KẾT_QUẢ_XÉT_NGHIỆM | 4 | clinical recall | OVERLONG_RESULT_CLAUSE|type_collision |
| 71 | 4 | NSAID | THUỐC | 4 | ViHealthBERT | empty_candidates|ambiguous_section |
| 72 | 4 | khu trú vùng cạnh cột sống bên trái đoạn giữa lưng | TRIỆU_CHỨNG | 4 | ViHealthBERT | OVERLONG|assertion_risk:possible_missed_negation |
| 73 | 40 | khó thở khi nằm đột ngột (paroxysmal nocturnal dyspnea) | TRIỆU_CHỨNG | 4 | section-aware recall | OVERLONG|assertion_risk:negation_without_local_cue |
| 74 | 46 | hạ huyết áp | TRIỆU_CHỨNG | 4 | ViHealthBERT | assertion_risk:possible_missed_negation|type_collision |
| 75 | 46 | hạ huyết áp, không đặc hiệu | CHẨN_ĐOÁN | 4 | ontology diagnosis recall | assertion_risk:possible_missed_negation|type_collision |
| 76 | 46 | không đặc hiệu | TRIỆU_CHỨNG | 4 | ViHealthBERT | assertion_risk:possible_missed_negation|type_collision |
| 77 | 46 | stent | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 78 | 5 | (aspartate aminotransferase) là 319 | KẾT_QUẢ_XÉT_NGHIỆM | 4 | clinical recall | OVERLONG_RESULT_CLAUSE|type_collision |
| 79 | 5 | (alanine aminotransferase) là 690 | KẾT_QUẢ_XÉT_NGHIỆM | 4 | clinical recall | OVERLONG_RESULT_CLAUSE|type_collision |
| 80 | 50 | prednisone 40 mg | THUỐC | 4 | ontology drug recall | assertion_risk:possible_missed_negation|type_collision |
| 81 | 51 | khám | TÊN_XÉT_NGHIỆM | 4 | lab-pair recall | ambiguous_section|section_heading_like |
| 82 | 52 | cắt bỏ ống dẫn mật chủ | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 83 | 52 | cắt bỏ phân đoạn bên trái gan | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 84 | 54 | cắt bỏ một phần thận phải | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 85 | 54 | cắt bỏ tuyến thượng thận phải | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 86 | 54 | viêm phổi thuỳ | TRIỆU_CHỨNG | 4 | ViHealthBERT | assertion_risk:possible_missed_negation|type_collision |
| 87 | 54 | viêm phổi thuỳ, không đặc hiệu | CHẨN_ĐOÁN | 4 | ontology diagnosis recall | assertion_risk:possible_missed_negation|type_collision |
| 88 | 54 | truyền máu | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 89 | 58 | hạ huyết áp | TRIỆU_CHỨNG | 4 | ViHealthBERT | assertion_risk:possible_missed_negation|type_collision |
| 90 | 58 | hạ huyết áp, không đặc hiệu | CHẨN_ĐOÁN | 4 | ontology diagnosis recall | assertion_risk:possible_missed_negation|type_collision |
| 91 | 58 | tỉnh chậm | TRIỆU_CHỨNG | 4 | ViHealthBERT | generic_status_as_symptom|ambiguous_section |
| 92 | 58 | tỉnh chậm | TRIỆU_CHỨNG | 4 | ViHealthBERT | generic_status_as_symptom|ambiguous_section |
| 93 | 58 | Chẩn đoán hình ảnh | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | ambiguous_section|section_heading_like |
| 94 | 58 | chọc dò dịch não tủy | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 95 | 58 | Truyền dịch tĩnh mạch | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 96 | 59 | Phẫu thuật đặt cảng | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 97 | 61 | chụp cắt lớp vi tính | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |
| 98 | 63 | viêm túi mật cấp | CHẨN_ĐOÁN | 4 | ontology diagnosis recall | assertion_risk:possible_missed_negation|type_collision |
| 99 | 63 | viêm túi mật cấp tính | TRIỆU_CHỨNG | 4 | ViHealthBERT | assertion_risk:possible_missed_negation|type_collision |
| 100 | 69 | Cắt bỏ thận trái | TÊN_XÉT_NGHIỆM | 4 | ViHealthBERT | procedure_as_test|ambiguous_section |

---

## 16. Annotation-pool summary

| Field | Value |
|-------|-------|
| Path | `analysis/schema_audit/annotation_pool.csv` |
| Row count | **415** (deduped entities; category tags overlap) |

Category tag counts:

| Category | Tags |
|----------|-----:|
| procedure_as_test | 159 |
| test_name_result | 60 |
| symptom_case | 60 |
| diagnosis_case | 60 |
| drug_case | 40 |
| assertion_case | 40 |
| multi_icd | 40 |
| clean_control | 40 |
| v10_replacement | 39 |

All human_* columns left empty for annotation.

---

## 17. Root-cause verdict

**Yes — we are fundamentally following the wrong annotation schema in several coupled ways.**

Primary verdict labels (evidence-ranked):

1. **WRONG_TYPE_SCHEMA** — Procedure/Treatment NER class remapped into `TÊN_XÉT_NGHIỆM`; 159 likely procedures; Disease↔symptom typing collisions (84 pairs).
2. **WRONG_SPAN_POLICY** — Official examples want minimal symptoms, maximal drugs, split test name/result; pipeline often does the opposite (overlong symptoms, rare maximal drugs, overlong results).
3. **OVER_EXTRACTION** — 3236 entities with large FP subclasses (procedures, generic status, merged symptoms), not merely “rich notes”.
4. **CANDIDATE_SET_FAILURE** — ICD always singleton vs official multi-label sets.
5. **DISTRIBUTED_PIPELINE_FAILURE** — FPs arise from NER **and** multiple recalls; pruning one component cannot fix the schema mismatch.
6. **ASSERTION_SCOPE_FAILURE** (secondary) — 0 `isFamily`; 220 assertion-risk rows; section heuristics remain brittle.

v7–v10 model/rule iteration stayed near ~24 points because improvements operated **inside** this mismatched schema rather than correcting it.

---

## 18. Recommended new architecture

### Primary

**Task-specific span model with five labels + NONE (procedure rejection), dedicated lab name/result segmentation, joint/contextual assertions, and multi-label ICD candidate-set ranking.**
Use v7 / Qwen / rules / ontologies only as weak-supervision teachers. See `architecture_decision.md`.

### Fallback

Precision-first gates on current v7 (reject procedure-as-test; shrink section-aware spans; stop ungated Procedure→test remap) while annotation proceeds — bridge only.

---

## 19. Next concrete implementation task

After annotation begins on `annotation_pool.csv`:

1. Annotate the pool (keep/correct span/type/assertions/candidates) — prioritize all `procedure_as_test` + symptom/diagnosis collisions.
2. Build a **local scorer** mirroring competition WER / J_assertion / J_candidates on the annotated subset.
3. Train / evaluate a **NONE-aware type (or span) classifier** that rejects procedures and generic status; measure lift vs frozen base-v7 on the local gold.
4. Only then design any new pipeline version (not “v11 additive”); keep v7 as leaderboard reference until local gold shows clear gains.

Do **not** declare a model version successful from this audit alone.
