# Official annotation schema (encoded for audit)

Source: competition task description (`docs/tung/competition_brief.md` §3.2–3.3).
These are **official rules** unless marked as **hypotheses**.

---

## Allowed types

```text
TRIỆU_CHỨNG
TÊN_XÉT_NGHIỆM
KẾT_QUẢ_XÉT_NGHIỆM
CHẨN_ĐOÁN
THUỐC
```

There is **no** output class for:

```text
procedure
treatment intervention
device
anatomy alone
patient demographic information
generic clinical status
```

---

## Candidate mappings

| Type | Candidates |
|------|------------|
| `CHẨN_ĐOÁN` | ICD-10 candidate **list** |
| `THUỐC` | RxNorm candidate **list** |
| `TRIỆU_CHỨNG` | none |
| `TÊN_XÉT_NGHIỆM` | none |
| `KẾT_QUẢ_XÉT_NGHIỆM` | none |

---

## Assertions

Assertions apply **only** to:

```text
TRIỆU_CHỨNG
CHẨN_ĐOÁN
THUỐC
```

Possible values (list, ≤3):

```text
isNegated
isFamily
isHistorical
```

Official cue examples:

| Assertion | Example |
|-----------|---------|
| `isNegated` | *"không ho"* |
| `isFamily` | *"bố bệnh nhân xuất hiện trường hợp đau bụng tương tự"* |
| `isHistorical` | *"có tiền sử hen suyễn"* |

---

## Span-style hypotheses (from official examples)

Recorded as **hypotheses to audit**, not proven universal rules:

### THUỐC — maximal medication expression

Include name + strength + route + frequency + PRN when present.

Official example spans:

- `Chlorpheniramine 0.4 MG/ML`
- `Capsaicin 0.38 MG/ML`

### TRIỆU_CHỨNG — minimal clinical complaint or sign phrase

Official example spans:

- `ho đờm xanh`
- `tức ngực`
- `đau thượng vị`
- `ợ hơi`

### CHẨN_ĐOÁN — disease phrase with clinically meaningful specificity

Official example:

- `bệnh trào ngược dạ dày - thực quản`

### TÊN_XÉT_NGHIỆM — test or investigation name; not treatment procedure

Official example spans:

- `TWBC`
- `NEUT% (Tỷ lệ % bạch cầu trung tính)`
- `LYPH% (Tỷ lệ bạch cầu lympho)`

### KẾT_QUẢ_XÉT_NGHIỆM — result value (+ unit when available); separate from test name

Official example spans:

- `14,43`
- `76,4`
- `12,8`

Hypothesis: for text like `kali là 6.6 mmol/l`, preferred segmentation is:

```text
TÊN_XÉT_NGHIỆM = kali
KẾT_QUẢ_XÉT_NGHIỆM = 6.6 mmol/l
```

---

## Diagnosis candidate-set observation

The official example maps **one** diagnosis to:

```text
["K21.0", "K21.9"]
```

Therefore, `CHẨN_ĐOÁN` candidate output **may be multi-label**.

Do **not** assume one ICD code per diagnosis.

---

## Medication + assertion scope hypothesis (official example)

Pre-admission drugs carry `isHistorical`.

Symptom indications that appear inside the same medication-list context (e.g. indication phrases such as `ho`, `táo bón`, `lo âu`, `mất ngủ`) **may remain without** `isHistorical` even when they co-occur with historical medications.

---

## Evaluation implication (for audit interpretation)

Wrong-type predictions may be penalized as both a false positive and a false negative (type collision / WER). Over-extraction of non-schema classes (procedures, generic status) likely inflates WER without helping assertion/candidate Jaccard.
