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
