#!/usr/bin/env bash
# CPU fallback local OpenAI-compatible server for Qwen/Qwen3.5-9B.
# Use ONLY when GPU vLLM cannot load the model (e.g. 8GB Quadro OOM).
# Same model id. Localhost only. No external API.
set -euo pipefail

source /home/student10/miniforge3/etc/profile.d/conda.sh

ENV_NAME="${V9_VLLM_ENV:-v9_vllm}"
MODEL="${V9_MODEL:-Qwen/Qwen3.5-9B}"
HOST="${V9_HOST:-127.0.0.1}"
PORT="${V9_PORT:-8000}"

conda activate "${ENV_NAME}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/storage/student10/tungnl/cache/pip}"
export HF_HOME="${HF_HOME:-/storage/student10/tungnl/cache/huggingface}"
export TORCH_HOME="${TORCH_HOME:-/storage/student10/tungnl/cache/torch}"
mkdir -p "${PIP_CACHE_DIR}" "${HF_HOME}" "${TORCH_HOME}"

python -m pip install -q "transformers>=4.51" "accelerate" "fastapi" "uvicorn" "pydantic"

export V9_MODEL="${MODEL}"
export V9_HOST="${HOST}"
export V9_PORT="${PORT}"
echo "HF_HOME=${HF_HOME}"

exec python "$(dirname "$0")/serve_v9_qwen_cpu.py"
