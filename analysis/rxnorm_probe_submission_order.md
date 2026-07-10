# Recommended leaderboard submission order

Baseline reference (newest v7 same_env):
- path: `/storage/student10/tungnl/Ontological-Reasoning-in-Medical-Knowledge-Retrieval/artifacts/v7_newest_same_env/submission`
- semantic hash: `71593faca03ed5339b805b96c381c9e4864693112cccddf3bc14461719653a60`
- entities: 3236
- drugs: 271

## Order

1. `rxnorm_probe_example_policy`
2. `rxnorm_probe_ingredient_first`
3. `rxnorm_probe_baseline_plus_ingredient`

## Reason

- Probe 1 tests the strongest hypothesis from official examples (no strength → IN; strength/range → SCD).
- Probe 2 tests whether gold is broadly ingredient-oriented.
- Probe 3 tests whether multi-candidate coverage (baseline + ingredient) helps Jaccard.

Do **not** submit automatically. Do **not** package the control baseline.

## ZIP artifacts

| Probe | Path | Size | SHA256 | Changed | Signal |
|-------|------|-----:|--------|--------:|--------|
| rxnorm_probe_example_policy | `/storage/student10/tungnl/Ontological-Reasoning-in-Medical-Knowledge-Retrieval/output/rxnorm_probe_example_policy.zip` | 91504 | `19b881fdcfa18c30f028e8f54db107d59d0868d403fac4c4e400d1a9f3309ddb` | 18 | LOW SIGNAL |
| rxnorm_probe_ingredient_first | `/storage/student10/tungnl/Ontological-Reasoning-in-Medical-Knowledge-Retrieval/output/rxnorm_probe_ingredient_first.zip` | 91494 | `880050861f2bd227b405fc74d9bee2cad51c9690c9555079d0c77ca37188684d` | 23 | MODERATE SIGNAL |
| rxnorm_probe_baseline_plus_ingredient | `/storage/student10/tungnl/Ontological-Reasoning-in-Medical-Knowledge-Retrieval/output/rxnorm_probe_baseline_plus_ingredient.zip` | 91652 | `4a7f43520051296652821daf707aa547a844d000a11b7f215a307f2ea7af185d` | 23 | MODERATE SIGNAL |

