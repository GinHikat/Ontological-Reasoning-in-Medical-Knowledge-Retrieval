# CURRENT_WORK.md

> **Single active long-run handoff.** Rewrite (do not append) when a long job starts, changes, or finishes.
> User resume prompt: `continue from CURRENT_WORK.md`

---

## Active work

| Field | Value |
|-------|-------|
| **Status** | `DONE` — `free_first` full corpus **100/100** gold + compare written |
| **Updated** | 2026-07-12 22:30 +0700 |
| **Host** | `ict14` |
| **Experiment** | `openrouter_schema_teacher` profile **`free_first`** (`EXTERNAL_API_DIAGNOSTIC_ONLY`) |
| **tmux** | none (job finished; session gone) |

### Models (all $0)

| Role | Model |
|------|-------|
| A | `tencent/hy3:free` |
| B | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| C | `poolside/laguna-m.1:free` |
| Judge | `tencent/hy3:free` |

### Paths

| Role | Path |
|------|------|
| Output | `output/openrouter_schema_teacher_free/` |
| Cache | `cache/openrouter_schema_teacher_free/` |
| Analysis | `analysis/openrouter_teacher_free/` |
| Gold | `output/openrouter_schema_teacher_free/diagnostic_pseudo_gold/*.json` (100) |
| Report | `analysis/openrouter_teacher_free/final_report.md` |

### Finish summary

- Overnight `--full-only` exited 0 at 12:48 with **99/100** (doc **29** KeyError on hy3 entity missing `type`).
- Hardened `build_proposals` to skip incomplete entities; re-ran doc 29 → **100/100**.
- Compare vs frozen v7/v10 → `analysis/openrouter_teacher_free/{comparison_v7_v10.tsv,schema_metrics.*}`.
- Verdict: `FREE_ENSEMBLE_PARTIALLY_CORRECT_SCHEMA` (strong procedure-as-test rejection; sparse vs v7; do not submit).

### Quick checks

```bash
ls output/openrouter_schema_teacher_free/diagnostic_pseudo_gold/ | wc -l   # 100
cat analysis/openrouter_teacher_free/final_report.md
```

### Next (needs human decision)

1. Review `analysis/openrouter_teacher_free/final_report.md`.
2. Continue schema-audit manual annotation / local scorer (PLAN path), **or**
3. If starting paid teacher: **ask for NEW** extractor + judge model IDs first (`.env` paid IDs intentionally empty).

### !!! Before any paid / `default` profile run

Paid model IDs in `.env` are **empty on purpose**.

**Ask the user for NEW paid extractor + judge IDs** before:

```bash
OPENROUTER_TEACHER_PROFILE=default
OPENROUTER_EXTRACTOR_MODELS=<id1>,<id2>,<id3>
OPENROUTER_JUDGE_MODEL=<judge_id>
OPENROUTER_BUDGET_USD=<enough for paid>
```

## Do not

- Mix free outputs into competition submission
- Overwrite paid `openrouter_schema_teacher` artifacts
- Commit/push unless asked
- Start `profile=default` without user-chosen paid model IDs
