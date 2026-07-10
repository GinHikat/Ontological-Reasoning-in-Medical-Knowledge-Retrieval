# RxNorm Probe Analysis and Next Direction

## 1. Assumption used

The official v7 submission and the three RxNorm probes were produced from the same underlying v7 code.

Differences in:

```text
WER
J_assertion
num_scored
entity counts
entity types
```

are attributed to existing Mac GPU/model inference nondeterminism.

We will not investigate or attempt to fix this nondeterminism.

The v7 code is treated as the reference system rather than requiring two pipeline runs to produce identical output artifacts.

Under this assumption, the useful comparison is the candidate metric:

```text
J_candidates
```

---

## 2. Results

| Submission            | J_candidates | Difference from v7 |
| --------------------- | -----------: | -----------------: |
| **v7 reference**      |  **17.4691** |                  — |
| Example Policy        |      17.4521 |            −0.0170 |
| Ingredient First      |      17.1154 |            −0.3537 |
| Baseline + Ingredient |      17.0103 |            −0.4588 |

The candidate contribution to the final score has weight:

```text
0.4
```

Therefore, the approximate candidate-only final-score effects are:

| Policy                | Candidate-only score effect |
| --------------------- | --------------------------: |
| Example Policy        |                     −0.0068 |
| Ingredient First      |                     −0.1415 |
| Baseline + Ingredient |                     −0.1835 |

---

## 3. Main conclusion

The Example Policy is effectively neutral relative to v7:

```text
17.4691 → 17.4521
```

The difference is only:

```text
−0.017 J_candidates
```

This is too small to justify further leaderboard submissions or a large linker rewrite.

The experiment does not show that the forum-derived policy improves the current system.

It shows:

```text
Existing v7 candidate policy
≈
Example Policy
>
Ingredient First
>
Baseline + Ingredient
```

Therefore:

```text
Do not replace the current v7 linker globally with the Example Policy.

Do not adopt an ingredient-first policy.

Do not return multiple candidates as a hedge.
```

---

## 4. What was learned reliably

### 4.1 Multi-candidate hedging is harmful

The `Baseline + Ingredient` probe had the lowest candidate score:

```text
17.0103
```

Appending an ingredient candidate to an existing candidate usually lowers Jaccard similarity.

Therefore, future drug linking should normally return:

```text
one canonical RxCUI
```

not:

```json
["clinical_drug_rxcui", "ingredient_rxcui"]
```

Multiple candidates should only be returned when there is strong evidence that the gold annotation itself contains multiple IDs.

There is currently no such evidence.

---

### 4.2 Global ingredient-first mapping is harmful

The Ingredient First policy reduced candidate performance:

```text
17.4691 → 17.1154
```

Therefore, even though the official nystatin example uses an ingredient concept, this rule does not generalize to all drugs.

The linker should not reduce every medication to:

```text
IN/PIN
```

Strength, formulation, route, and the original RxNorm concept still matter.

---

### 4.3 The official-example policy is not a breakthrough

The Example Policy was the best of the three probes but remained slightly below v7:

```text
v7:             17.4691
Example Policy: 17.4521
```

This indicates that the policy may be correct for selected cases but is not broadly better than the existing hybrid linker.

It can be retained as a possible local fallback:

```text
No reliable strength
+
safe single ingredient
+
no good existing candidate
→ consider IN/PIN
```

It should not override an existing confident candidate.

---

### 4.4 RxNorm policy is not the main remaining bottleneck

The best candidate-policy experiment changed the candidate score by almost nothing.

Meanwhile, the system still has approximately:

```text
WER ≈ 72–73
J_assertion ≈ 30
J_candidates ≈ 17
```

The large remaining problem is not choosing between closely related RxNorm levels.

The larger problem is:

```text
missing entities
incorrect spans
incorrect types
incorrect assertions
```

Candidate optimization cannot produce a major score jump while entity extraction remains this weak.

