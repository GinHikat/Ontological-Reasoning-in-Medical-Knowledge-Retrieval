# RxNorm probe leaderboard results

Fill in after official scoring. Do not invent scores.

| Submission | Final | WER | J_assertion | J_candidates | Δ J_candidates | Δ Final |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Newest v7 same_env baseline | | | | | 0 | 0 |
| Example Policy | | | | | | |
| Ingredient First | | | | | | |
| Baseline + Ingredient | | | | | | |

## Expected invariants (if packaging is clean)

Because only THUỐC candidates change:

- WER and J_assertion should match the baseline submission used here
- The probed metric is J_candidates (and final score)

## Interpretation rules

### Outcome A — Example Policy > Ingredient First > Baseline
Ingredient fallback matters; strength-aware SCD adds value → integrate Example Policy carefully.

### Outcome B — Ingredient First > Example Policy > Baseline
Gold is broadly ingredient-oriented → build ingredient-first linker policy.

### Outcome C — Baseline + Ingredient wins by a large margin
Multi-candidate coverage matters → investigate multi-ID gold / annotation variability.

### Outcome D — all three worse
Do not redesign RxNorm linking around the forum hypothesis; return to v9 recall.

### Outcome E — Example Policy only slightly better
Integrate carefully; continue v9 because entity recall remains the main bottleneck.
