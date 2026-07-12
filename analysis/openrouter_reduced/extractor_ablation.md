# Extractor ablation (offline, cached aligned outputs)

**Reference:** `archives/openrouter_schema_teacher_free_2026-07-12/diagnostic_pseudo_gold/` (2213 ents, 100 docs)

**API calls:** none

## Results

| Config | Exact recall | Overlap recall | Type agree | Assert agree | Ent Δ | Proc-as-test survival | Lab split | Sym/Dx | Unique exact support |
|--------|-------------:|---------------:|-----------:|-------------:|------:|----------------------:|----------:|-------:|---------------------:|
| `A_only` | 0.711 | 0.823 | 0.986 | 0.847 | -179 | 10/159 | 0.789 | 0.839 | 1574 |
| `B_only` | 0.363 | 0.399 | 0.979 | 0.948 | -1211 | 14/159 | 0.345 | 0.411 | 804 |
| `C_only` | 0.581 | 0.642 | 0.965 | 0.873 | -578 | 18/159 | 0.640 | 0.603 | 1286 |
| `A_B_union` | 0.810 | 0.891 | 0.986 | 0.874 | 196 | 22/159 | 0.857 | 0.900 | 1792 |
| `A_C_union` | 0.851 | 0.920 | 0.990 | 0.876 | 387 | 22/159 | 0.914 | 0.921 | 1884 |
| `B_C_union` | 0.709 | 0.768 | 0.979 | 0.924 | -147 | 25/159 | 0.753 | 0.749 | 1570 |

## Standalone ranking (selection priority)

1. `A_only` → `tencent/hy3:free` (score=161.08)
2. `C_only` → `poolside/laguna-m.1:free` (score=138.74)
3. `B_only` → `nvidia/nemotron-3-ultra-550b-a55b:free` (score=108.52)

## Selected primary extractor

- **Role:** Extractor B (`A_only`)
- **Model ID:** `tencent/hy3:free`

### Selection evidence

- Highest combined score among standalone extractors under priority: exact/type agreement, procedure rejection, span policy proxies (lab split, sym/dx), assertion agreement.
- Exact-span recall vs frontier gold: **0.711**
- Overlap-span recall: **0.823**
- Type agreement on overlaps: **0.986**
- Procedure-as-test survival (lower better): **10/159**
- Unique exact entities supported: **1574**

Note: Unions raise recall but are not usable as a single primary extractor call. Largest model (Nemotron Ultra) is reserved primarily for judging unless it won standalone selection.