---

## 5. Decision on RxNorm development

Stop spending leaderboard submissions on broad RxNorm policy probes.

Keep the following conclusions:

```text
1. Return one candidate, not a list of alternatives.

2. Do not map all drugs to ingredients.

3. Preserve the existing hybrid candidate when it is available.

4. Ingredient fallback may be used only for narrow, high-confidence cases.

5. A strength-aware generic SCD policy is reasonable, but it is not currently a major score lever.

6. Do not prioritize another RxNorm-only version.
```

The three probes should be recorded as completed ablations.

---

## 6. Next major version

Proceed to:

```text
v9_llm_recall
```

The goal is not to replace the deterministic pipeline.

The goal is to use a self-hosted LLM as another high-recall candidate generator:

```text
ViHealthBERT candidates
+
section/rule candidates
+
ontology candidates
+
LLM candidates
        ↓
deterministic exact-span validation
        ↓
merge and overlap handling
        ↓
existing ICD/RxNorm linker
        ↓
existing assertion detector
```

The LLM should initially propose only:

```text
TRIỆU_CHỨNG
CHẨN_ĐOÁN
THUỐC
```

It should not generate:

```text
character offsets
ICD IDs
RxCUIs
assertions
final submission JSON
```

These remain deterministic responsibilities.

---

## 7. First v9 experiment

The first v9 experiment should be strictly additive.

For every LLM proposal:

```text
1. The proposed text must be an exact substring of the original document.

2. Offsets must be calculated programmatically.

3. The proposal must pass a second LLM verification step.

4. The span must not overlap an existing v7 entity.

5. Existing v7 entities must not be removed or modified.

6. Existing candidates and assertions must remain unchanged.

7. Only completely new, non-overlapping entities may be added.
```

This isolates the question:

```text
Can an LLM find valid clinical entities that v7 completely misses?
```

---

## 8. Why additive LLM recall comes first

The current deterministic system contains many overlapping or imperfect entities.

Allowing an LLM to replace or retag them immediately would make it difficult to determine whether a score change came from:

```text
new recall
span replacement
type correction
assertion changes
candidate changes
```

The first LLM version should therefore test recall only:

```text
v9 = v7 + verified non-overlapping LLM entities
```

If this improves the leaderboard, later versions can test:

```text
LLM overlap conflict resolution
LLM type correction
LLM span correction
LLM assertion reasoning
```

one at a time.

---

## 9. Development priority

Recommended order:

```text
1. Complete v9 LLM proposer and verifier.

2. Generate candidates for a difficult pilot subset.

3. Manually audit all accepted additions.

4. Run the full 100-record cache.

5. Compare fresh same-environment v7 and v9.

6. Confirm existing v7 entities remain unchanged.

7. Submit v9 only if it adds a meaningful number of credible entities.
```

A useful v9 should add more than a handful of entities.

However, excessive additions are also dangerous.

Suggested review ranges:

```text
0 additions
→ implementation/prompt failed

1–30 additions
→ likely too conservative, but inspect quality

30–250 additions
→ useful first submission range

250–500 additions
→ high recall but requires careful review

>500 additions
→ likely excessive false positives
```

These are review guidelines, not hard gold-derived thresholds.

---

## 10. Final strategic conclusion

The RxNorm forum post was worth testing, but it did not reveal a major scoring exploit.

The results show:

```text
Example Policy:
approximately neutral

Ingredient First:
harmful

Baseline + Ingredient:
more harmful
```

Therefore, the project should no longer spend submissions trying to infer broad RxNorm fallback rules.

Preserve the strongest practical lesson:

```text
Choose one canonical candidate.
Do not hedge with multiple RxCUIs.
```

Then shift development resources to the main bottleneck:

```text
entity recall and semantic understanding
```

The next major experiment is:

```text
v9_llm_recall
```

No additional unchanged-v7 control submission is needed under the accepted nondeterminism assumption.
