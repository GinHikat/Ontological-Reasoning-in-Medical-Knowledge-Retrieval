# v9 resume audit

Date: 2026-07-11  
Host: `ictserver6` (8× Tesla K80, driver 440 / CUDA 10.2)  
Branch: `tung` @ `79c0a8d`

## Existing v9 files

### Code (complete)
- `modules/pipelines/v9.py` — mid-pipeline LLM insert (pre-refactor)
- `modules/components/postprocessing/llm_recall.py` — cache → additive mentions
- `modules/components/llm/` — client, schemas, document_lines, parser, aligner
- `modules/evaluation/generate_v9_llm_cache.py` — Phase A cache generator
- `modules/evaluation/analyze_v9_llm_recall.py` — diagnostics / gate
- `modules/evaluation/build_v9_pilot_report.py`
- `modules/evaluation/enrich_v9_traces.py`
- `modules/pipelines/factory.py` — registers `v9_llm_recall`

### Prompts
- `prompts/v9_llm_recall_proposer_v1.txt`
- `prompts/v9_llm_recall_verifier_v1.txt`

### Scripts
- `scripts/serve_v9_qwen.sh` (GPU vLLM)
- `scripts/serve_v9_qwen_cpu.py` / `.sh` (CPU fallback)
- `scripts/setup_v9_vllm_env.sh`, `scripts/download_qwen35_9b_curl.sh`

### Analysis
- `analysis/v9_starting_state.txt` — NER path audit
- `analysis/v9_gpu_serve_failure.txt` — Quadro 8GB OOM on ict14
- `analysis/v9_pilot_cache_log.txt` — pilot stalled 2/12

### Missing (not yet generated)
- `analysis/v9_pilot_report.md`, `analysis/v9_llm_recall_report.md`, TSVs, manual review
- `output/v9_*`

## Completed components

- Local OpenAI-compatible client (localhost only)
- Line index + exact aligner + JSON parser (one repair retry)
- Proposer/verifier prompts (injection resistance, types TRIỆU_CHỨNG/CHẨN_ĐOÁN/THUỐC)
- Cache schema + resume-safe skip unless `--force`
- Mid-pipeline `LLMRecallPostProcessor` (non-overlap add)
- Analysis/report scripts (unrun)

## Incomplete components

- **Pilot cache** (2/12, both timeouts — no accepted candidates)
- **Full 100-doc cache**
- **Literal freeze-v7-then-append wrapper** (`LLMAdditiveRecallPipeline`) — required by current brief; mid-pipeline insert can still mutate v7 via merge/dedup/linker
- Phase B pipeline run, invariants, traces, packaging
- `v9_vllm` conda env **absent on ictserver6**

## Cache entries

| Path | Count | Notes |
|------|------:|-------|
| `cache/v9_llm_recall/*.json` | 2 | Both `proposer_failed` / Timed out after 3600s |
| Valid usable entries | **0** | `final_accepted_candidates: []` |
| Invalid/stale | **2** | Timeout stubs — quarantine + regenerate (do not keep as “done”) |

Pilot docs already attempted: `3`, `13` (failed).  
Pilot set remaining: `20,41,48,70,87,89,91,93,96,100` (+ regenerate 3,13).

## Model / backend configured

| Setting | Value |
|---------|-------|
| Model | `Qwen/Qwen3.5-9B` (weights under `/storage/.../manual`, ~19G) |
| Preferred backend | local OpenAI-compatible `http://127.0.0.1:8000/v1` |
| Generation defaults | temperature=0, top_p=1, enable_thinking=False, max_tokens=4096 |
| ict14 GPU vLLM | Failed (8GB Quadro; see `v9_gpu_serve_failure.txt`) |
| ictserver6 GPU | **Cannot run Qwen3.5** — driver 440 / CUDA 10.2; `nanachi` torch 2.6 sees no CUDA; K80 unsupported by modern vLLM |
| ictserver6 LLM path | **CPU** via `nanachi` + `serve_v9_qwen_cpu.py` |
| ictserver6 NER GPU | `nanachi_ictserver6` (torch 1.12.1+cu102) for Phase B only |

## Architecture gap vs brief

Current: v7 stack copy + LLM insert before merge (LLM mentions share linker/dedup with v7).  
Required: run newest v7 once → **freeze** FinalEntities → link/assert **only** LLM additions → append → sort; persist `base_v7_snapshot/`.

## NER checkpoint (Phase 1)

See `analysis/v9_starting_state.txt` + re-verify 2026-07-11:

- Old path: `modules/model/statedict/ner/vihealthbert` — **missing**
- New path: `v_dataset/statedict/ner/vihealthbert` — **exists**
- `model.safetensors` SHA256: `dcf86eafb66506ad5dc89abac8b36f9809f77e61786055a756e0a8338460677d`
- Conclusion: path fix after `data→v_dataset` rename; **same intended weights**; keep as-is for v9

## Resume plan

1. Implement `LLMAdditiveRecallPipeline` (delegate `build_v7_structured_pipeline`)
2. Quarantine 2 timeout cache stubs
3. Start CPU Qwen server; regenerate pilot → quality gate
4. Full 100-doc cache (resume-safe)
5. Phase B on GPU NER env if possible; diagnostics + decision
