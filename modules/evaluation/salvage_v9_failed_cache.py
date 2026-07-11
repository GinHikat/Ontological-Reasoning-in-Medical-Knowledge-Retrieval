from __future__ import annotations

"""Re-parse truncated proposer failures offline, then optionally re-run verifier.

Does not call the proposer. Safe to run after full cache gen for stubs like doc 16.
By default only writes an analysis artifact; pass --write-cache to replace the stub
(requires a live local LLM for verifier unless --skip-verifier).
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.components.llm.client import LocalChatLLMClient, LocalLLMClientError
from modules.components.llm.document_lines import build_line_index
from modules.components.llm.response_parser import (
    PROPOSER_SCHEMA_HINT,
    VERIFIER_SCHEMA_HINT,
    ResponseParseError,
    parse_proposer_response,
    parse_verifier_response,
)
from modules.components.llm.schemas import ALLOWED_LLM_TYPES, AcceptedLLMCandidate
from modules.components.llm.span_aligner import align_proposals
from modules.components.postprocessing.llm_recall import document_sha256
from modules.evaluation.generate_v9_llm_cache import (
    PROPOSER_PROMPT_VERSION,
    VERIFIER_PROMPT_VERSION,
    _chat_with_optional_repair,
    _load_prompt,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--doc-id", type=str, default="16")
    p.add_argument("--input-dir", type=Path, default=PROJECT_ROOT / "v_dataset" / "var" / "test")
    p.add_argument("--cache-dir", type=Path, default=PROJECT_ROOT / "cache" / "v9_llm_recall")
    p.add_argument("--analysis-dir", type=Path, default=PROJECT_ROOT / "analysis")
    p.add_argument("--prompt-dir", type=Path, default=PROJECT_ROOT / "prompts")
    p.add_argument("--base-url", type=str, default="http://127.0.0.1:8000/v1")
    p.add_argument("--model", type=str, default="Qwen/Qwen3.5-9B")
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument("--skip-verifier", action="store_true")
    p.add_argument(
        "--write-cache",
        action="store_true",
        help="Replace cache stub (quarantines old file first). Needs verifier unless --skip-verifier.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    path = args.input_dir / f"{args.doc_id}.txt"
    text = path.read_text(encoding="utf-8")
    sha = document_sha256(text)
    cache_path = args.cache_dir / f"{sha}.json"
    if not cache_path.exists():
        raise FileNotFoundError(f"No cache for doc {args.doc_id}: {cache_path}")

    record = json.loads(cache_path.read_text(encoding="utf-8"))
    raw = record.get("raw_proposer_response") or ""
    if not raw.strip():
        raise RuntimeError(f"doc {args.doc_id} has empty raw_proposer_response; cannot salvage")

    proposals = parse_proposer_response(raw)
    indexed = build_line_index(text)
    alignments = align_proposals(indexed, proposals)
    aligned_only = [a for a in alignments if a.status == "aligned"]

    decisions: list[Any] = []
    raw_verifier = ""
    parse_failures: list[str] = list(record.get("parse_failures") or [])
    parse_failures.append(
        f"offline_truncated_salvage: recovered {len(proposals)} proposals "
        f"from raw_proposer_response ({len(aligned_only)} aligned)"
    )
    repair_used = bool(record.get("repair_used"))

    if aligned_only and not args.skip_verifier:
        verifier_prompt = _load_prompt(args.prompt_dir, VERIFIER_PROMPT_VERSION)
        client = LocalChatLLMClient(
            base_url=args.base_url,
            model=args.model,
            timeout=args.timeout,
            temperature=0.0,
            top_p=1.0,
            max_tokens=args.max_tokens,
            enable_thinking=False,
        )
        proposal_payload = [
            {
                "proposal_id": a.proposal_id,
                "line_id": a.line_id,
                "text": a.text,
                "type": a.type,
            }
            for a in aligned_only
        ]
        doc_block = indexed.as_prompt_block()
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
        raw_verifier, decisions, verifier_repair, fails = _chat_with_optional_repair(
            client,
            verifier_messages,
            parse_verifier_response,
            VERIFIER_SCHEMA_HINT,
            role="verifier",
        )
        parse_failures.extend(fails)
        repair_used = repair_used or verifier_repair

    decision_by_id = {d.proposal_id: d for d in decisions}
    accepted: list[AcceptedLLMCandidate] = []
    type_disagreements: list[dict[str, Any]] = []
    verifier_rejected: list[dict[str, Any]] = []
    verifier_missing: list[dict[str, Any]] = []

    if args.skip_verifier:
        status = "salvaged_awaiting_verifier"
    else:
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
            if text[a.start : a.end] != a.text:
                verifier_rejected.append({**a.to_dict(), "detail": "final_span_mismatch"})
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
        status = "ok" if not parse_failures else "completed_with_parse_issues"

    out = {
        "document_sha256": sha,
        "doc_id": args.doc_id,
        "model": record.get("model"),
        "prompt_versions": {
            "proposer": PROPOSER_PROMPT_VERSION,
            "verifier": VERIFIER_PROMPT_VERSION,
        },
        "generation_settings": record.get("generation_settings") or {},
        "raw_proposer_response": raw,
        "parsed_proposals": [p.to_dict() for p in proposals],
        "alignment_results": [a.to_dict() for a in alignments],
        "raw_verifier_response": raw_verifier,
        "verifier_decisions": [d.to_dict() for d in decisions],
        "final_accepted_candidates": [c.to_dict() for c in accepted],
        "diagnostics": {
            "status": status,
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
            "salvage": "offline_truncated_json",
        },
        "repair_used": repair_used,
        "parse_failures": parse_failures,
    }

    args.analysis_dir.mkdir(parents=True, exist_ok=True)
    analysis_path = args.analysis_dir / f"v9_doc{args.doc_id}_salvage_record.json"
    analysis_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {analysis_path}")
    print(
        f"doc={args.doc_id} proposals={len(proposals)} aligned={len(aligned_only)} "
        f"accepted={len(accepted)} status={status}"
    )

    if args.write_cache:
        if args.skip_verifier:
            raise SystemExit("Refusing --write-cache with --skip-verifier (incomplete for Phase B)")
        quarantine = args.cache_dir / "_quarantine"
        quarantine.mkdir(parents=True, exist_ok=True)
        dest = quarantine / f"{sha}.proposer_failed.json"
        if cache_path.exists():
            cache_path.replace(dest)
            print(f"Quarantined old stub -> {dest}")
        cache_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote cache {cache_path}")


if __name__ == "__main__":
    main()
