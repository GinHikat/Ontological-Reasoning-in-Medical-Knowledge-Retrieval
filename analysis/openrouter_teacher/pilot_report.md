# Pilot report — openrouter_schema_teacher

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`

## Selected files

Auto-selected from schema audit (invalid ids filtered in later fix):

`['24', '3', '*', '37', '78']`

Curated audit-derived reference set (for resume): `75, 36, 20, 37, 51`

Completed gold in this pilot: `['24']`

## Models used

| Role | Model |
|------|-------|
| Extractor A | `anthropic/claude-opus-4.8` |
| Extractor B | `google/gemini-3.1-pro-preview` |
| Extractor C | `openai/gpt-5.5` |
| Judge | `anthropic/claude-opus-4.8` |

## Requests / tokens / cost (pilot process usage)

| Metric | Value |
|--------|------:|
| Requests | 12 |
| Input tokens | 46948 |
| Output tokens | 54819 |
| Estimated cost (process) | $1.461559 |
| Budget limit (capped by key remaining) | $1.3827399999999999 |
| Parse OK rate | 0.9166666666666666 |

Ledger unique request hashes: 26; ledger uncached cost sum ≈ $3.0081

## Gates

```json
{
  "budget_set": true,
  "valid_final": 1,
  "pilot_n": 5,
  "parse_ok_rate": 0.9230769230769231,
  "pilot_ok": false,
  "continue_full": false
}
```

**Gate result:** pilot did **not** unlock full 100-doc run.

Reasons:
1. Only 1/5 pilot files produced valid final JSON
2. OpenRouter **key limit remaining hit $0** (key limit=$3; account still has unused total credits but this key cannot spend more)
3. Parse OK rate 0.923 (threshold 0.95) — borderline / below after failures

## Doc 24 snapshot (only completed pilot gold)

- Teacher entities: 22
- Type dist: {'CHẨN_ĐOÁN': 2, 'TRIỆU_CHỨNG': 17, 'THUỐC': 3}
- Critic issues: 6
- Schema-audit procedure-as-test on file 24: **7/7 rejected** (none remain as TÊN_XÉT_NGHIỆM)

## Alignment / candidate failures

See `output/openrouter_schema_teacher/logs/*_error.json` for budget stops.
Ontology candidate selection ran for completed docs; invented IDs are stripped by local allow-list.

## Resume requirements

Raise OpenRouter key spending limit (or add credits to this key) then:

```bash
tmux new -s openrouter_teacher
python -m modules.evaluation.run_openrouter_schema_teacher --docs 75 36 20 37 51 --full
# or after pilot gates pass:
python -m modules.evaluation.run_openrouter_schema_teacher --full
```
