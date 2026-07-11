# Schema-first principles audit — starting state

Recorded at Phase 0. Analysis only; no commits/pushes; no pipeline reruns.

| Field | Value |
|-------|-------|
| **Host** | `ict14` |
| **Branch** | `tung` |
| **HEAD** | `0f7209159eeb6baa8e51034b49bec306e04e1b07` |
| **Working tree** | clean (`nothing to commit`) |
| **Dirty files** | none |
| **Project** | `schema_first_principles_audit` (not a model version) |

## Recent commits

```text
0f72091 docs: close v10 experiment with official leaderboard score; plan manual annotation phase
e073991 feat: v10 finalize — parallel runner --output-dir, base_v7 snapshot, analysis artifacts
4bd496e feat: v10 LLM conflict resolution pipeline, postprocessing, and validation analysis
baa37fe feat: v9 truncated-JSON salvage, parse-failure raw retention, output-dir layout fix, and prompt injection hardening
b7ac0ea feat: v9 additive freeze pipeline, CPU thread tuning, and session handoff docs
```

## Available output artifacts

| Path | Role | Count |
|------|------|------:|
| `output/v10_llm_conflict_resolution/base_v7_snapshot/` | Preferred **base-v7** (from completed v10 run) | 100 JSON |
| `output/v10_llm_conflict_resolution/submission/` | Preferred **v10** submission | 100 JSON |
| `output/v10_llm_conflict_resolution/trace/` | Preferred traces | 100 non-empty `*_trace.txt` |
| `output/v10_llm_conflict_resolution_submission.zip` | Competition ZIP (do not resubmit) | present |
| `output/v10_llm_conflict_resolution_full.zip` | Diagnostic ZIP | present |

Aggregate SHA256 of sorted file hashes:

| Set | Aggregate SHA256 |
|-----|------------------|
| base_v7_snapshot `*.json` | `faf5376280c764110013bda838c5b3a645287ebb3389400109b401c3728d18cd` |
| submission `*.json` | `f8694c7154d86c759f70483e88f52410719ef89f106774a00c145e7c2db2f567` |

Empty traces: **0**.

## Available input files

| Path | Count |
|------|------:|
| `v_dataset/var/test/*.txt` | 100 |

## Ontology / mapping resources (offline audit)

| Path | Purpose |
|------|---------|
| `v_dataset/viettel/base/short_diagnosis.csv` | ICD-10 id / name_vi / name_en (~12k) |
| `v_dataset/viettel/mapping/diagnosis_10.csv` | Full ICD hierarchy + index terms |
| `v_dataset/viettel/base/` (RxNorm assets as used by pipeline) | Drug candidate audit (TTY / level where recoverable) |

## Constraints for this audit

- Do **not** build v11 / change inference rules / rerun Qwen / rerun v7–v10.
- Do **not** submit to leaderboard.
- Do **not** investigate neural nondeterminism.
- Prefer base-v7 snapshot as the current-pipeline entity inventory (generated inside the completed v10 run).
