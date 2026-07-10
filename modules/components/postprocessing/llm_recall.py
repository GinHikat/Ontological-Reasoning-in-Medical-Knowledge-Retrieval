from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.components.llm.schemas import ALLOWED_LLM_TYPES, DEFAULT_MODEL
from modules.core.schemas import Document, EntityMention, Span


def document_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_path_for_sha(cache_dir: Path, sha: str) -> Path:
    return cache_dir / f"{sha}.json"


def load_cache_record(cache_dir: Path, sha: str) -> Optional[dict[str, Any]]:
    path = cache_path_for_sha(cache_dir, sha)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def spans_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return max(a_start, b_start) < min(a_end, b_end)


class LLMRecallPostProcessor(BaseMentionPostProcessor):
    """Additive merge of precomputed LLM-recalled entities (no live LLM calls).

    Loads cache/v9_llm_recall/<document_sha256>.json and appends only completely
    non-overlapping candidates. Never modifies existing pipeline mentions.
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        model_name: str = DEFAULT_MODEL,
        require_cache: bool = True,
    ):
        root = Path(__file__).resolve().parents[3]
        self.cache_dir = Path(cache_dir) if cache_dir else root / "cache" / "v9_llm_recall"
        self.model_name = model_name
        self.require_cache = require_cache

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        sha = document_sha256(document.text)
        record = load_cache_record(self.cache_dir, sha)

        diagnostics: dict[str, Any] = {
            "document_sha256": sha,
            "cache_hit": record is not None,
            "exact_span_duplicates_skipped": [],
            "overlap_rejected": [],
            "invalid_rejected": [],
            "type_disagreements_logged": [],
            "added": [],
        }

        if record is None:
            msg = (
                f"LLM recall cache miss for doc_id={document.doc_id} "
                f"sha256={sha} under {self.cache_dir}"
            )
            if self.require_cache:
                raise FileNotFoundError(msg)
            document.metadata.setdefault("llm_recall_diagnostics", diagnostics)
            document.metadata["llm_recall_diagnostics"]["error"] = msg
            return mentions

        existing = list(mentions)
        existing_spans = [
            (m.span.start, m.span.end, m.label, m.text)
            for m in existing
            if m.span.start is not None and m.span.end is not None
        ]

        prompt_version = (
            (record.get("prompt_versions") or {}).get("proposer")
            or (record.get("generation_settings") or {}).get("proposer_prompt_version")
            or "v9_llm_recall_proposer_v1"
        )
        model = record.get("model") or self.model_name

        for cand in record.get("final_accepted_candidates") or []:
            text = str(cand.get("text", ""))
            ent_type = str(cand.get("type", ""))
            start = cand.get("start")
            end = cand.get("end")
            line_id = str(cand.get("line_id", ""))
            proposer_type = str(cand.get("proposer_type", ent_type))
            verifier_type = str(cand.get("verifier_type", ent_type))

            reason = self._validate_candidate(
                document.text, text, ent_type, start, end, proposer_type, verifier_type
            )
            if reason is not None:
                diagnostics["invalid_rejected"].append(
                    {
                        "text": text,
                        "type": ent_type,
                        "start": start,
                        "end": end,
                        "reason": reason,
                    }
                )
                continue

            assert isinstance(start, int) and isinstance(end, int)

            # Exact same span → skip; never change existing type.
            exact_hit = False
            for e_start, e_end, e_label, e_text in existing_spans:
                if e_start == start and e_end == end:
                    exact_hit = True
                    entry = {
                        "text": text,
                        "llm_type": ent_type,
                        "existing_type": e_label,
                        "existing_text": e_text,
                        "start": start,
                        "end": end,
                        "reason": "EXACT_SPAN_DUPLICATE",
                    }
                    if e_label != ent_type:
                        entry["type_disagreement"] = True
                        diagnostics["type_disagreements_logged"].append(entry)
                    diagnostics["exact_span_duplicates_skipped"].append(entry)
                    break
            if exact_hit:
                continue

            # Any partial overlap → reject.
            overlap_hit = False
            for e_start, e_end, e_label, e_text in existing_spans:
                if e_start is None or e_end is None:
                    continue
                if spans_overlap(start, end, int(e_start), int(e_end)):
                    overlap_hit = True
                    diagnostics["overlap_rejected"].append(
                        {
                            "text": text,
                            "type": ent_type,
                            "start": start,
                            "end": end,
                            "existing_text": e_text,
                            "existing_type": e_label,
                            "existing_start": e_start,
                            "existing_end": e_end,
                            "reason": "OVERLAP_REJECTED",
                        }
                    )
                    break
            if overlap_hit:
                continue

            mention = EntityMention(
                text=text,
                label=ent_type,
                span=Span(start, end),
                confidence=1.0,
                source="llm_recall",
                metadata={
                    "llm_recall": True,
                    "model": model,
                    "prompt_version": prompt_version,
                    "verified": True,
                    "line_id": line_id,
                    "proposer_type": proposer_type,
                    "verifier_type": verifier_type,
                    "proposal_id": cand.get("proposal_id"),
                },
            )
            existing.append(mention)
            existing_spans.append((start, end, ent_type, text))
            diagnostics["added"].append(
                {
                    "text": text,
                    "type": ent_type,
                    "start": start,
                    "end": end,
                    "line_id": line_id,
                    "proposer_type": proposer_type,
                    "verifier_type": verifier_type,
                }
            )

        document.metadata["llm_recall_diagnostics"] = diagnostics
        return existing

    @staticmethod
    def _validate_candidate(
        original: str,
        text: str,
        ent_type: str,
        start: Any,
        end: Any,
        proposer_type: str,
        verifier_type: str,
    ) -> Optional[str]:
        if ent_type not in ALLOWED_LLM_TYPES:
            return f"disallowed_type:{ent_type}"
        if not isinstance(start, int) or not isinstance(end, int):
            return "non_int_offsets"
        if start < 0 or end < start or end > len(original):
            return "offset_out_of_range"
        if original[start:end] != text:
            return "text_offset_mismatch"
        if proposer_type != verifier_type:
            return "proposer_verifier_type_mismatch"
        if ent_type != proposer_type:
            return "stored_type_mismatch"
        return None
