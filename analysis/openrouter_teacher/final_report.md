# Final report — openrouter_schema_teacher

**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`

Do **not** use these outputs in a competition submission.
Do **not** use them to train a final competition model unless organizers
explicitly confirm that external-API-generated offline training data is allowed.

This experiment is **not** a pipeline version (not v11). Frozen v7 remains the
canonical leaderboard reference (24.79660).

---

## 1. Exact model IDs and providers

| Role | Model ID | Family |
|------|----------|--------|
| Extractor A (precision) | `anthropic/claude-opus-4.8` | Anthropic |
| Extractor B (coverage) | `google/gemini-3.1-pro-preview` | Google |
| Extractor C (boundaries) | `openai/gpt-5.5` | OpenAI |
| Judge / critic | `anthropic/claude-opus-4.8` | Anthropic (independent calls) |

Selection mode: explicit `.env` after Models API validation
(`analysis/openrouter_teacher/model_selection.md`).

Note: `openai/gpt-5.5-pro` was abandoned for this run because the OpenRouter key
could not afford its default/high token reservation (HTTP 402). Non-pro `gpt-5.5`
was used as the OpenAI-family high-capability extractor.

## 2. API configuration and cost

| Setting | Value |
|---------|-------|
| Base URL | `https://openrouter.ai/api/v1` |
| Structured output | JSON Schema + response-healing plugin |
| Temperature | `0` |
| Max tokens | `8192` |
| Concurrency | `3` |
| Cache | `cache/openrouter_schema_teacher/` (SHA256 request hash) |
| Configured budget | `OPENROUTER_BUDGET_USD` (capped to live key remaining) |

Observed OpenRouter key state at stop:

- Key spending **limit = $3.00**, **remaining = $0.00**
- Account total credits still unused beyond the key cap
- Pilot process estimated spend ≈ **$1.46** (plus earlier debug/smoke calls)

## 3. Pilot validation

Auto-selected pilot ids (first run; later fixed to reject non-digit ids such as `*`):

```text
24 (procedure-heavy), 3 (lab-heavy), * (invalid; fixed), 37 (drug), 78 (clean-ish)
```

Curated audit-derived resume set:

```text
75, 36, 20, 37, 51
```

| Check | Result |
|-------|--------|
| API parse (pilot process) | ~92% OK (below 95% gate) |
| Valid final JSON | **1 / 5** (`24.json`) |
| Exact-span enforcement | active (aligner + gates) |
| Invented candidate IDs | stripped via local allow-list |
| Cache | working for identical successful requests |
| Cost accounting | usage ledger + budget stop |

**Pilot gates failed** → full 100-doc run did **not** start.

## 4. Full-run completion

**Status:** `BLOCKED` — OpenRouter key credit limit exhausted; pilot gates not satisfied.

Resume requires raising the key limit (or provisioning a key with sufficient remaining
budget), then re-running with resume (existing gold files are skipped).

## 5. Entity density comparison

On completed file `24.json` only:

| Source | Entities |
|--------|---------:|
| Teacher diagnostic gold | 22 |
| Frozen v7 | 32 |
| Frozen v10 | 32 |

Teacher is denser on symptoms, **sparser** overall, and produces **zero** lab-name /
lab-result entities on this procedure-heavy note (possible under-extraction of genuine
tests, or correct omission if none present — needs more files).

## 6. Procedure-as-test correction

Schema-audit flagged **7** `LIKELY_PROCEDURE_NOT_TEST` spans on file 24.

Teacher final output retains **0** of them as `TÊN_XÉT_NGHIỆM` → **7/7 rejected**.

This is direct positive evidence that frontier adjudication can correct the core
v7/v10 procedure→test schema failure on at least this document.

Corpus-level count over all 159 flagged spans: **not measured** (full run blocked).

## 7. Lab name/result segmentation

On file 24 teacher output: `TÊN_XÉT_NGHIỆM=0`, `KẾT_QUẢ_XÉT_NGHIỆM=0`, paired=0.

Insufficient evidence for lab segmentation behavior; lab-heavy pilot doc (`3` / `36`)
did not complete.

## 8. Symptom/diagnosis separation

File 24 teacher: 17 symptoms, 2 diagnoses, **0** overlapping sym↔dx pairs in final gold.

v7 file 24 had 0 diagnoses and 8 test-names (mostly procedures) — teacher retyped the
clinical picture toward diagnosis/symptom rather than procedure-as-test.

