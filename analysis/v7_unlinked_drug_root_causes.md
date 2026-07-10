# V7 Unlinked Drug Root-Cause Audit

Diagnostic only. No hard-coded predictions.

## Safeguard parameters used for recoverable_by_safe_containment

- prefix_extra <= 15
- suffix_extra <= 60
- total_extra <= 70
- recipient length <= 80

## Canonical scored v7 artifact

**Unavailable on disk.** Path `output/v7_structured/run1/submission` exists but contains
0 JSON files (gitignored historical artifact not restored after `data`→`v_dataset` rename).

Leaderboard reference from `state.md` / prior manifests:

- Score **24.79660**
- THUỐC 276; linked 259; unlinked **17**

See `analysis/v8_canonical_17_drug_audit.md` for observational notes.

## Fresh same-environment v7 run

- output: `output/v7_structured/same_env/submission`
- unlinked drugs: **1**
- recoverable_by_safe_containment: **0**

| Reason | Count |
|---|---:|
| NO_ONTOLOGY_EVIDENCE | 1 |

### Examples

- `4` [59,64] `NSAID` → NO_ONTOLOGY_EVIDENCE (recoverable=False)

### Interpretation

In this same-env snapshot SapBERT already links 270/271 drugs. The only empty candidate
has no ontology recall evidence, so provenance-transfer + rescue-only linking has no
safe target. That yields a **no-op ablation** for leaderboard upside (0 newly rescued).
