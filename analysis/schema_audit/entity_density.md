# Entity density

- Total entities (base-v7 snapshot): **3236**
- Documents: **100**
- Min / median / mean / max per document: **3 / 27.5 / 32.36 / 165**

Note: ~3,236 entities / 100 docs is high relative to typical clinical notes, but density alone is not proof of over-extraction — see type audits.

## By type

| Type | Count | Docs containing | Mean/doc | Median/doc | Len p50 | Len p90 |
|------|------:|----------------:|---------:|-----------:|-------:|-------:|
| CHẨN_ĐOÁN | 215 | 66 | 2.15 | 2.0 | 17 | 33 |
| KẾT_QUẢ_XÉT_NGHIỆM | 134 | 44 | 1.34 | 2.0 | 7 | 45 |
| THUỐC | 271 | 58 | 2.71 | 3.5 | 10 | 19 |
| TRIỆU_CHỨNG | 1920 | 100 | 19.20 | 15.5 | 14 | 30 |
| TÊN_XÉT_NGHIỆM | 696 | 96 | 6.96 | 5.0 | 10 | 26 |
