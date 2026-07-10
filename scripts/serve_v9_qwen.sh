#!/usr/bin/env bash
# Serve Qwen/Qwen3.5-9B locally via vLLM (OpenAI-compatible on 127.0.0.1:8000).
# Prefer a free GPU. Do NOT co-locate with SapBERT/NER in the same GPU process.
set -euo pipefail

source /home/student10/miniforge3/etc/profile.d/conda.sh

ENV_NAME="${V9_VLLM_ENV:-v9_vllm}"
MODEL="${V9_MODEL:-Qwen/Qwen3.5-9B}"
HOST="${V9_HOST:-127.0.0.1}"
PORT="${V9_PORT:-8000}"
MAX_LEN="${V9_MAX_MODEL_LEN:-16384}"
GPU_UTIL="${V9_GPU_MEM_UTIL:-0.90}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

export CUDA_VISIBLE_DEVICES
export HF_HOME="${HF_HOME:-/storage/student10/tungnl/cache/huggingface}"
export TORCH_HOME="${TORCH_HOME:-/storage/student10/tungnl/cache/torch}"
mkdir -p "${HF_HOME}" "${TORCH_HOME}"
conda activate "${ENV_NAME}"

echo "Serving ${MODEL} on ${HOST}:${PORT} (CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES})"
echo "Using conda env: ${ENV_NAME}"
echo "HF_HOME=${HF_HOME}"

# Recommended conceptual command from the v9 plan.
# If BF16 OOM on 8GB Quadro RTX 4000, the failure is reported by vLLM;
# do not silently switch models.
exec vllm serve "${MODEL}" \
    --host "${HOST}" \
    --port "${PORT}" \
    --max-model-len "${MAX_LEN}" \
    --gpu-memory-utilization "${GPU_UTIL}" \
    --language-model-only \
    --reasoning-parser qwen3
