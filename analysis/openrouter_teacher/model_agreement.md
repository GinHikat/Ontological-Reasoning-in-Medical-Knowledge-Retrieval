# Model agreement

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`

## Document 24

- `openai_gpt-5.5`: 4 aligned proposals
- `anthropic_claude-opus-4.8`: 23 aligned proposals
- `google_gemini-3.1-pro-preview`: 3 aligned proposals
- pairwise `openai_gpt-5.5` vs `anthropic_claude-opus-4.8`: exact=0, overlap_same_type≈4
- pairwise `openai_gpt-5.5` vs `google_gemini-3.1-pro-preview`: exact=3, overlap_same_type≈3
- pairwise `anthropic_claude-opus-4.8` vs `google_gemini-3.1-pro-preview`: exact=0, overlap_same_type≈2

- judge-accepted exact spans from `openai_gpt-5.5`: 4/22 gold
- judge-accepted exact spans from `anthropic_claude-opus-4.8`: 0/22 gold
- judge-accepted exact spans from `google_gemini-3.1-pro-preview`: 3/22 gold

## Notes

- Gemini and GPT under-extracted on doc 24 relative to Opus; judge leaned on denser proposals.
- Full pairwise corpus stats require completing the 100-doc run (blocked by OpenRouter key credit limit).
