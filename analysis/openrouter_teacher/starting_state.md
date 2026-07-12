# OpenRouter schema teacher — starting state

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY` — not for competition submission or training unless organizers confirm.

| Field | Value |
|-------|-------|
| **Recorded** | 2026-07-11 21:25 +0700 |
| **Host** | ict14 |
| **Branch** | `tung` |
| **Commit** | `eee2fac21356b34d749a9e620f8ca3dd449479e7` |
| **Dirty files** | none (clean working tree at start) |

## Paths

| Role | Path |
|------|------|
| Input documents | `v_dataset/var/test/` (100 `.txt` files) |
| Frozen v7 comparison | `output/v10_llm_conflict_resolution/base_v7_snapshot/` |
| Frozen v10 comparison | `output/v10_llm_conflict_resolution/submission/` |
| Schema-audit location | `analysis/schema_audit/` |
| Teacher outputs | `output/openrouter_schema_teacher/` |
| Request cache | `cache/openrouter_schema_teacher/` |

## Constraints (from brief)

- Do not rerun v7 / v9 / v10
- Do not manually annotate; no Streamlit; no training
- Do not submit / ZIP / commit / push automatically
- Independent extractors must not see v7/v10/audit flags
