# RxNorm Hidden-Policy Probe Results

## 1. Submitted probes

All three submissions were generated from the same newest-v7 output and differed only in `THUỐC.candidates`.

| Probe                 |  Final score |     WER | J_assertion | J_candidates |
| --------------------- | -----------: | ------: | ----------: | -----------: |
| **Example Policy**    | **24.00320** | 72.8869 |     29.6282 |  **17.4521** |
| Ingredient First      |     23.86850 | 72.8869 |     29.6282 |      17.1154 |
| Baseline + Ingredient |     23.82650 | 72.8869 |     29.6282 |      17.0103 |

The identical WER and assertion scores confirm that the experiment was controlled correctly. Only candidate selection affected the results.

---

## 2. Pairwise differences

### Example Policy vs Ingredient First

```text
Δ J_candidates = +0.3367
Δ final score  = +0.1347
```

The Example Policy is clearly better than mapping all eligible drugs to ingredient-level concepts.

This suggests:

```text
No strength
→ ingredient fallback may be reasonable

Explicit strength
→ retain/select a generic clinical drug concept when possible
```

A purely ingredient-first policy is too aggressive.

---

### Example Policy vs Baseline + Ingredient

```text
Δ J_candidates = +0.4418
Δ final score  = +0.1767
```

Adding both the original candidate and the ingredient candidate performs substantially worse than selecting one canonical candidate.

This strongly suggests that the gold annotation usually expects:

```text
one canonical RxCUI
```

rather than a broad list of plausible alternatives.

Because candidate scoring uses Jaccard similarity, unnecessary extra candidates are penalized.

---

### Ingredient First vs Baseline + Ingredient

```text
Δ J_candidates = +0.1051
Δ final score  = +0.0420
```

Even when ingredient-level mapping is imperfect, selecting only the ingredient is better than returning both the original and ingredient candidates.

Again, this indicates:

```text
choose one candidate
rather than hedge with multiple candidates
```

---

## 3. Main conclusion

The ranking is:

```text
Example Policy
>
Ingredient First
>
Baseline + Ingredient
```

Therefore, the strongest current hypothesis is:

```text
1. Prefer a single canonical RxCUI.

2. If no explicit drug strength is present:
   fallback toward IN/PIN ingredient concepts.

3. If an explicit strength is present:
   prefer a generic SCD when a sufficiently reliable match exists.

4. For strength ranges:
   using the lower bound is consistent with the official example.

5. Do not append ingredient candidates to an existing candidate list as a hedge.
```

This is consistent with the official examples:

```text
nystatin oral suspension 5 ml
→ no actual drug strength
→ ingredient nystatin

acetaminophen 325–650 mg po
→ explicit strength range
→ lower bound 325 mg
→ generic clinical drug
```

---

## 4. What this experiment does not prove

We did not submit the unchanged newest-v7 output as a control.

Therefore, we cannot yet determine whether:

```text
Example Policy
```

is better or worse than leaving the newest-v7 candidates unchanged.

We can only conclude that, among the three tested policies:

```text
Example Policy is the best.
```

The old official v7 result of `J_candidates = 17.4691` cannot be used as the control because it came from a different pipeline run with different:

```text
WER
assertions
entity counts
num_scored
```

The fact that `17.4521` is close to `17.4691` is interesting but not a valid direct comparison.

---

## 5. Interpretation of multi-candidate output

The `Baseline + Ingredient` probe is the clearest negative result.

It changed 23 drug entities by appending an ingredient alternative and produced the lowest candidate score:

```text
17.0103
```

This means we should not return multiple candidates merely because several RxNorm concepts are medically plausible.

A list containing:

```json
["baseline_rxcui", "ingredient_rxcui"]
```

is generally worse than choosing the single candidate most likely to match the organiser's canonicalization rule.

Future linkers should therefore output:

```text
one candidate per drug entity
```

unless there is strong new evidence that a specific gold entity contains multiple RxCUIs.

---

## 6. Interpretation of ingredient fallback

Ingredient First was better than multi-candidate hedging but worse than Example Policy.

Therefore:

```text
ingredient fallback is useful
but should not replace strength-aware clinical drug matching globally
```

The likely policy is conditional:

```text
No reliable strength
→ IN/PIN

Reliable strength and compatible form
→ SCD
```

rather than:

```text
always IN
```

---

## 7. Known probe limitations

The current probe generator still has some imperfections:

### Combination drugs

A mention such as:

```text
albuterolipratropium nebulizer
```

can be interpreted as a single albuterol ingredient even though it contains:

```text
albuterol + ipratropium
```

Combination-drug mentions should normally be left unchanged unless all ingredients can be resolved safely.

### Unit normalization

The current policy does not always equate:

```text
1 gram
```

with:

```text
1000 mg
```

This can cause strength-bearing mentions to fall back to the ingredient instead of selecting an SCD.

### SCD ties

Several mentions, including:

```text
aspirin 325mg
acetaminophen 500mg
```

have multiple plausible SCDs in the local dictionary.

The current probe falls back to ingredient when it cannot identify one unique best SCD.

Therefore, the measured Example Policy score may underestimate the value of a better strength/form-aware tie-breaker.

---

## 8. Recommended implementation direction

Do not integrate Ingredient First.

Do not use multiple candidates as a hedge.

Use the Example Policy as the basis of the future drug linker:

```text
Step 1:
Parse ingredient, strength, strength range, route, dose form, and brand.

Step 2:
If the mention has no reliable strength:
select one safe IN/PIN ingredient concept.

Step 3:
If the mention has a reliable strength:
select one generic SCD matching:
- ingredient
- normalized strength
- explicit dose form
- route-compatible form

Step 4:
For ranges, test the lower bound first.

Step 5:
Prefer generic SCD over branded SBD unless the text explicitly contains a brand.

Step 6:
If SCD selection remains ambiguous:
fallback to one ingredient concept.

Step 7:
Never append multiple plausible alternatives merely for coverage.
```

Before integration, improve:

```text
g ↔ mg ↔ mcg normalization
combination-drug detection
dose-form normalization
route compatibility
SCD tie-breaking
```

---

## 9. Recommended next submission

The highest-value remaining control experiment is:

```text
unchanged newest-v7 output
```

Submit the exact same frozen baseline used to generate these three probes.

That gives the true comparison:

```text
Newest v7 unchanged
vs
Example Policy
```

Interpretation:

### If unchanged v7 J_candidates < 17.4521

The Example Policy genuinely improves the linker and should be integrated.

### If unchanged v7 J_candidates ≈ 17.4521

The policy is mostly neutral. Do not invest heavily in it.

### If unchanged v7 J_candidates > 17.4521

The existing linker is better overall. Keep the forum-derived policy only as a limited fallback for selected cases.

---

## 10. Strategic decision

The forum experiment was worthwhile.

It established two useful facts:

```text
Multiple candidate hedging is harmful.

Conditional ingredient/SCD selection is better than universal ingredient mapping.
```

However, it has not demonstrated a major candidate-score breakthrough.

The best probe reached:

```text
J_candidates = 17.4521
```

which remains low relative to the overall competition gap.

Therefore, after submitting the unchanged newest-v7 control, development should resume on:

```text
v9_llm_recall
```

The LLM should improve missing entity recall, while the deterministic linker should use the following RxNorm preference:

```text
single canonical candidate
+
ingredient fallback when strength is absent
+
generic SCD when strength is reliably available
```
