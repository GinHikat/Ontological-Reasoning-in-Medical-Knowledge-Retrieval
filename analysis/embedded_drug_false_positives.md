# Embedded Drug False Positives

## Case: `al pain` inside `abdominal pain`

Observed in the previous `v8_candidate_integrity` (override) experiment.

| Field | Value |
|---|---|
| Final entity text | `al pain` |
| Surrounding phrase | `abdominal pain` |
| Match type | `embedded_compact` |
| Matched alias | `alpain` |
| Behavior under override v8 | preset RxCUI replaced the SapBERT candidate |
| Same-env impact | 1 / 276 drug candidates changed |

### Why this matters

Unconditional preset override can change an already-linked SapBERT candidate when an embedded alias fires inside a non-drug phrase. That single change made the override experiment a negative/no-op ablation for leaderboard purposes.

### Rescue-mode policy (`v8_candidate_rescue`)

```text
if v7 already linked "al pain":
    keep the v7 candidate exactly
    do NOT override with preset RxCUI
```

Expected:

```text
0 candidate change for "al pain"
```

### Scope note

This document records the false-positive pattern. Broad embedded-drug recall precision cleanup is intentionally out of scope for `v8_candidate_rescue`, which is a candidate-rescue experiment, not an entity-removal experiment.
