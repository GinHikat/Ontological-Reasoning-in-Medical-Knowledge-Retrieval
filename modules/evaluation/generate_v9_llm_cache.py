from __future__ import annotations

"""Phase A: offline LLM candidate cache generation for v9_llm_recall.

Runs Qwen alone against raw competition text, writes validated exact-span
candidates under cache/v9_llm_recall/<document_sha256>.json, then exits so the
normal SapBERT/NER pipeline can run without GPU contention.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.components.llm.client import LocalChatLLMClient, LocalLLMClientError
from modules.components.llm.document_lines import build_line_index
from modules.components.llm.response_parser import (
    PROPOSER_SCHEMA_HINT,
    VERIFIER_SCHEMA_HINT,
    ResponseParseError,
    build_repair_messages,
    parse_proposer_response,
    parse_verifier_response,
)
from modules.components.llm.schemas import (
    ALLOWED_LLM_TYPES,
    DEFAULT_MODEL,
    PROPOSER_PROMPT_VERSION,
    VERIFIER_PROMPT_VERSION,
    AcceptedLLMCandidate,
    DocumentLLMCacheRecord,
)
from modules.components.llm.span_aligner import align_proposals
from modules.components.postprocessing.llm_recall import (
    cache_path_for_sha,
    document_sha256,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate offline v9 LLM recall cache.")
    p.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "v_dataset" / "var" / "test",
    )
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=PROJECT_ROOT / "cache" / "v9_llm_recall",
    )
    p.add_argument(
        "--prompt-dir",
        type=Path,
        default=PROJECT_ROOT / "prompts",
    )
    p.add_argument("--base-url", type=str, default="http://127.0.0.1:8000/v1")
    p.add_argument("--model", type=str, default=DEFAULT_MODEL)
    p.add_argument("--timeout", type=float, default=600.0)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--top-p", type=float, default=1.0)
    p.add_argument("--max-tokens", type=int, default=4096)
    p.add_argument(
        "--files",
        type=str,
        default=None,
        help="Comma-separated file stems to process (e.g. 3,13,20). Default: all.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if cache entry already exists.",
    )
    p.add_argument(
        "--skip-health-check",
        action="store_true",
        help="Do not require /models health check before starting.",
    )
    return p.parse_args()


def _load_prompt(prompt_dir: Path, name: str) -> str:
    path = prompt_dir / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def _select_files(input_dir: Path, files_arg: str | None) -> list[Path]:
    all_files = sorted(input_dir.glob("*.txt"), key=lambda p: int(p.stem) if p.stem.isdigit() else p.stem)
    if not files_arg:
        return all_files
    wanted = {x.strip() for x in files_arg.split(",") if x.strip()}
    selected = [p for p in all_files if p.stem in wanted]
    missing = wanted - {p.stem for p in selected}
    if missing:
        raise FileNotFoundError(f"Requested files not found: {sorted(missing)}")
    return selected


def _chat_with_optional_repair(
    client: LocalChatLLMClient,
    messages: list[dict[str, str]],
    parse_fn,
    schema_hint: str,
    role: str,
) -> tuple[str, Any, bool, list[str]]:
    """Return (raw_response, parsed, repair_used, failures)."""
    failures: list[str] = []
    raw = client.chat(messages)
    try:
        parsed = parse_fn(raw)
        return raw, parsed, False, failures
    except (ResponseParseError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"{role}_parse_error: {exc}")
        repair_messages = build_repair_messages(
            role=role,
            invalid_response=raw,
            schema_hint=schema_hint,
        )
        try:
            repaired_raw = client.chat(repair_messages)
        except LocalLLMClientError as repair_exc:
            failures.append(f"{role}_repair_connection_error: {repair_exc}")
            raise
        try:
            parsed = parse_fn(repaired_raw)
            return repaired_raw, parsed, True, failures
        except (ResponseParseError, json.JSONDecodeError, ValueError) as repair_parse_exc:
            failures.append(f"{role}_repair_parse_error: {repair_parse_exc}")
            # Preserve the best available raw text for cache diagnostics.
            err = ResponseParseError(
                f"{role} parse failed after one repair retry: {repair_parse_exc}"
            )
            err.raw_response = repaired_raw or raw  # type: ignore[attr-defined]
            raise err from repair_parse_exc


def process_document(
    *,
    file_path: Path,
    client: LocalChatLLMClient,
    proposer_prompt: str,
    verifier_prompt: str,
    cache_dir: Path,
    force: bool,
) -> DocumentLLMCacheRecord:
    text = file_path.read_text(encoding="utf-8")
    sha = document_sha256(text)
    out_path = cache_path_for_sha(cache_dir, sha)
    if out_path.exists() and not force:
        existing = DocumentLLMCacheRecord.from_dict(
            json.loads(out_path.read_text(encoding="utf-8"))
        )
        return existing

    indexed = build_line_index(text)
    doc_block = indexed.as_prompt_block()

    proposer_messages = [
        {"role": "system", "content": proposer_prompt},
        {
            "role": "user",
            "content": (
                "Extract entities from the following line-indexed clinical document.\n\n"
                f"{doc_block}"
            ),
        },
    ]

    parse_failures: list[str] = []
    repair_used = False
    raw_proposer = ""
    proposals = []
    try:
        raw_proposer, proposals, repair_used, fails = _chat_with_optional_repair(
            client,
            proposer_messages,
            parse_proposer_response,
            PROPOSER_SCHEMA_HINT,
            role="proposer",
        )
        parse_failures.extend(fails)
    except (ResponseParseError, LocalLLMClientError) as exc:
        parse_failures.append(str(exc))
        raw_proposer = raw_proposer or str(getattr(exc, "raw_response", "") or "")
        record = DocumentLLMCacheRecord(
            document_sha256=sha,
            doc_id=file_path.stem,
            model=client.model,
            prompt_versions={
                "proposer": PROPOSER_PROMPT_VERSION,
                "verifier": VERIFIER_PROMPT_VERSION,
            },
            generation_settings=client.generation_settings,
            raw_proposer_response=raw_proposer,
            parsed_proposals=[],
            alignment_results=[],
            raw_verifier_response="",
            verifier_decisions=[],
            final_accepted_candidates=[],
            diagnostics={
                "status": "proposer_failed",
                "error": str(exc),
                "n_lines": len(indexed.lines),
            },
            repair_used=repair_used,
            parse_failures=parse_failures,
        )
        out_path.write_text(
            json.dumps(record.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return record

    alignments = align_proposals(indexed, proposals)
    aligned_only = [a for a in alignments if a.status == "aligned"]

    raw_verifier = ""
    decisions = []
    verifier_repair = False
    if aligned_only:
        proposal_payload = [
            {
                "proposal_id": a.proposal_id,
                "line_id": a.line_id,
                "text": a.text,
                "type": a.type,
            }
            for a in aligned_only
        ]
        verifier_messages = [
            {"role": "system", "content": verifier_prompt},
            {
                "role": "user",
                "content": (
                    "Verify the following aligned proposals against the document.\n\n"
                    f"DOCUMENT:\n{doc_block}\n\n"
                    f"PROPOSALS:\n{json.dumps(proposal_payload, ensure_ascii=False, indent=2)}"
                ),
            },
        ]
        try:
            raw_verifier, decisions, verifier_repair, fails = _chat_with_optional_repair(
                client,
                verifier_messages,
                parse_verifier_response,
                VERIFIER_SCHEMA_HINT,
                role="verifier",
            )
            parse_failures.extend(fails)
            repair_used = repair_used or verifier_repair
        except (ResponseParseError, LocalLLMClientError) as exc:
            parse_failures.append(str(exc))
            decisions = []
            raw_verifier = raw_verifier or ""

    decision_by_id = {d.proposal_id: d for d in decisions}
    accepted: list[AcceptedLLMCandidate] = []
    type_disagreements: list[dict[str, Any]] = []
    verifier_rejected: list[dict[str, Any]] = []
    verifier_missing: list[dict[str, Any]] = []

    for a in aligned_only:
        d = decision_by_id.get(a.proposal_id)
        if d is None:
            verifier_missing.append(a.to_dict())
            continue
        if not d.accept:
            verifier_rejected.append(
                {**a.to_dict(), "verifier_type": d.type, "detail": d.detail}
            )
            continue
        verifier_type = d.type if d.type is not None else a.type
        if verifier_type != a.type:
            type_disagreements.append(
                {
                    **a.to_dict(),
                    "proposer_type": a.type,
                    "verifier_type": verifier_type,
                    "reason": "TYPE_DISAGREEMENT",
                }
            )
            continue
        if verifier_type not in ALLOWED_LLM_TYPES:
            verifier_rejected.append(
                {**a.to_dict(), "verifier_type": verifier_type, "detail": "bad_type"}
            )
            continue
        # Final absolute-span check.
        if text[a.start : a.end] != a.text:
            verifier_rejected.append(
                {**a.to_dict(), "detail": "final_span_mismatch"}
            )
            continue
        accepted.append(
            AcceptedLLMCandidate(
                text=a.text,
                type=a.type,
                start=a.start,
                end=a.end,
                line_id=a.line_id,
                proposer_type=a.type,
                verifier_type=verifier_type,
                proposal_id=a.proposal_id,
            )
        )

    diagnostics = {
        "status": "ok" if not parse_failures else "completed_with_parse_issues",
        "n_lines": len(indexed.lines),
        "n_raw_proposals": len(proposals),
        "n_aligned": len(aligned_only),
        "n_zero_match": sum(1 for a in alignments if a.status == "zero_match"),
        "n_multiple_match": sum(1 for a in alignments if a.status == "multiple_match"),
        "n_bad_line": sum(1 for a in alignments if a.status == "bad_line"),
        "n_verifier_accepted": len(accepted),
        "n_verifier_rejected": len(verifier_rejected),
        "n_type_disagreements": len(type_disagreements),
        "n_verifier_missing": len(verifier_missing),
        "type_disagreements": type_disagreements,
        "verifier_rejected": verifier_rejected,
        "verifier_missing": verifier_missing,
    }

    record = DocumentLLMCacheRecord(
        document_sha256=sha,
        doc_id=file_path.stem,
        model=client.model,
        prompt_versions={
            "proposer": PROPOSER_PROMPT_VERSION,
            "verifier": VERIFIER_PROMPT_VERSION,
        },
        generation_settings={
            **client.generation_settings,
            "proposer_prompt_version": PROPOSER_PROMPT_VERSION,
            "verifier_prompt_version": VERIFIER_PROMPT_VERSION,
        },
        raw_proposer_response=raw_proposer,
        parsed_proposals=[p.to_dict() for p in proposals],
        alignment_results=[a.to_dict() for a in alignments],
        raw_verifier_response=raw_verifier,
        verifier_decisions=[d.to_dict() for d in decisions],
        final_accepted_candidates=[c.to_dict() for c in accepted],
        diagnostics=diagnostics,
        repair_used=repair_used,
        parse_failures=parse_failures,
    )
    out_path.write_text(
        json.dumps(record.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record


def main() -> None:
    args = parse_args()
    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    proposer_prompt = _load_prompt(args.prompt_dir, PROPOSER_PROMPT_VERSION)
    verifier_prompt = _load_prompt(args.prompt_dir, VERIFIER_PROMPT_VERSION)

    client = LocalChatLLMClient(
        base_url=args.base_url,
        model=args.model,
        timeout=args.timeout,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        enable_thinking=False,
    )

    if not args.skip_health_check:
        try:
            health = client.health_check()
            print(f"Local LLM healthy: {json.dumps(health, ensure_ascii=False)[:300]}")
        except LocalLLMClientError as exc:
            raise SystemExit(
                f"Local LLM health check failed: {exc}\n"
                "Start vLLM first, e.g.:\n"
                "  vllm serve Qwen/Qwen3.5-9B --host 127.0.0.1 --port 8000 "
                "--max-model-len 16384 --language-model-only --reasoning-parser qwen3"
            ) from exc

    files = _select_files(args.input_dir, args.files)
    print(f"Generating LLM cache for {len(files)} documents -> {args.cache_dir}")

    summary = {
        "documents": 0,
        "cache_writes": 0,
        "raw_proposals": 0,
        "aligned": 0,
        "final_accepted": 0,
        "parse_failure_docs": 0,
    }

    for path in tqdm(files, desc="v9 LLM cache"):
        record = process_document(
            file_path=path,
            client=client,
            proposer_prompt=proposer_prompt,
            verifier_prompt=verifier_prompt,
            cache_dir=args.cache_dir,
            force=args.force,
        )
        summary["documents"] += 1
        summary["cache_writes"] += 1
        summary["raw_proposals"] += len(record.parsed_proposals)
        summary["aligned"] += sum(
            1 for a in record.alignment_results if a.get("status") == "aligned"
        )
        summary["final_accepted"] += len(record.final_accepted_candidates)
        if record.parse_failures:
            summary["parse_failure_docs"] += 1

    summary_path = PROJECT_ROOT / "analysis" / "v9_llm_cache_generation_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
