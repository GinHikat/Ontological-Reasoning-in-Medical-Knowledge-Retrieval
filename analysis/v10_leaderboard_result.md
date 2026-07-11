# v10_llm_conflict_resolution — official leaderboard result

## 1. Official result

```text
Submission:
v10_llm_conflict_resolution

Submitted:
11/07/2026 19:17

Score:
24.04370

WER:
72.4852

num_scored:
100

J_assertion:
30.0917

num_records:
100

J_candidates:
16.9044
```

Status: **completed**. Decision: **not promoted over v7**. No more immediate v10 submissions.

## 2. Comparison with v9

Reference (v9 additive recall): Score 23.84290 / WER 72.7861 / J_assertion 29.7128 / J_candidates 16.9122.

```text
Score:
24.04370 - 23.84290
= +0.20080

WER:
72.4852 - 72.7861
= -0.3009
```

Because lower WER is better:

```text
WER improved by 0.3009
```

Assertions:

```text
30.0917 - 29.7128
= +0.3789
```

Candidates:

```text
16.9044 - 16.9122
= -0.0078
```

## 3. Comparison with v7

Reference (v7): Score 24.79660 / WER 72.0039 / J_assertion 31.3672 / J_candidates 17.4691.

```text
Score:
24.04370 - 24.79660
= -0.75290

WER:
72.4852 - 72.0039
= +0.4813
```

Because lower WER is better:

```text
WER worsened by 0.4813
```

Assertions:

```text
30.0917 - 31.3672
= -1.2755
```

Candidates:

```text
16.9044 - 17.4691
= -0.5647
```

## 4. Weighted score decomposition

Competition weighting used here: text 0.3, assertion 0.3, candidates 0.4.
Text contribution uses signed WER improvement (lower WER → positive contribution).

### v10 versus v9

```text
Text contribution:
0.3009 × 0.3
= +0.09027

Assertion contribution:
0.3789 × 0.3
= +0.11367

Candidate contribution:
-0.0078 × 0.4
= -0.00312

Total:
+0.20082
```

Round the total comparison to:

```text
+0.20080
```

to match the official score difference.

### v10 versus v7

```text
Text contribution:
-0.4813 × 0.3
= -0.14439

Assertion contribution:
-1.2755 × 0.3
= -0.38265

Candidate contribution:
-0.5647 × 0.4
= -0.22588

Total:
-0.75292
```

Round the total comparison to:

```text
-0.75290
```

to match the official score difference.

## 5. Nondeterminism assumption

```text
Separate executions of the neural pipeline are not deterministic
on the current Mac GPU environment.

The project will not attempt to fix this.

Therefore, leaderboard differences cannot be attributed entirely
to one set of replacements.
```

Do not use nondeterminism to dismiss the result completely.

The correct practical interpretation is:

```text
v10 produced a better official result than v9,
but still did not outperform the v7 reference.
```

## 6. Technical interpretation

- Conflict resolution beat additive recall: text and assertion axes drove the +0.20080 vs v9.
- Candidate score was effectively neutral vs v9 (−0.0078) and still well below v7 (−0.5647).
- Non-empty ICD/RxNorm on a replacement is not sufficient evidence of correctness.
- Categories **C** (span expansion) and **D** (symptom→diagnosis type correction) remain the main noise risk among the 39 replacements (A6 B3 C18 D12).

## 7. Final verdict

### Verdict 1 — v9 additive recall

```text
v9 additive LLM recall remains a negative experiment.

Adding a small number of non-overlapping LLM entities did not help.
No more additive-v9 submissions are planned.
```

### Verdict 2 — v10 conflict resolution

```text
v10 conflict resolution is better than v9 additive recall.

The official score improved by 0.20080 over v9.

The improvement came mainly from:
- better text score
- better assertion score

Candidate score was almost unchanged and slightly worse.
```

### Verdict 3 — comparison with v7

```text
v10 did not beat the v7 reference.

The score remained 0.75290 below v7.

Therefore, the current 39 conflict replacements are not reliable
enough to replace v7 as the main submission.
```

### Verdict 4 — interpretation of LLM value

```text
The experiment supports the hypothesis that the LLM is more useful
for span and type conflict resolution than for additive recall.

However, the current conflict rules are still too noisy.

Categories C and D remain the main risk:
- span expansion
- symptom-to-diagnosis type correction
```

### Verdict 5 — candidate mapping

```text
v10 did not improve candidate performance.

J_candidates:
v9  = 16.9122
v10 = 16.9044

The difference is effectively neutral but slightly negative.
```

Therefore:

```text
Candidate correctness remains an upstream span/type problem.

A non-empty ICD or RxNorm candidate is not sufficient evidence
that a replacement is correct.
```

### Summary verdict

```text
v10 validates conflict resolution as a more promising LLM use
than additive recall, but the current implementation is not strong
enough to replace v7.

The project should now stop submission-driven iteration and build
a manually annotated local development set.
```

## 8. Next phase

### Verdict 6 — next phase

```text
Stop leaderboard-driven model iteration temporarily.

Do not build v11 yet.

The next phase is:
manual annotation and local evaluation.
```

Primary goals:

```text
1. Create a small trusted development set.

2. Annotate exact spans, types, assertions, and candidates.

3. Measure v7, v9, and v10 locally.

4. Determine which replacement categories are actually correct.

5. Use annotation evidence before designing the next model version.
```

Suggested work items:

1. Select representative documents.
2. Define annotation guidelines.
3. Build annotation format and tooling.
4. Annotate the first pilot subset.
5. Implement local scorer.
6. Evaluate v7 and v10 against the pilot gold.

## Consolidated table

| Version                 |    Score |     WER | J_assertion | J_candidates | Decision                 |
| ----------------------- | -------: | ------: | ----------: | -----------: | ------------------------ |
| v7 reference            | 24.79660 | 72.0039 |     31.3672 |      17.4691 | Best current reference   |
| v9 additive recall      | 23.84290 | 72.7861 |     29.7128 |      16.9122 | Negative                 |
| v10 conflict resolution | 24.04370 | 72.4852 |     30.0917 |      16.9044 | Better than v9, below v7 |

RxNorm policy probes remain recorded separately in `state.md` (not part of this table).
