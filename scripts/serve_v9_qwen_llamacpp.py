#!/usr/bin/env python3
"""Local OpenAI-compatible chat server for Qwen/Qwen3.5-9B via llama.cpp (CPU).

Same model id as the HF/vLLM path. Uses a local Q4_K_M GGUF of Qwen3.5-9B so
CPU inference can finish the v9 cache in reasonable time. Localhost only.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI
from llama_cpp import Llama
from pydantic import BaseModel

MODEL_ID = os.environ.get("V9_MODEL", "Qwen/Qwen3.5-9B")
GGUF_PATH = os.environ.get(
    "V9_GGUF_PATH",
    "/storage/student10/tungnl/cache/huggingface/hub/models--Qwen--Qwen3.5-9B/gguf/Qwen3.5-9B-Q4_K_M.gguf",
)
HOST = os.environ.get("V9_HOST", "127.0.0.1")
PORT = int(os.environ.get("V9_PORT", "8000"))
N_THREADS = int(os.environ.get("V9_CPU_THREADS", str(os.cpu_count() or 8)))
N_CTX = int(os.environ.get("V9_N_CTX", "16384"))
# Keep some cores free for the cache client / OS on shared lab boxes.
N_THREADS_BATCH = int(os.environ.get("V9_CPU_THREADS_BATCH", str(N_THREADS)))

if not os.path.isfile(GGUF_PATH):
    raise SystemExit(f"GGUF not found: {GGUF_PATH}")

print(
    f"[v9-llamacpp] Loading {GGUF_PATH} as id={MODEL_ID} "
    f"n_threads={N_THREADS} n_ctx={N_CTX} ...",
    flush=True,
)
llm = Llama(
    model_path=GGUF_PATH,
    n_ctx=N_CTX,
    n_threads=N_THREADS,
    n_threads_batch=N_THREADS_BATCH,
    n_gpu_layers=0,
    logits_all=False,
    verbose=False,
    chat_format=None,  # use model's native chat template from GGUF
)


def _reset_kv() -> None:
    """Clear KV cache between requests to avoid find_slot corruption after aborts."""
    try:
        llm.reset()
    except Exception as exc:  # noqa: BLE001 — best-effort recovery
        print(f"[v9-llamacpp] reset warning: {exc}", flush=True)
print("[v9-llamacpp] Model ready.", flush=True)

app = FastAPI(title="v9-local-qwen-llamacpp")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 2048
    chat_template_kwargs: Optional[dict[str, Any]] = None


@app.get("/v1/models")
def list_models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [{"id": MODEL_ID, "object": "model", "owned_by": "local"}],
    }


def _strip_think(text: str) -> str:
    if "</think>" in text:
        return text.split("</think>", 1)[-1].strip()
    if "<think>" in text:
        rest = text.split("<think>", 1)[-1]
        if "</think>" in rest:
            return rest.split("</think>", 1)[-1].strip()
    return text.strip()


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest) -> dict[str, Any]:
    t0 = time.time()
    enable_thinking = False
    if req.chat_template_kwargs and "enable_thinking" in req.chat_template_kwargs:
        enable_thinking = bool(req.chat_template_kwargs["enable_thinking"])

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    # Qwen3.5: disable thinking unless explicitly requested.
    if not enable_thinking:
        # Prefer chat-template kwarg; also inject /no_think as belt-and-suspenders.
        if messages and messages[0]["role"] == "system":
            if "/no_think" not in messages[0]["content"]:
                messages[0]["content"] = messages[0]["content"].rstrip() + "\n/no_think"
        else:
            messages.insert(0, {"role": "system", "content": "/no_think"})

    max_new = max(1, min(int(req.max_tokens), 2048))
    print(
        f"[v9-llamacpp] generate start max_new={max_new} thinking={enable_thinking} "
        f"msgs={len(messages)}",
        flush=True,
    )

    # Greedy / near-greedy decode for extraction.
    temperature = float(req.temperature)
    top_p = float(req.top_p)
    do_sample = temperature > 0.0

    _reset_kv()
    try:
        try:
            out = llm.create_chat_completion(
                messages=messages,
                temperature=temperature if do_sample else 0.0,
                top_p=top_p if do_sample else 1.0,
                max_tokens=max_new,
                stream=False,
            )
        except TypeError:
            # Older llama-cpp may not accept all kwargs.
            out = llm.create_chat_completion(
                messages=messages,
                temperature=0.0,
                max_tokens=max_new,
            )
    except Exception as exc:  # noqa: BLE001
        _reset_kv()
        print(f"[v9-llamacpp] generate ERROR: {exc}", flush=True)
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model or MODEL_ID,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": ""},
                    "finish_reason": "error",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "error": str(exc),
        }

    choice = out["choices"][0]
    text = _strip_think(str(choice["message"].get("content") or ""))
    usage = out.get("usage") or {}
    dt = time.time() - t0
    completion_tokens = int(usage.get("completion_tokens") or 0)
    print(
        f"[v9-llamacpp] generate done new_tokens={completion_tokens} "
        f"secs={dt:.1f} chars={len(text)} tok/s="
        f"{(completion_tokens / dt) if dt > 0 and completion_tokens else 0:.2f}",
        flush=True,
    )
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model or MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": choice.get("finish_reason") or "stop",
            }
        ],
        "usage": {
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": completion_tokens,
            "total_tokens": int(usage.get("total_tokens") or 0),
        },
    }


if __name__ == "__main__":
    if HOST not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit(f"Refusing non-local host: {HOST}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
