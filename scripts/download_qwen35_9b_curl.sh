#!/usr/bin/env bash
# Download Qwen/Qwen3.5-9B weight shards via curl (resume-friendly).
# Destination is under HF cache on /storage (not /home).
set -euo pipefail

OUT="${1:-/storage/student10/tungnl/cache/huggingface/hub/models--Qwen--Qwen3.5-9B/manual}"
mkdir -p "$OUT"
cd "$OUT"

download_one() {
  local f="$1"
  echo "=== $f ==="
  if [ -f "$f" ]; then
    echo "partial/exists $(du -h "$f" | awk '{print $1}')"
  fi
  curl -L --retry 30 --retry-delay 5 -C - \
    -o "$f" \
    "https://huggingface.co/Qwen/Qwen3.5-9B/resolve/main/$f"
  echo "DONE $f size=$(du -h "$f" | awk '{print $1}')"
}

for f in \
  model.safetensors-00001-of-00004.safetensors \
  model.safetensors-00002-of-00004.safetensors \
  model.safetensors-00003-of-00004.safetensors \
  model.safetensors-00004-of-00004.safetensors \
  model.safetensors.index.json \
  tokenizer.json \
  tokenizer_config.json \
  vocab.json \
  merges.txt \
  config.json \
  preprocessor_config.json \
  video_preprocessor_config.json \
  chat_template.jinja
do
  download_one "$f"
done

echo ALL_CURL_DONE
ls -lah
