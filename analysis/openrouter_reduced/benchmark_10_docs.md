# Comparison — `benchmark_10_docs`

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`

- Docs compared: **10**
- Reduced entities: **251**
- Archived frontier entities: **319**
- Exact-span agreement (recall vs gold): **0.5141**
- Overlap agreement (recall vs gold): **0.6646**
- Type agreement on overlaps: **0.9623**
- Assertion agreement on overlaps: **0.7406**
- Candidate agreement: **0.6667**
- Additions / removals: **87 / 155**
- Procedure-as-test (reduced / gold): **0 / 1**
- Lab split agreement: **0.6356**

## Type distribution

| Type | Reduced | Gold |
|------|--------:|-----:|
| CHẨN_ĐOÁN | 38 | 54 |
| KẾT_QUẢ_XÉT_NGHIỆM | 48 | 49 |
| THUỐC | 18 | 25 |
| TRIỆU_CHỨNG | 99 | 122 |
| TÊN_XÉT_NGHIỆM | 48 | 69 |

## Runtime / API

| Metric | Value |
|--------|------:|
| Wall-clock (est.) | 1044s (~17.4 min) |
| API requests | 19 |
| Requests / doc | 1.9 |
| Extraction requests | 10 |
| Candidate batches | 3 |
| Documents judged | 6 |
| Input tokens | 106952 |
| Output tokens | 83668 |
| 429 count | 0 |
| Retry count | 0 |
| Parse failures | 0 |

## Success gates

| Gate | Result |
|------|--------|
| 100% valid JSON | PASS |
| 100% exact source spans | PASS |
| No invented candidate IDs | PASS |
| ≥90% exact-or-overlap vs archived frontier | **FAIL** (overlap recall 0.665) |
| ≥95% type agreement on overlaps | PASS (0.962) |
| ≤2.0 API requests / doc | PASS (1.9) |
| No unrecovered rate-limit failure | PASS |
| Cache resume | N/A this run (cold) |

**Benchmark gate decision:** do **not** proceed to full 100-document run.

Preferred target 1.0–1.4 req/doc was not met (1.9), but hard cap ≤2.0 passed.
Quality vs archived ensemble gold is the blocking failure.

