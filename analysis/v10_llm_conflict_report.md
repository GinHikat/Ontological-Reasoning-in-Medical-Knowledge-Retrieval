# v10_llm_conflict_resolution report

documents: 100
base_v7_snapshot files: 100
trace files: 100

## Funnel
- conflicts considered (cache accepts scanned): 1257
- Category A proposed (preview): 7 / accepted: 6
- Category B proposed (preview): 3 / accepted: 3
- Category C proposed (preview): 18 / accepted: 18
- Category D proposed (preview): 12 / accepted: 12
- total replacements: 39

## Candidate consistency
- CONSISTENT: 36
- QUESTIONABLE: 3
- INCONSISTENT: 0
- UNRESOLVED: 0

## Hard invariants
- invalid spans: 0
- missing documents: 0
- malformed JSON: 0
- empty traces: 0
- pure additions: 0
- unpaired removals: 0
- unexpected modifications: 0

## Replacements per document
- file 3: 4
- file 4: 3
- file 88: 3
- file 19: 2
- file 23: 2
- file 50: 2
- file 57: 2
- file 1: 1
- file 5: 1
- file 16: 1
- file 18: 1
- file 24: 1
- file 28: 1
- file 32: 1
- file 36: 1
- file 37: 1
- file 41: 1
- file 47: 1
- file 51: 1
- file 58: 1
- file 63: 1
- file 75: 1
- file 83: 1
- file 86: 1
- file 87: 1
- file 94: 1
- file 96: 1
- file 97: 1

No document exceeds 10 replacements.

## Decision

SCORED — completed; not promoted over v7

Official (submitted 11/07/2026 19:17): Score **24.04370** / WER 72.4852 / J_assertion 30.0917 / J_candidates 16.9044
vs v9 **+0.20080** / vs v7 **−0.75290**. See `analysis/v10_leaderboard_result.md`.

