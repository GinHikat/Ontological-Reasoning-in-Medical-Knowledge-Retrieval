# v9 GGUF precision bakeoff (llama.cpp CPU)

Same prompt / same `n_threads` / same `max_tokens`. Separate from live `:8000` cache job.

- threads: 8
- n_ctx: 4096
- max_tokens: 256

| Quant | Size | Load s | Gen s | Completion toks | tok/s | preview |
|-------|-----:|-------:|------:|----------------:|------:|---------|
| Q4_K_M | 5.3G | 6.32 | 62.28 | 140 | **2.248** | `[{"entity": "Đau ngực", "type": "TRIỆU_CHỨNG"}, {"entity": "khó thở", "type": "T` |
| Q8_0 | 8.9G | 92.83 | 137.82 | 211 | **1.531** | `[\n  {\n    "entity": "Đau ngực",\n    "type": "TRIỆU_CHỨNG"\n  },\n  {\n    "en` |
| BF16 | 16.7G | 109.3 | 221.26 | 211 | **0.954** | `[\n  {\n    "entity": "Đau ngực",\n    "type": "TRIỆU_CHỨNG"\n  },\n  {\n    "en` |

## Conclusion

- On this CPU host with llama.cpp, **higher precision is slower**, not faster.
- Q4_K_M ≫ Q8_0 ≫ BF16 for tok/s (memory-bandwidth bound).
- Live v9 cache correctly stays on Q4_K_M.

## Notes

- Live full-cache server keeps using local Q4_K_M on `:8000` (unchanged).
- Q8/BF16 from `unsloth/Qwen3.5-9B-GGUF` (same model family; speed test).
- Absolute tok/s under contention with the 40-thread live cache; ratios are the point.
