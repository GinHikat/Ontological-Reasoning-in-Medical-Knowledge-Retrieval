# OpenRouter model selection

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`

**Selection mode:** `profile:free_first`

## Extractors

| Role | Model ID | Family | Context | Structured outputs | Reason |
|------|----------|--------|--------:|--------------------|--------|
| extractor_A | `tencent/hy3:free` | tencent | 262144 | True | Profile-configured free_first / explicit IDs; validated via Models API. |
| extractor_B | `nvidia/nemotron-3-ultra-550b-a55b:free` | nvidia | 1000000 | None | Profile-configured free_first / explicit IDs; validated via Models API. |
| extractor_C | `poolside/laguna-m.1:free` | poolside | 262144 | None | Profile-configured free_first / explicit IDs; validated via Models API. |

## Judge

- **Model ID:** `tencent/hy3:free`
- **Family:** tencent
- **Context:** 262144
- **Structured outputs:** True
- **Reason:** Profile-configured judge; validated via Models API.

## Pricing metadata

### `tencent/hy3:free`
```json
{
  "prompt": "0",
  "completion": "0"
}
```

### `nvidia/nemotron-3-ultra-550b-a55b:free`
```json
{
  "prompt": "0",
  "completion": "0"
}
```

### `poolside/laguna-m.1:free`
```json
{
  "prompt": "0",
  "completion": "0"
}
```

### `tencent/hy3:free`
```json
{
  "prompt": "0",
  "completion": "0"
}
```
