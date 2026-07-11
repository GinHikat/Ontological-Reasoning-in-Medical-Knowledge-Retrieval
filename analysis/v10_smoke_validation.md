# v10 smoke validation

Artifact: `output/v10_llm_conflict_resolution_smoke/`

## Counts

- base entities: 57
- v10 entities: 57
- replacements: 1
- pure additions: 0
- unpaired removals: 0

## Replacement

```text
atenololtrong [1849, 1862]
→
atenolol [1849, 1857]
```

- type: THUỐC
- candidates: ['1202']
- assertions: []
- original_document[1849:1857] == 'atenolol': **PASS**

## Trace

- Contains `V10 LLM CONFLICT RESOLUTION`: PASS
- `final_replacements: 1`: PASS

## Unrelated entities

- Preserved identically: **PASS**

## Decision

**SMOKE OK** — proceed to full 100-document run.
