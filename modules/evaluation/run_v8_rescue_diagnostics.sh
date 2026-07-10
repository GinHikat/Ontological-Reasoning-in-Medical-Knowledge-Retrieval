#!/usr/bin/env bash
# Post-run diagnostics for v8_candidate_rescue (run after both pipelines finish).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
source /home/student10/miniforge3/etc/profile.d/conda.sh
conda activate nanachi

V7_DIR="${1:-output/v7_structured/same_env}"
V8_DIR="${2:-output/v8_candidate_rescue/same_env}"
INPUT_DIR="${3:-v_dataset/var/test}"
ANALYSIS_DIR="${4:-analysis}"

echo "=== Unlinked drug audit ==="
python modules/evaluation/analyze_unlinked_drugs.py \
  --canonical-dir output/v7_structured/run1/submission \
  --same-env-dir "$V7_DIR/submission" \
  --input-dir "$INPUT_DIR" \
  --analysis-dir "$ANALYSIS_DIR"

echo "=== Same-env causal compare + report ==="
TRACE_DIR=""
if [[ -d "$V8_DIR/trace" ]]; then
  TRACE_DIR="--trace-dir $V8_DIR/trace"
fi
# shellcheck disable=SC2086
python modules/evaluation/analyze_v8_candidate_rescue.py \
  --v7-dir "$V7_DIR" \
  --v8-dir "$V8_DIR" \
  --input-dir "$INPUT_DIR" \
  --analysis-dir "$ANALYSIS_DIR" \
  $TRACE_DIR \
  --package-zip output/v8_candidate_rescue_submission.zip

echo "=== Done ==="
