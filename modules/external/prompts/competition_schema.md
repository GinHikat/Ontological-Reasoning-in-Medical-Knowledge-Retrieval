# Competition schema for openrouter_schema_teacher

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`. Outputs must not be used for competition
submission or for training a final competition model unless organizers explicitly
confirm that external-API-generated offline training data is allowed.

## Allowed output types

Extract **only** these five entity types:

| Type | Meaning |
|------|---------|
| `TRIỆU_CHỨNG` | Symptom or clinical sign |
| `TÊN_XÉT_NGHIỆM` | Laboratory test or diagnostic investigation **name** |
| `KẾT_QUẢ_XÉT_NGHIỆM` | Laboratory / investigation **result** (separate from name) |
| `CHẨN_ĐOÁN` | Disease, disorder, confirmed condition, diagnostic conclusion |
| `THUỐC` | Medication expression |

Everything else is omitted. There is **no** output type for:

- procedure / treatment intervention
- device
- anatomy alone
- patient demographics
- section headings
- generic clinical status

## TRIỆU_CHỨNG

Use a **minimal meaningful** symptom or clinical-sign phrase.

Do **not** include:

- leading negation
- temporal explanation
- treatment indication connector
- whole descriptive clause when a smaller phrase is sufficient

Example: source text `không đau ngực` becomes:

```json
{
  "text": "đau ngực",
  "type": "TRIỆU_CHỨNG",
  "assertions": ["isNegated"]
}
```

## CHẨN_ĐOÁN

Extract a disease, disorder, confirmed condition, or diagnostic conclusion.
Preserve meaningful diagnostic specificity. Distinguish diagnoses from symptoms.

## THUỐC

Use a **maximal contiguous** medication-expression span. Include when present:

- name, strength, dose, form, route, frequency, PRN

Do **not** include treatment-indication text.

## TÊN_XÉT_NGHIỆM

Extract a laboratory test or diagnostic investigation **name**.

Possible examples: `WBC`, `INR`, `creatinin`, `MRI`, `CT`, `X-quang`, `siêu âm`,
`điện tâm đồ`, `cấy máu`.

Do **not** output treatment procedures such as:

`đặt shunt`, `đặt stent`, `đặt catheter`, `phẫu thuật`, `dẫn lưu`, `truyền dịch`,
`truyền máu`, `tiêm`, `cắt bỏ`, `ghép`.

Some procedures (e.g. biopsy, puncture) may be diagnostically motivated. Reason from
context and omit them when they are primarily interventions rather than investigation
names.

## KẾT_QUẢ_XÉT_NGHIỆM

Extract the result **separately** from the test name. Prefer value, value+unit, or
qualitative finding.

Example: `kali là 6.6 mmol/l` becomes:

- `TÊN_XÉT_NGHIỆM`: `kali`
- `KẾT_QUẢ_XÉT_NGHIỆM`: `6.6 mmol/l`

## Assertions

Apply only to: `TRIỆU_CHỨNG`, `CHẨN_ĐOÁN`, `THUỐC`.

Allowed values: `isNegated`, `isFamily`, `isHistorical`.

Assertions are **entity-specific**. Do not mark every entity in a historical section
as historical.

## Offsets and anchors

- `text` must be an **exact contiguous substring** of the source document.
- `start` / `end` are character offsets into the original document (`document[start:end] == text`).
- Provide short `left_anchor` and `right_anchor` (nearby source context) to disambiguate
  repeated phrases.
- Do **not** normalize, correct spelling, translate, strip accents, or rewrite capitalization.

## Candidates / ontology IDs

Do **not** invent ICD-10 or RxNorm IDs at extraction time. Candidate IDs are assigned
in a later stage from a local retrieved list only.