## 9. Drug-boundary behavior

Teacher: 3 drugs. Maximal-span proxy inconclusive on this small set.
RxNorm candidate counts: `{0:1, 1:2}` (local retrieval + model selection; no invented IDs).

## 10. Assertion behavior

`isFamily` count on completed gold: **0**.
Critic raised one `wrong_assertion` issue; final adjudication left entity count unchanged
(before=22, after=22).

## 11. ICD multi-candidate behavior

Diagnoses on file 24: **2**, both with **0** selected ICD candidates
(`diagnosis_candidate_count_distribution: {"0": 2}`).

Suggests either weak local retrieval for those spans or conservative model selection.
Not enough data for multi-code behavior.

## 12. RxNorm behavior

Drugs mostly received 0–1 RxCUI from the local candidate list. No ingredient-first hedge
layer was applied at selection time.

## 13. Model agreement

On file 24 raw proposals (after alignment):

| Model | Approx. proposals |
|-------|------------------:|
| `anthropic/claude-opus-4.8` | 23 |
| `google/gemini-3.1-pro-preview` | 3 |
| `openai/gpt-5.5` | 4 |

Large coverage disagreement: Gemini/GPT under-extracted vs Opus on this note.
Judge output density tracks Opus more closely. See
`analysis/openrouter_teacher/model_agreement.md` and
`model_disagreements.tsv`.

## 14. Critic findings

File 24: **6** critic issues
(`missed_entity` ×3, `wrong_boundary` ×2, `wrong_assertion` ×1).

Final critic adjudication did not change entity count (22→22). Critic is diagnostic,
not treated as ground truth.

## 15. Comparison with v7 and v10

Artifacts:

- `analysis/openrouter_teacher/comparison_v7_v10.tsv`
- `analysis/openrouter_teacher/schema_metrics.json`
- `analysis/openrouter_teacher/schema_metrics.md`

File 24 vs v7 (approx.): exact-agree 11; overlap-agree 19; additions 11; removals 21.
Primary qualitative delta: removal of procedure-as-test `TÊN_XÉT_NGHIỆM` spans.

## 16. Remaining risks

1. **Credit / key limit** blocked statistically meaningful corpus measurement.
2. Extractor disagreement is large; ensemble quality depends heavily on the judge.
3. Possible **lab under-extraction** on completed note (0 test entities).
4. ICD selection returned empty candidates for both diagnoses on file 24.
5. Auto pilot selection initially admitted a non-document id (`*`) from collisions TSV —
   fixed to require digit file ids.
6. Structured-output schema had to be sanitized (no `uniqueItems` / min/max) for Anthropic.

## 17. Architecture implications

Even with n=1 completed document, frontier models **can** reject procedure-as-test
errors that dominate the schema audit. That supports the schema-first architecture
conclusion: type/span policy is the bottleneck more than additive v10 conflict rules.

However, extractor disagreement and incomplete ontology coding imply a compliant next
system should **not** blindly distill a single frontier teacher dump. Prefer:

- task-specific span/type model (5 labels + NONE)
- deterministic exact-span validation
- local ontology retrieval + constrained candidate selection
- use teacher outputs only as offline diagnostics / weak labels if organizers allow

## 18. Compliance warning

```text
EXTERNAL_API_DIAGNOSTIC_ONLY
No competition submission was produced from these outputs.
No training run consumed these outputs.
OpenRouter was used solely to diagnose schema understanding.
```

---

## Diagnostic verdict

```text
FRONTIER_MODELS_PARTIALLY_CORRECT_SCHEMA
```

Reasons:

- Strong procedure-as-test correction on the completed procedure-heavy document (7/7).
- Incomplete pilot/full corpus; severe extractor disagreement; empty ICD selections;
  possible lab omissions → cannot claim strong corpus-wide schema mastery.

## Recommended compliant architecture

```text
UNCERTAIN
```

Measured reasons:

- **YES lean:** procedure rejection matches the schema-audit root cause; constrained
  ontology selection is the right shape for a ≤9B self-hosted imitate-the-teacher stack.
- **NO lean:** with only one finished document and large model disagreement, it is too
  early to commit that a ≤9B model can reproduce judge-quality schema decisions.
- Therefore **UNCERTAIN** until the pilot/full run completes under an adequate budget.
