# WORKLOG — live session state

> **Agents: read this first, then `PLAN.md`.** Update this file after every meaningful step.

Last updated: 2026-07-11 00:45 +07

## Status

```text
ACTIVE EXPERIMENT: rxnorm_policy_probes (COMPLETE — awaiting manual submit)
BASELINE: newest v7 same_env (NOT the missing 24.79660 ZIP)
PARALLEL: v9_llm_recall left untouched
DECISION: user submits ZIPs manually; fill scores in analysis/rxnorm_probe_leaderboard_results.md
```

## Next action

1. User manually submits ZIPs in order (see `analysis/rxnorm_probe_submission_order.md`).
2. After scores: fill `analysis/rxnorm_probe_leaderboard_results.md` and decide Outcome A–E.
3. Resume v9 only after probe scores are in (or if user redirects).

## Baseline used

```text
source: output/v7_structured/same_env/submission
frozen: artifacts/v7_newest_same_env/submission
semantic hash: 71593faca03ed5339b805b96c381c9e4864693112cccddf3bc14461719653a60
entities: 3236 | drugs: 271 | linked drugs: 270/271
```

Note: scored 24.79660 artifact still missing on disk; user authorized newest v7 as reference.

## Probe ZIPs (validated)

| Probe | Changed | Signal | SHA256 |
|-------|--------:|--------|--------|
| example_policy | 18 | LOW | `19b881fdcfa18c30f028e8f54db107d59d0868d403fac4c4e400d1a9f3309ddb` |
| ingredient_first | 23 | MODERATE | `880050861f2bd227b405fc74d9bee2cad51c9690c9555079d0c77ca37188684d` |
| baseline_plus_ingredient | 23 | MODERATE | `4a7f43520051296652821daf707aa547a844d000a11b7f215a307f2ea7af185d` |

Paths under `output/rxnorm_probe_*.zip`.

## Done this session

- [x] Phase 0 hygiene
- [x] Switched baseline to newest v7 same_env (user instruction)
- [x] RxNorm inventory (no RXNREL; lexical resolver)
- [x] `modules/evaluation/generate_rxnorm_policy_probes.py`
- [x] Unit tests nystatin + acetaminophen PASS
- [x] Control + 3 probes + ZIPs + analysis docs
- [ ] Leaderboard scores (user)

## Unit tests

- nystatin → `7597`: PASS
- acetaminophen 325-650 → `313782`: PASS

## Do not

- Rerun models / Qwen / v9 for this task
- Auto-submit Viettel
- Auto-commit
