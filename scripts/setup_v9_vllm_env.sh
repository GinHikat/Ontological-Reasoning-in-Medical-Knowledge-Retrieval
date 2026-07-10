#!/usr/bin/env bash
# Create a SEPARATE vLLM environment for Qwen/Qwen3.5-9B.
# Does not modify the main competition pipeline environment (nanachi/tung).
set -euo pipefail

source /home/student10/miniforge3/etc/profile.d/conda.sh

ENV_NAME="${V9_VLLM_ENV:-v9_vllm}"
PYTHON_VERSION="${V9_VLLM_PYTHON:-3.11}"

echo "Creating conda env: ${ENV_NAME} (python=${PYTHON_VERSION})"
if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  echo "Env ${ENV_NAME} already exists"
else
  conda create -y -n "${ENV_NAME}" "python=${PYTHON_VERSION}"
fi

echo "Installing vLLM into ${ENV_NAME} ..."
conda activate "${ENV_NAME}"

# Keep large caches off nearly-full /home.
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/storage/student10/tungnl/cache/pip}"
export HF_HOME="${HF_HOME:-/storage/student10/tungnl/cache/huggingface}"
export TORCH_HOME="${TORCH_HOME:-/storage/student10/tungnl/cache/torch}"
mkdir -p "${PIP_CACHE_DIR}" "${HF_HOME}" "${TORCH_HOME}"

python -m pip install -U pip
python -m pip install -U "vllm" "openai"

python - <<'PY'
import vllm, torch
print("vllm", vllm.__version__)
print("torch", torch.__version__)
print("cuda", torch.cuda.is_available())
PY

echo "Done. Start server with scripts/serve_v9_qwen.sh when a GPU is free."
