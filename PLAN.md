# PLAN — active experiment: `v9_llm_recall`

Last updated: 2026-07-10

## Goal

```text
existing v7 output  +  new non-overlapping LLM-recalled entities
```

LLM is an **offline high-recall candidate generator only**. It must NOT emit competition JSON, ICD, RxNorm, offsets, or rewrite v7 entities.

## Hard constraints

| Must | Must not |
|------|----------|
| Model: `Qwen/Qwen3.5-9B` only (no silent model switch) | External APIs (OpenAI/Anthropic/Gemini/DashScope/…) |
| Self-hosted local endpoint (`127.0.0.1` / localhost / `::1`) | LLM offsets / start / end / positions |
| Two-phase: LLM cache → then NER/SapBERT pipeline | Replace/modify existing v7 entities/types/candidates/assertions |
| Exact substring alignment only (reject 0-match and multi-match) | Fuzzy / Levenshtein / accent-normalized alignment |
| Verifier accept only if proposer type == verifier type | Extract labs/tests/procedures/anatomy-alone/demographics in v9 |
| Additive non-overlap merge only | Build v9 on v8 pipelines |
| Same-env causal compare: fresh v7 vs fresh v9 | Investigate SapBERT nondeterminism |

Target LLM types only: `TRIỆU_CHỨNG`, `CHẨN_ĐOÁN`, `THUỐC`.

## Architecture

```text
Phase A: generate_v9_llm_cache.py  →  cache/v9_llm_recall/<doc_sha256>.json
         (Qwen alone; then unload)

Phase B: run_pipeline.py --pipeline v9_llm_recall
         (ViHealthBERT + SapBERT + ontology; reads cache only)
```

Pipeline order (v7 copy + insert):

```text
… ClinicalRecall → LLMRecall → CandidateMerge → PrecisionFilter → OverlapDedup → Linker → Assertions
```

## Phase checklist

- [x] P0 — hygiene + `analysis/v9_starting_state.txt` + NER checkpoint audit
- [x] P1–P5 — local LLM client (`modules/components/llm/`)
- [x] P6–P13 — line index, prompts, parser, aligner, verifier prompts
- [x] P14–P17 — cache generator, `LLMRecallPostProcessor`, `v9.py`, factory register, `.gitignore` cache/
- [ ] P18–P20 — pilot on files `3,13,20,41,48,70,87,89,91,93,96,100` → `analysis/v9_pilot_report.md`
- [ ] P21 — full 100-doc LLM cache; unload Qwen; same-env v7 then v9 runs
- [ ] P22–P25 — diagnostics TSVs/report + submission decision (`READY FOR MANUAL REVIEW` / `NOT READY`)
- [ ] P26 — 100 non-empty traces (+ enrich from cache)
- [ ] P27 — finalize `state.md` (no leaderboard score until submitted)

## Environments

| Role | Conda env | Notes |
|------|-----------|-------|
| Competition pipeline (NER/SapBERT) | `nanachi` | Use this for `run_pipeline.py` |
| vLLM / local Qwen server | `v9_vllm` | Separate; do not destroy `nanachi` |
| Broken/incomplete for sklearn | `tung` | Avoid for pipeline |

## Key paths

| Path | Purpose |
|------|---------|
| `modules/components/llm/` | client, schemas, document_lines, parser, aligner |
| `modules/components/postprocessing/llm_recall.py` | cache → additive mentions |
| `modules/pipelines/v9.py` | `build_v9_llm_recall_pipeline` |
| `modules/evaluation/generate_v9_llm_cache.py` | Phase A |
| `modules/evaluation/analyze_v9_llm_recall.py` | Phase 22+ |
| `modules/evaluation/build_v9_pilot_report.py` | Pilot report |
| `modules/evaluation/enrich_v9_traces.py` | Trace LLM detail |
| `prompts/v9_llm_recall_proposer_v1.txt` | Proposer prompt |
| `prompts/v9_llm_recall_verifier_v1.txt` | Verifier prompt |
| `cache/v9_llm_recall/` | SHA256-keyed cache (gitignored) |
| `scripts/serve_v9_qwen.sh` | GPU vLLM (preferred when VRAM free) |
| `scripts/serve_v9_qwen_cpu.py` | CPU fallback OpenAI-compatible server |
| `scripts/download_qwen35_9b_curl.sh` | Weight download to storage |

## Model weights

Local curl-downloaded weights (complete):

```text
/storage/student10/tungnl/cache/huggingface/hub/models--Qwen--Qwen3.5-9B/manual
```

Set:

```bash
export V9_MODEL=Qwen/Qwen3.5-9B
export V9_MODEL_PATH=/storage/student10/tungnl/cache/huggingface/hub/models--Qwen--Qwen3.5-9B/manual
export HF_HOME=/storage/student10/tungnl/cache/huggingface
```

## Hardware reality (this machine)

- GPUs: 2× Quadro RTX 4000 **8GB** — often occupied by other users.
- GPU vLLM BF16 **cannot** fit Qwen3.5-9B; exact failure logged in `analysis/v9_gpu_serve_failure.txt`.
- CPU fallback: same model id, localhost only; **very slow** (~15 s/token order-of-magnitude on smoke test).
- Prefer GPU when free; do not silently switch to another HF model name.

## NER checkpoint audit (do not re-litigate)

`inference_ner.py` path fix (committed in `a299cfc`) points at `v_dataset/statedict/ner/vihealthbert` after `data`→`v_dataset` rename. Same intended weights; old `modules/model/statedict/...` missing. SHA256 `model.safetensors`: `dcf86eafb66506ad5dc89abac8b36f9809f77e61786055a756e0a8338460677d`. Keep as-is for v9 (not a secret second NER experiment).

## v8 conclusions (preserve; do not submit)

- `v8_candidate_integrity`: negative/no-op ablation; not submitted
- `v8_candidate_rescue`: 0 newly rescued drugs; no-op; not submitted

## Decision gate (P25)

`NOT READY` if: any v7 entity removed/changed; invalid span; missing cache; 0 additions; unresolved parser failures.

Do not package Viettel ZIP until user reviews additions.
