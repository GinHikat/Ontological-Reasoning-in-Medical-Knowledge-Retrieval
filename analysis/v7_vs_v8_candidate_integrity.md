# v7 vs v8 candidate integrity

## Scope
Isolated THUỐC candidate-linking experiment on top of `v7_structured`.
Same-environment baseline: `output/v7_regression` (see `analysis/v7_regression_nondeterminism.md`).
Canonical scored artifact remains the leaderboard reference (Score 24.79660).

## Drug totals
- Total final drugs: 276
- V7 (same-env) drugs with candidates: 274
- V7 (same-env) drugs without candidates: 2
- Canonical v7 drugs with candidates: 259
- Canonical v7 drugs without candidates: 17
- Final drugs originating from ontology drug recall (exact span overlap): 202
- Final drugs with preset metadata: 202

### Preset aliases
- unambiguous: 202
- ambiguous: 0
- invalid/missing: 0

### Linking path
- V8 direct preset path used: 202
- V8 SapBERT fallback used: 74

## Candidate changes (v7_regression → v8)
- unchanged candidate arrays: 275
- changed candidate arrays: 1
- newly linked drugs: 0
- newly unlinked drugs: 0
- previously linked drugs that changed ID: 1

**How many of the 17 previously unlinked canonical-v7 drugs received a candidate in v8?**
0 additional vs same-env v7 (15/17 were already linked under same-env SapBERT numerics; 1 remains unlinked in both; 1 other remains unlinked in both). Same-env unlinked count is 2 in both v7_regression and v8.

**How many of the 259 previously linked canonical-v7 drugs changed to a different candidate?**
Versus same-env v7_regression: **1** drug candidate changed.

## The single change
File 41, text `al pain` inside `abdominal pain`.
- match: embedded_compact alias `alpain`
- preset RxCUI: 602512 (unambiguous)
- v7 SapBERT: 152220 → v8 preset: 602512
- This is a noisy false-positive ontology alias hit inside a symptom phrase.

## Noisy pattern inspection
See `analysis/v8_noisy_cases.json` for methadone/lasix/vancozosyn/bactrim contexts.
