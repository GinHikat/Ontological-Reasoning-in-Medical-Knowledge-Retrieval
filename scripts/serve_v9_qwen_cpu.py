#!/usr/bin/env python3
"""Minimal localhost OpenAI-compatible chat server for Qwen on CPU.

Used only as an explicit hardware fallback when GPU vLLM cannot load
Qwen/Qwen3.5-9B (e.g. 8GB Quadro RTX 4000 OOM). Same model id; no external API.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Optional

import torch
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = os.environ.get("V9_MODEL", "Qwen/Qwen3.5-9B")
MODEL_PATH = os.environ.get(
    "V9_MODEL_PATH",
    "/storage/student10/tungnl/cache/huggingface/hub/models--Qwen--Qwen3.5-9B/manual",
)
if not os.path.isdir(MODEL_PATH):
    MODEL_PATH = MODEL_ID
HOST = os.environ.get("V9_HOST", "127.0.0.1")
PORT = int(os.environ.get("V9_PORT", "8000"))

# Prefer float16 on CPU if available to cut memory; fall back to float32.
DTYPE = torch.float16 if hasattr(torch, "float16") else torch.float32

print(f"[v9-cpu-server] Loading {MODEL_PATH} (id={MODEL_ID}) on CPU dtype={DTYPE} ...", flush=True)
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    dtype=DTYPE,
    device_map="cpu",
    trust_remote_code=True,
)
model.eval()
print("[v9-cpu-server] Model ready.", flush=True)

app = FastAPI(title="v9-local-qwen-cpu")


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


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest) -> dict[str, Any]:
    t0 = time.time()
    enable_thinking = False
    if req.chat_template_kwargs and "enable_thinking" in req.chat_template_kwargs:
        enable_thinking = bool(req.chat_template_kwargs["enable_thinking"])

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    try:
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=enable_thinking,
        )
    except TypeError:
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    inputs = tokenizer(prompt, return_tensors="pt")
    max_new = min(int(req.max_tokens), 2048)
    print(
        f"[v9-cpu-server] generate start prompt_tokens={inputs['input_ids'].shape[-1]} "
        f"max_new={max_new} thinking={enable_thinking}",
        flush=True,
    )

    gen_kwargs: dict[str, Any] = {
        **inputs,
        "max_new_tokens": max_new,
        "do_sample": False,
        "pad_token_id": tokenizer.eos_token_id,
    }
    # Deterministic greedy decode — do not pass temperature/top_p when not sampling.

    with torch.no_grad():
        output_ids = model.generate(**gen_kwargs)

    new_tokens = output_ids[0][inputs["input_ids"].shape[-1] :]
    text = tokenizer.decode(new_tokens, skip_special_tokens=True)
    # Strip accidental think blocks if the template ignored enable_thinking=false.
    if "</think>" in text:
        text = text.split("</think>", 1)[-1].strip()
    elif "<think>" in text:
        text = text.split("<think>", 1)[-1]
        if "</think>" in text:
            text = text.split("</think>", 1)[-1].strip()

    dt = time.time() - t0
    print(
        f"[v9-cpu-server] generate done new_tokens={int(new_tokens.shape[0])} "
        f"secs={dt:.1f} chars={len(text)}",
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
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": int(inputs["input_ids"].shape[-1]),
            "completion_tokens": int(new_tokens.shape[0]),
            "total_tokens": int(inputs["input_ids"].shape[-1] + new_tokens.shape[0]),
        },
    }


if __name__ == "__main__":
    if HOST not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit(f"Refusing non-local host: {HOST}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
