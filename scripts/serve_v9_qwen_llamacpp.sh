#!/usr/bin/env bash
# Fast CPU local OpenAI-compatible server for Qwen/Qwen3.5-9B via llama.cpp GGUF.
# Same model id. Localhost only. No external inference API.
set -euo pipefail

source /home/student10/miniforge3/etc/profile.d/conda.sh
conda activate "${V9_VLLM_ENV:-v9_vllm}"

export HF_HOME="${HF_HOME:-/storage/student10/tungnl/cache/huggingface}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/storage/student10/tungnl/cache/pip}"
export V9_MODEL="${V9_MODEL:-Qwen/Qwen3.5-9B}"
export V9_GGUF_PATH="${V9_GGUF_PATH:-/storage/student10/tungnl/cache/huggingface/hub/models--Qwen--Qwen3.5-9B/gguf/Qwen3.5-9B-Q4_K_M.gguf}"
export V9_HOST="${V9_HOST:-127.0.0.1}"
export V9_PORT="${V9_PORT:-8000}"
export V9_CPU_THREADS="${V9_CPU_THREADS:-$(nproc)}"
export V9_N_CTX="${V9_N_CTX:-8192}"

echo "ENV=v9_vllm MODEL=${V9_MODEL} GGUF=${V9_GGUF_PATH} THREADS=${V9_CPU_THREADS}"
exec python "$(dirname "$0")/serve_v9_qwen_llamacpp.py"
