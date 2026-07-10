v7 regression investigation
==========================

Question: Do shared-class edits for v8 change v7_structured competition output?

Method:
1. Ran full v7_structured with post-edit code -> output/v7_regression
2. Temporarily restored HEAD versions of hybrid.py / clinical.py /
   ontology_drug_recall.py and ran samples 1,10,11,12,100
   -> output/v7_orig_code_sample
3. Compared all three against canonical output/v7_structured/run1/submission

Results (5-file sample):
- canonical vs ORIG_CODE: span=0 type=4 cand=8
- canonical vs OUR_v7_regression: span=0 type=4 cand=8
- ORIG_CODE vs OUR_v7_regression: span=0 type=0 cand=0

Full 100-file OUR_v7_regression vs canonical:
- span/text mismatches: 0
- assertion mismatches: 0
- type mismatches: 90 (disease/symptom SapBERT borderline flips)
- candidate mismatches: 142 (SapBERT retrieval nondeterminism)

Conclusion:
- Our code changes do NOT alter v7 behavior vs the original code in the
  same environment (bit-identical on the sample; same mismatch pattern
  vs canonical as original code).
- Bit-identical reproduction of the scored canonical artifact is not
  achievable on this machine due to SapBERT numerical nondeterminism
  (MPS/CPU float differences and borderline cosine ties), not due to
  v8 opt-in flags (defaults remain False).

Therefore for v8 candidate-integrity measurement we compare:
  output/v8_candidate_integrity  vs  output/v7_regression
(same environment / same SapBERT numerics), while still treating
canonical score 24.79660 as the leaderboard baseline reference.
