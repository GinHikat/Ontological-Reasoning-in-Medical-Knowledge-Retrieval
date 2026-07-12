# OpenRouter model selection

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`

**Selection mode:** `explicit_env`

## Extractors

| Role | Model ID | Family | Context | Structured outputs | Reason |
|------|----------|--------|--------:|--------------------|--------|
| extractor_A | `anthropic/claude-opus-4.8` | anthropic | 1000000 | True | Explicitly configured via OPENROUTER_EXTRACTOR_MODELS; validated against Models API. |
| extractor_B | `google/gemini-3.1-pro-preview` | google | 1048576 | True | Explicitly configured via OPENROUTER_EXTRACTOR_MODELS; validated against Models API. |
| extractor_C | `openai/gpt-5.5` | openai | 1050000 | True | Explicitly configured via OPENROUTER_EXTRACTOR_MODELS; validated against Models API. |

## Judge

- **Model ID:** `anthropic/claude-opus-4.8`
- **Family:** anthropic
- **Context:** 1000000
- **Structured outputs:** True
- **Reason:** Explicitly configured via OPENROUTER_JUDGE_MODEL; validated against Models API.

## Pricing metadata

### `anthropic/claude-opus-4.8`
```json
{
  "prompt": "0.000005",
  "completion": "0.000025",
  "web_search": "0.01",
  "input_cache_read": "0.0000005",
  "input_cache_write": "0.00000625",
  "input_cache_write_1h": "0.00001"
}
```

### `google/gemini-3.1-pro-preview`
```json
{
  "prompt": "0.000002",
  "completion": "0.000012",
  "image": "0.000002",
  "audio": "0.000002",
  "web_search": "0.014",
  "internal_reasoning": "0.000012",
  "input_cache_read": "0.0000002",
  "input_cache_write": "0.000000375"
}
```

### `openai/gpt-5.5`
```json
{
  "prompt": "0.000005",
  "completion": "0.00003",
  "web_search": "0.01",
  "input_cache_read": "0.0000005"
}
```

### `anthropic/claude-opus-4.8`
```json
{
  "prompt": "0.000005",
  "completion": "0.000025",
  "web_search": "0.01",
  "input_cache_read": "0.0000005",
  "input_cache_write": "0.00000625",
  "input_cache_write_1h": "0.00001"
}
```
