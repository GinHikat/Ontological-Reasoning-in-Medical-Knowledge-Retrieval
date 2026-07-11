# v9 resume audit

Date: 2026-07-11 (updated)  
Host: `ict14` (80-thread Xeon Gold 6230, 125 GiB RAM; GPUs occupied)  
Branch: `tung` @ `79c0a8d` (+ dirty additive-pipeline / serve changes)

## Existing v9 files

### Code (complete / reused)
- `modules/pipelines/v9.py` — **`LLMAdditiveRecallPipeline`** (delegate `build_v7_structured_pipeline`, freeze finals, link/assert LLM-only, merge+sort)
- `modules/evaluation/run_pipeline.py` — writes `base_v7_snapshot/` beside `submission/` for v9
- `modules/components/postprocessing/llm_recall.py` — cache load helpers / overlap
- `modules/components/llm/` — client, schemas, document_lines, parser, aligner
- `modules/evaluation/generate_v9_llm_cache.py` — Phase A
- `modules/evaluation/analyze_v9_llm_recall.py`, `build_v9_pilot_report.py`, `enrich_v9_traces.py`
- `modules/pipelines/factory.py` — registers `v9_llm_recall`

### Prompts
- `prompts/v9_llm_recall_proposer_v1.txt`
- `prompts/v9_llm_recall_verifier_v1.txt`

### Scripts
- `scripts/serve_v9_qwen.sh` (GPU vLLM; OOM on 8GB Quadro)
- `scripts/serve_v9_qwen_cpu.py` (HF transformers CPU — ~0.05 tok/s, abandoned for cache gen)
- `scripts/serve_v9_qwen_llamacpp.py` / `.sh` (**active** CPU path)

### Analysis
- `analysis/v9_starting_state.txt` — NER path audit
- `analysis/v9_gpu_serve_failure.txt`
- `analysis/v9_pilot_cache_log.txt`
- `analysis/v9_llamacpp_server.log`

## Completed components

- Local OpenAI-compatible client (localhost only)
- Line index + exact aligner + JSON parser (one repair retry)
- Proposer/verifier prompts (types TRIỆU_CHỨNG / CHẨN_ĐOÁN / THUỐC)
- Cache schema + resume-safe skip unless `--force`
- **Post-freeze additive pipeline** (`LLMAdditiveRecallPipeline`)
- llama.cpp Q4_K_M local backend for same model id (~3.2 tok/s @ 40 threads)

## Incomplete components

- Pilot cache (in progress)
- Full 100-doc cache
- Phase B pipeline run, invariants, traces, packaging, reports

## Cache entries

| Path | Count | Notes |
|------|------:|-------|
| `cache/v9_llm_recall/*.json` | 0 usable at audit rewrite | regenerating |
| `_quarantine/` | 3 | HF-CPU timeout stubs (`proposer_failed` / empty raw) |
| Valid usable entries | **0** (pre-pilot regen) | do not reuse timeout stubs |

Pilot documents: `3,13,20,41,48,70,87,89,91,93,96,100` — none successfully cached yet.

## Model / backend configured

| Setting | Value |
|---------|-------|
| Model | `Qwen/Qwen3.5-9B` (unchanged id) |
| Active backend | llama.cpp CPU, GGUF `Qwen3.5-9B-Q4_K_M.gguf` |
| Endpoint | `http://127.0.0.1:8000/v1` |
| Threads | 40 (80 oversubscribed → 0.13 tok/s; 40 → ~3.2 tok/s) |
| Precision | Q4_K_M GGUF (local quant of same model) |
| Thinking | disabled (`enable_thinking=False` + `/no_think`) |
| Generation | temperature=0, top_p=1, max_tokens=1024 |
| HF BF16 weights | still on disk under `.../manual` (~19G) |

## NER checkpoint (Phase 1)

- Old path: `modules/model/statedict/ner/vihealthbert` — **missing**
- New path: `v_dataset/statedict/ner/vihealthbert` — **exists**
- `model.safetensors` SHA256: `dcf86eafb66506ad5dc89abac8b36f9809f77e61786055a756e0a8338460677d`
- Conclusion: path fix after `data→v_dataset` rename; **same intended weights**; keep as-is for v9

## Architecture vs brief

Implemented: newest v7 once → freeze FinalEntities → load cache → reject overlaps → link/assert **only** LLM additions → append → deterministic sort; persist `base_v7_snapshot/`.
