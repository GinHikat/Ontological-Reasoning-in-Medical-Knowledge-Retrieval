#!/usr/bin/env python3
"""One-shot llama.cpp CPU bakeoff: Q4 vs Q8 vs BF16 on the same prompt.

Does NOT bind :8000. Uses few threads so it can run beside the live cache gen.
Writes analysis/v9_gguf_precision_bench.md
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from llama_cpp import Llama

GGUF_DIR = Path(
    "/storage/student10/tungnl/cache/huggingface/hub/models--Qwen--Qwen3.5-9B/gguf"
)
DEFAULTS = {
    "Q4_K_M": GGUF_DIR / "Qwen3.5-9B-Q4_K_M.gguf",
    "Q8_0": GGUF_DIR / "Qwen3.5-9B-Q8_0.gguf",
    "BF16": GGUF_DIR / "Qwen3.5-9B-BF16.gguf",
}

PROMPT_MESSAGES = [
    {
        "role": "system",
        "content": (
            "Extract clinical entities as JSON only. Types: TRIỆU_CHỨNG, "
            "CHẨN_ĐOÁN, THUỐC. Exact substrings only. /no_think"
        ),
    },
    {
        "role": "user",
        "content": (
            "Extract entities from:\n"
            "[L001] Lý do nhập viện: Đau ngực và khó thở\n"
            "[L002] Bệnh sử: Tăng huyết áp, đái tháo đường típ 2\n"
            "[L003] Thuốc đang dùng: metformin, amlodipine\n"
            "[L004] Khám: ran ẩm đáy phổi hai bên\n"
        ),
    },
]


def bench_one(path: Path, label: str, n_threads: int, n_ctx: int, max_tokens: int) -> dict:
    if not path.is_file():
        return {"label": label, "path": str(path), "error": "missing"}
    t_load0 = time.time()
    llm = Llama(
        model_path=str(path),
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_threads_batch=n_threads,
        n_gpu_layers=0,
        logits_all=False,
        verbose=False,
        chat_format=None,
    )
    t_load = time.time() - t_load0

    # warmup tiny
    llm.create_chat_completion(
        messages=[{"role": "user", "content": "ping /no_think"}],
        temperature=0.0,
        max_tokens=4,
    )

    t0 = time.time()
    out = llm.create_chat_completion(
        messages=PROMPT_MESSAGES,
        temperature=0.0,
        top_p=1.0,
        max_tokens=max_tokens,
    )
    dt = time.time() - t0
    usage = out.get("usage") or {}
    new_toks = int(usage.get("completion_tokens") or 0)
    prompt_toks = int(usage.get("prompt_tokens") or 0)
    text = (out["choices"][0]["message"].get("content") or "").strip()
    # free
    del llm
    return {
        "label": label,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "n_threads": n_threads,
        "n_ctx": n_ctx,
        "max_tokens": max_tokens,
        "load_sec": round(t_load, 2),
        "gen_sec": round(dt, 2),
        "prompt_tokens": prompt_toks,
        "completion_tokens": new_toks,
        "tok_per_sec": round(new_toks / dt, 3) if dt > 0 and new_toks else 0.0,
        "chars": len(text),
        "preview": text[:240].replace("\n", "\\n"),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--threads", type=int, default=8, help="Keep low beside live 40-thread cache")
    p.add_argument("--n-ctx", type=int, default=4096)
    p.add_argument("--max-tokens", type=int, default=256)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("analysis/v9_gguf_precision_bench.md"),
    )
    p.add_argument(
        "--json-out",
        type=Path,
        default=Path("analysis/v9_gguf_precision_bench.json"),
    )
    args = p.parse_args()

    results = []
    for label, path in DEFAULTS.items():
        print(f"=== bench {label} {path} ===", flush=True)
        r = bench_one(path, label, args.threads, args.n_ctx, args.max_tokens)
        print(json.dumps(r, ensure_ascii=False), flush=True)
        results.append(r)

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# v9 GGUF precision bakeoff (llama.cpp CPU)",
        "",
        "Same prompt / same `n_threads` / same `max_tokens`. Separate from live `:8000` cache job.",
        "",
        f"- threads: {args.threads}",
        f"- n_ctx: {args.n_ctx}",
        f"- max_tokens: {args.max_tokens}",
        "",
        "| Quant | Size | Load s | Gen s | Completion toks | tok/s | preview |",
        "|-------|-----:|-------:|------:|----------------:|------:|---------|",
    ]
    for r in results:
        if r.get("error"):
            lines.append(f"| {r['label']} | — | — | — | — | — | `{r['error']}` |")
            continue
        gb = r["size_bytes"] / (1024**3)
        lines.append(
            f"| {r['label']} | {gb:.1f}G | {r['load_sec']} | {r['gen_sec']} | "
            f"{r['completion_tokens']} | **{r['tok_per_sec']}** | `{r['preview'][:80]}` |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Live full-cache server keeps using local Q4_K_M on `:8000` (unchanged).",
        "- Q8/BF16 files from `unsloth/Qwen3.5-9B-GGUF` (same model family; speed test).",
        "- If run beside the 40-thread cache job, absolute tok/s is under contention; ratios still informative.",
        "",
    ]
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
