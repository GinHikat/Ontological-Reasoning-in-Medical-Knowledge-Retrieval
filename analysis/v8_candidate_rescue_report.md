# V8 Candidate Rescue Report

## Same-environment causal comparison

- v7: `output/v7_structured/same_env`
- v8: `output/v8_candidate_rescue/same_env`
- hard invariants pass: **True**
- failure_count: 0

## Drug linking

- Total drugs: 271
- Same-env v7 linked: 270
- Same-env v7 unlinked: 1
- V8 linked: 270
- V8 unlinked: 1
- Newly rescued drugs: **0**
- Existing candidates preserved: 270
- Existing candidates changed: **0** (MUST BE 0)
- Existing candidates removed: **0** (MUST BE 0)
- Still unlinked: 1

## Rescued examples

- (none)

## Unrescued examples

- `4` [59,64] `NSAID` (onto_alias=; preset=)

## Provenance (from traces)

- direct_preset_rescue count: 0
- transferred_preset_rescue count: 0
- v7_candidate_preserved count: 270
- unlinked_after_v7_and_rescue count: 1
- conflicting donor markers: 0
- transferred metadata markers: 0
