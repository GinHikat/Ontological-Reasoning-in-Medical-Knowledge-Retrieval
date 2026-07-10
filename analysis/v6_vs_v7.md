# v6 vs v7 diagnostic comparison

## Totals

| Metric | v6_refined | v7_structured |
|---|---:|---:|
| total entities | 2644 | 3160 |
| CHẨN_ĐOÁN | 104 | 216 |
| THUỐC | 165 | 276 |
| TRIỆU_CHỨNG | 1703 | 1877 |
| TÊN_XÉT_NGHIỆM | 559 | 655 |
| KẾT_QUẢ_XÉT_NGHIỆM | 113 | 136 |
| diagnosis with candidates | 104 | 216 |
| diagnosis without candidates | 0 | 0 |
| drug with candidates | 163 | 274 |
| drug without candidates | 2 | 2 |
| assertion isHistorical | 543 | 675 |
| assertion isNegated | 206 | 227 |
| assertion isFamily | 0 | 0 |
| span text_mismatch | 0 | 0 |
| span invalid_start_end | 0 | 0 |
| span zero_length | 0 | 0 |
| span duplicate_exact_spans | 4 | 0 |
| span overlapping_spans | 60 | 285 |
| span nested_spans | 49 | 273 |

## v7 relative to v6

- **new_entities_only_in_v7**: 643
- **entities_removed_from_v6**: 123
- **same_spans_changed_labels**: 100
- **same_spans_changed_candidates**: 92
- **same_spans_changed_assertions**: 51
