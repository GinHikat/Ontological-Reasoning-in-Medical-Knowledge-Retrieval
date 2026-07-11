# WORKLOG — append-only session log

> Growing file. **Do not** open/read the whole thing. Latest state is at the **bottom**.

## Agent I/O (mandatory)

**Read** (last ~80 lines — enough for recent Status / Next):

```bash
tail -n 80 WORKLOG.md
```

If the last entry is truncated mid-block, bump the window (`tail -n 120`). Do **not** use the Read tool on this file unless debugging corruption.

**Append** after every meaningful step (never rewrite earlier entries):

```bash
HOST=$(hostname)
TS=$(date '+%Y-%m-%d %H:%M %z')
cat >> WORKLOG.md <<EOF

---
### ${TS} | host=${HOST}
**Status:** one-line experiment state
**Next:** concrete next action(s)
- what you did
- paths / hashes / outcomes worth keeping
EOF
```

Rules:
- Chronological append only; edit history only to fix a bad last entry you just wrote.
- Put **Status** + **Next** in every entry so `tail` alone is enough to resume.
- Keep each entry short; dump long tables/logs under `analysis/` and link the path.
- Heredoc must be unquoted (`<<EOF`) if you want `${TS}` / `${HOST}` expanded; or paste values literally with `<<'EOF'`.

Pinned facts that rarely change (baseline hash, probe SHA256s) may be repeated briefly in Status or linked to `analysis/`.

---

### 2026-07-11 02:13 +07 | host=ictserver6
**Status:** rxnorm_policy_probes COMPLETE — awaiting manual submit; baseline = newest v7 same_env; v9 untouched; CURRENT_MACHINE.md has ict14 + ictserver6
**Next:** (1) user submits ZIPs per `analysis/rxnorm_probe_submission_order.md` (2) fill `analysis/rxnorm_probe_leaderboard_results.md` (3) resume v9 only after scores or user redirect
- Baseline: `output/v7_structured/same_env/submission` → frozen `artifacts/v7_newest_same_env/submission`
- Semantic hash: `71593faca03ed5339b805b96c381c9e4864693112cccddf3bc14461719653a60` (3236 ents, 271 drugs, 270/271 linked)
- Probes: example_policy / ingredient_first / baseline_plus_ingredient under `output/rxnorm_probe_*.zip` (see analysis docs for SHA256)
- Unit tests: nystatin→7597 PASS; acetaminophen→313782 PASS
- Do not: rerun models/Qwen/v9 for this task; auto-submit; auto-commit

---
### 2026-07-11 02:17 +07 | host=ictserver6
**Status:** same probes awaiting submit; dual-host machine notes written
**Next:** same as prior entry (manual ZIP submit → scores)
- Rewrote `CURRENT_MACHINE.md` for shared `/storage`: active `ictserver6` (8×K80, use `nanachi_ictserver6`) + prior `ict14` (2×Quadro, `nanachi` / `v9_vllm`)
- Switched WORKLOG to append-only + `tail` read convention (this format)

---
### 2026-07-11 02:32 +0700 | host=ictserver6
**Status:** v9_llm_recall resumed on ictserver6; additive freeze pipeline implemented; CPU Qwen server UP; pilot cache regenerating
**Next:** wait smoke LLM latency → run pilot 12-doc cache (long timeout) → pilot report/quality gate → full 100 cache → Phase B on nanachi_ictserver6 GPU for NER
- Wrote analysis/v9_resume_audit.md
- Quarantined 2 timeout cache stubs → cache/v9_llm_recall/_quarantine/
- Implemented LLMAdditiveRecallPipeline (delegate build_v7_structured_pipeline; freeze; link/assert LLM-only; base_v7_snapshot in run_pipeline)
- GPU for Qwen: NOT viable here (K80 + driver 440); NER Phase B can use nanachi_ictserver6
- CPU server: nanachi + serve_v9_qwen_cpu.py on :8000, model Qwen/Qwen3.5-9B, thinking off
- Recorded official RxNorm probe scores in state.md; no more RxNorm probes

