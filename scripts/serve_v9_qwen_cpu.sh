#!/usr/bin/env bash
# CPU fallback local OpenAI-compatible server for Qwen/Qwen3.5-9B.
# Use ONLY when GPU vLLM cannot load the model (e.g. 8GB Quadro OOM).
# Same model id. Localhost only. No external API.
set -euo pipefail

source /home/student10/miniforge3/etc/profile.d/conda.sh

# Prefer dedicated v9_vllm when present; on ictserver6 fall back to nanachi (CPU).
ENV_NAME="${V9_VLLM_ENV:-}"
if [[ -z "${ENV_NAME}" ]]; then
  if conda env list | awk '{print $1}' | grep -qx 'v9_vllm'; then
    ENV_NAME=v9_vllm
  else
    ENV_NAME=nanachi
  fi
fi
MODEL="${V9_MODEL:-Qwen/Qwen3.5-9B}"
HOST="${V9_HOST:-127.0.0.1}"
PORT="${V9_PORT:-8000}"

conda activate "${ENV_NAME}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/storage/student10/tungnl/cache/pip}"
export HF_HOME="${HF_HOME:-/storage/student10/tungnl/cache/huggingface}"
export TORCH_HOME="${TORCH_HOME:-/storage/student10/tungnl/cache/torch}"
export V9_CPU_THREADS="${V9_CPU_THREADS:-$(nproc)}"
mkdir -p "${PIP_CACHE_DIR}" "${HF_HOME}" "${TORCH_HOME}"

python -m pip install -q "transformers>=4.51" "accelerate" "fastapi" "uvicorn" "pydantic"

export V9_MODEL="${MODEL}"
export V9_HOST="${HOST}"
export V9_PORT="${PORT}"
echo "ENV=${ENV_NAME} HF_HOME=${HF_HOME} V9_CPU_THREADS=${V9_CPU_THREADS}"

exec python "$(dirname "$0")/serve_v9_qwen_cpu.py"
