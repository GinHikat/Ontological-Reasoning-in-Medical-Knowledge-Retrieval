# Local RxNorm data inventory

Date: 2026-07-11

## Primary drug ontology

| Path | Role |
|------|------|
| `v_dataset/viettel/base/short_drug.csv` | Main RxNorm-derived dictionary used by the pipeline |
| `v_dataset/viettel/mapping/drug_rxnorm.csv` | Same content as `short_drug.csv` (duplicate mapping copy) |
| `v_dataset/viettel/base/short_drug.npy` | Embedding matrix companion (not used by probes) |

### `short_drug.csv`

- **Rows:** 310,332
- **Columns:** `term`, `rxcui`, `tty`, `ingredients`, `snomed`, `atc`, `drugbank`
- **ID loading:** string-safe (`dtype=str` / CSV text); never float-cast RxCUI
- **`ingredients` column:** free-text synonym / related-term lists, **not** structured parent RxCUI IDs

### TTY counts (raw `tty` field; multi-tags joined with `\|`)

| TTY (raw) | Rows |
|-----------|-----:|
| SY | 48,228 |
| SCD | 27,284 |
| SCDC | 26,547 |
| SBD | 20,083 |
| SBDG | 20,024 |
| SBDC | 16,355 |
| PSN | 15,745 |
| SCDG | 14,706 |
| IN | 14,455 |
| SY\|PSN | 13,868 |
| … | … |
| PIN | 3,441 |
| BN | 11,762 |

Probe logic treats a row as having a TTY if that token appears in `tty.split("|")` (so `SCD|PSN` counts as SCD).

### Official example concepts present locally

| Concept | RxCUI | Local TTY | Term |
|---------|------:|-----------|------|
| nystatin (ingredient) | 7597 | IN | nystatin |
| acetaminophen (ingredient) | 161 | IN | acetaminophen |
| acetaminophen 325 MG Oral Tablet | 313782 | SCD\|PSN | acetaminophen 325 mg oral tablet |

## Relationship / hierarchy files

| Asset | Present? |
|-------|----------|
| RXNREL / RRF | **No** |
| Explicit concept→ingredient parent table | **No** |
| Structured parent-child RxNorm graph | **No** |

**Conclusion:** probes use a **conservative lexical ingredient resolver** (mention aliases + baseline candidate term decomposition). No RxNav / external API.

## Other drug-related paths (not used as relationship graph)

- `modules/dataset/dataset_processing/process_rxnorm.py` — processing script only
- Pipeline loaders in `modules/components/postprocessing/ontology_drug_recall.py`