---
### 2026-07-11 02:40 +0700 | host=ict14
**Status:** CURRENT_WORK.md convention added; pilot cache still RUNNING on ict14 (CPU timeouts)
**Next:** user can `continue from CURRENT_WORK.md`; wait/fix pilot timeouts (raise timeout or faster Qwen) before pilot report
- Created CURRENT_WORK.md (rewriteable long-run handoff + tmux commands)
- Wired into AGENTS.md + .cursor/rules/v9-resume.mdc
- Live: serve_v9_qwen_cpu.py + generate_v9_llm_cache pilot 12 docs; doc20 = proposer_failed timeout; usable accepted=0

---
### 2026-07-11 02:47 +0700 | host=ict14
**Status:** P20 pilot aborted — CPU Qwen timed out (3600s) on docs 3/13/20; 0 valid cache entries
**Next:** Unblock serving (GPU+quant when free, or much smaller max_tokens / chunked prompts); then re-run pilot without --force
- Pilot job 647176 aborted after ~3h; tqdm showed 3/12 at exactly 3600s/doc
- Quarantined timeout stubs: cache/v9_llm_recall/_quarantine/ (docs 3,13,20; raw_len=0; proposer_failed)
- Valid cache/*.json count: 0
- CPU server still on :8000 (pid ~213051); GPUs still ~full (764/604 MiB free)
- Server never finished generate for long prompts (prompt_tokens~1.6k–2.8k, max_new=1536)

---
### 2026-07-11 03:09 +0700 | host=ict14
**Status:** Qwen CPU server task aborted; check :8000 before any cache gen
**Next:** if resuming v9 on this host, restart serve_v9_qwen_cpu.py then pilot without --force
- Terminal 647174 aborted; verify with `ss -ltnp | grep 8000`

---
### 2026-07-11 03:21 +0700 | host=ict14
**Status:** v9 pilot cache RUNNING on ict14 via llama.cpp Q4 (~3.2 tok/s); HF CPU abandoned
**Next:** wait pilot 12-doc cache → build_v9_pilot_report → quality gate → full 100 cache → Phase B
- Quarantined 3 HF-timeout stubs under cache/v9_llm_recall/_quarantine/
- Added scripts/serve_v9_qwen_llamacpp.py (model id still Qwen/Qwen3.5-9B; GGUF Q4_K_M; 40 threads)
- Smoke: 177 toks / 55.5s; JSON entity extraction OK
- GEN_PID generate_v9_llm_cache pilot --timeout 1800 --max-tokens 1024 (no --force)
- LLMAdditiveRecallPipeline already in modules/pipelines/v9.py; NER path fix = same weights

---
### 2026-07-11 03:47 +0700 | host=ict14
**Status:** pilot cache progressing — doc 3 OK (39 parsed / 38 accepted) via llama.cpp Q4 @ ~3.7 tok/s
**Next:** finish 12-doc pilot → pilot report/quality gate → full 100 cache
- max_tokens raised to 2048 after doc3 JSON truncation at 1024
- prompt: compact JSON + explicit untrusted-doc injection resistance
- generate_v9_llm_cache preserves raw on repair failure
- GEN 381077; serve 380024 (n_threads=40, n_ctx=16384)

---
### 2026-07-11 05:04 +0700 | host=ict14
**Status:** pilot DONE (12/12, 200 accepted); full 100-doc cache RUNNING (resume-safe)
**Next:** wait 100 valid cache → unload Qwen → Phase B run_pipeline v9_llm_recall → diagnostics
- Pilot funnel: raw 243 / aligned 225 / accepted 200 (TC 109, CD 66, TH 25)
- Quality gate PASS with caveats (long imaging phrases, some English tokens, generic drug phrases)
- Report: analysis/v9_pilot_report.md
- Full gen PID ~446964; serve ~380024

---
### 2026-07-11 07:11 +0700 | host=ict14
**Status:** full cache STOPPED at ~37/100 — server RemoteDisconnected; port 8000 down; gen exited
**Next:** user resumes in tmux — pane A serve_v9_qwen_llamacpp (40 thr, n_ctx=16384); pane B generate_v9_llm_cache --timeout 1800 --max-tokens 2048 (no --force)
- Commands in CURRENT_WORK.md
- Do not --force; skips existing SHA256 cache keys

---
### 2026-07-11 08:06 +0700 | host=ict14
**Status:** mid-run audit on ~46/100 cache while gen continues; additive yield looks tiny
**Next:** wait full 100 cache → salvage doc16 verifier → Phase B → full overlap audit
- Wrote analysis/v9_midrun_cache_audit.md (+ stats json): 604 accepted but only ~19 non-overlap vs v7 same_env
- Doc16 truncated JSON salvage: 48 proposals / 47 aligned (analysis/v9_doc16_salvage_record.json); verifier deferred
- Added truncated-entities salvage in response_parser.py + salvage_v9_failed_cache.py
- Did not touch live llama.cpp server (gen still RUNNING)

---
### 2026-07-11 08:58 +0700 | host=ict14
**Status:** GGUF precision bakeoff Q4 vs Q8 DONE (BF16 still downloading); live cache untouched
**Next:** finish BF16 download → append BF16 row to analysis/v9_gguf_precision_bench.md; keep waiting full 100 cache
- Q4_K_M: 2.25 tok/s @ 8 thr (under contention with live 40-thr cache)
- Q8_0: 1.53 tok/s @ 8 thr — **slower than Q4**, not faster
- Script: scripts/bench_v9_gguf_precision.py; report analysis/v9_gguf_precision_bench.md
- Live :8000 still Q4; do not switch mid-cache

---
### 2026-07-11 09:43 +0700 | host=ict14
**Status:** GGUF bakeoff complete Q4 vs Q8 vs BF16; Q4 fastest; live cache still on Q4
**Next:** wait full 100 cache → salvage doc16 → Phase B
- See analysis/v9_gguf_precision_bench.md

---
### 2026-07-11 09:43 +0700 | host=ict14
**Status:** session handoff — full cache RUNNING ~64/100; bakeoff+mid-run audit preserved in CURRENT_WORK.md
**Next:** wait 100 cache (or resume via CURRENT_WORK.md if PIDs die) → salvage doc16 → unload Qwen → Phase B → diagnostics/decision
- CURRENT_WORK.md rewritten (PIDs serve 541794 / gen 542957; no tmux — prefer tmux if restarting)
- Key findings kept: additive ~3% vs v7 same_env; Q4 fastest on CPU; doc16 salvage ready
- Do not --force; do not switch quant mid-run

---
### 2026-07-11 14:14 +0700 | host=ict14
**Status:** Phase A DONE (100 cache + doc16 salvage); Phase B RUNNING on CPU (GPUs full)
**Next:** wait Phase B → analyze_v9_llm_recall + enrich traces → decision → state.md
- Cache: 100/100; doc16 salvaged → 30 accepted (completed_with_parse_issues)
- Qwen server stopped
- Phase B: CUDA_VISIBLE_DEVICES= empty; log analysis/v9_phase_b_log.txt; out output/v9_llm_recall/

---
### 2026-07-11 14:21 +0700 | host=ict14
**Status:** Phase B RUNNING on CPU — layout fixed; ~1/100 done (~7 min/doc → ~12h ETA)
**Next:** wait 100/100 Phase B → analyze + enrich → decision → state.md
- Fixed run_pipeline --output-dir to nest submission/base_v7_snapshot/trace under output/v9_llm_recall/
- CUDA_VISIBLE_DEVICES= (GPUs full); log analysis/v9_phase_b_log.txt

---
### 2026-07-11 15:58 +0700 | host=ict14
**Status:** v9_llm_recall Phase B + diagnostics DONE — decision READY FOR MANUAL REVIEW
**Next:** user manual review of 34 additions; package ZIP only if user asks; no auto-submit
- Phase B 100/100 (~1h42m CPU); submission + base_v7_snapshot + enriched traces
- Invariants all 0; final additions 34 (CD14/TC12/TH8); all CD/TH linked
- Reports: analysis/v9_llm_recall_report.md, analysis/v9_manual_review.md, TSVs
- state.md + CURRENT_WORK.md updated

---
### 2026-07-11 16:45 +0700 | host=ict14
**Status:** v9_llm_recall official leaderboard SCORED — NEGATIVE vs v7
**Next:** keep v7_structured (24.79660) as baseline; await user direction on next experiment
- Commit: baa37fe4235e8ec12e3955d4ece44ad198854344 (baa37fe)
- Submitted: 2026-07-11 16:42 +0700; ZIP 93 KB SHA prefix 6b74e773a0ec…
- Score 23.84290 / WER 72.7861 / J_assertion 29.7128 / J_candidates 16.9122 / num_scored 100 / num_records 100
- Delta vs v7 24.79660: Score −0.95370 / WER +0.7822 / J_assertion −1.6544 / J_candidates −0.5569
- Logged in state.md + CURRENT_WORK.md

---
### 2026-07-11 16:59 +0700 | host=ict14
**Status:** v9 closed NEGATIVE; v10_llm_conflict_resolution implemented + smoke OK
**Next:** full 100-doc Phase B when ready (GPU preferred; CPU OK); then manual review of replacements
- v9 leaderboard 23.84290 vs v7 24.79660 (−0.95370) — no more additive v9 submissions
- Pivot: LLM as constrained span/type conflict resolver (reuse cache/v9_llm_recall)
- New: llm_conflict_resolution.py (A/B/C/D), pipelines/v10.py, factory register, analyze_v10_llm_conflict.py
- Offline preview: 40 candidates (A7 B3 C18 D12); exact-span type-only D disabled
- Smoke: output_smoke/v10_llm_conflict_resolution/ (1 doc, CPU ~2m42s) — atenololtrong→atenolol accepted
- PLAN.md rewritten for v10; state.md v9 conclusion updated with pivot

---
### 2026-07-11 17:03 +0700 | host=ict14
**Status:** hygiene — moved smoke out of repo root
**Next:** full Phase B still pending (see CURRENT_WORK.md)
- Removed root `output_smoke/`; smoke now at `output/v10_llm_conflict_resolution_smoke/`

---
### 2026-07-11 17:05 +0700 | host=ict14
**Status:** v10 Phase B STARTED (100 docs, CPU)
**Next:** wait for output/v10_llm_conflict_resolution 100/100 → validation + annotation packet
- Smoke validated: analysis/v10_smoke_validation.md (PASS)
- Starting state: analysis/v10_full_run_starting_state.md
- Log: analysis/v10_phase_b_log.txt
- Note: v10 code still uncommitted on branch tung (HEAD baa37fe)

---
### 2026-07-11 17:14 +0700 | host=ict14
**Status:** v10 Phase B restarted PARALLEL (10 workers × 6 threads)
**Next:** wait 100/100 under output/v10_llm_conflict_resolution/ then finalize_v10_llm_conflict.py
- Killed sequential PID 906235 (~6/100); wiped partial outputs for clean same-run compare
- Extended run_pipeline_parallel.py: --output-dir + base_v7_snapshot for v9/v10
- Parent PID 913811; log analysis/v10_phase_b_log.txt

---
### 2026-07-11 18:58 +0700 | host=ict14
**Status:** v10 Phase B DONE — 100/100 parallel CPU (~1h13m); errors=0
**Next:** run finalize_v10_llm_conflict.py → manual review / decision (no auto-submit)
- Log end: newly_written=100 skipped=0 errors=0; submission+trace+base_v7 all 100
- Output: output/v10_llm_conflict_resolution/
- CURRENT_WORK.md → DONE

---
### 2026-07-11 19:02 +0700 | host=ict14
**Status:** v10 finalize DONE — READY FOR MANUAL REVIEW (39 replacements; hard gates all 0)
**Next:** human review of analysis/v10_annotation_review.md; submit only if user decides
- A6 B3 C18 D12; competition ZIP output/v10_llm_conflict_resolution_submission.zip sha256 05cb2caf…
- Diagnostic ZIP output/v10_llm_conflict_resolution_full.zip; report analysis/v10_llm_conflict_report.md
- CURRENT_WORK.md → IDLE / READY FOR MANUAL REVIEW
