"""Low-call OpenRouter reduced schema teacher (EXTERNAL_API_DIAGNOSTIC_ONLY).

Architecture:
  document → one primary extractor → exact-span align → local ontology retrieval
  → deterministic candidate accept → batch ambiguous candidate judge (largest model)
  → deterministic risk → conditional document judge (largest model) → final JSON
"""

from __future__ import annotations

import csv
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from modules.core.config import ProjectPaths
from modules.external.deterministic_candidate_selector import (
    BatchItem,
    CandidateThresholds,
    apply_deterministic_selection,
)
from modules.external.document_risk import RiskResult, score_document_risk
from modules.external.exact_span_aligner import AlignmentStats, align_entities
from modules.external.ontology_retrieval import LocalOntologyRetriever
from modules.external.openrouter_client import (
    ChatResult,
    OpenRouterClient,
    atomic_write_json,
    load_dotenv_file,
)
from modules.external.rate_limit_scheduler import RateLimitConfig, RateLimitScheduler
from modules.external.schema_gates import apply_schema_gates, to_competition_entity

ROOT = ProjectPaths().root
SCHEMA_DIR = ROOT / "modules" / "external" / "schemas"
PROMPT_SCHEMA = (
    ROOT / "modules" / "external" / "prompts" / "competition_schema.md"
).read_text(encoding="utf-8")

DEFAULT_EXTRACTOR = "tencent/hy3:free"
DEFAULT_JUDGE = "nvidia/nemotron-3-ultra-550b-a55b:free"
PROMPT_VERSION = "reduced_extractor_v1"
SCHEMA_VERSION = "reduced_extraction_v1"
CAND_JUDGE_PROMPT_VERSION = "reduced_cand_judge_v1"
DOC_JUDGE_PROMPT_VERSION = "reduced_doc_judge_v1"


def load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def env_flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default


def env_float(name: str, default: float | None = None) -> float | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return float(raw)


def read_document(test_dir: Path, doc_id: str) -> str:
    return (test_dir / f"{doc_id}.txt").read_text(encoding="utf-8")


def list_all_doc_ids(test_dir: Path) -> list[str]:
    return sorted(
        (p.stem for p in test_dir.glob("*.txt") if p.stem.isdigit()),
        key=lambda x: int(x),
    )


def extraction_system_prompt() -> str:
    return (
        "You are the primary clinical entity extractor for a Vietnamese medical "
        "competition schema.\n"
        "Return a complete final entity list for the document.\n"
        "Do not invent ontology IDs.\n"
        "Do not explain. Do not write long reasoning.\n\n"
        f"{PROMPT_SCHEMA}\n\n"
        "Internal checklist before returning:\n"
        "1. Find all valid entities belonging to the five output classes.\n"
        "2. Omit procedures, interventions, devices, headings, demographics, "
        "anatomy alone and generic status.\n"
        "3. Use minimal meaningful symptom spans.\n"
        "4. Use diagnosis spans with clinically meaningful specificity.\n"
        "5. Use maximal contiguous medication spans.\n"
        "6. Separate test names from test results.\n"
        "7. Remove leading negation words from entity spans.\n"
        "8. Apply assertions entity by entity.\n"
        "9. Keep repeated mentions at different offsets.\n"
        "10. Perform a final omission check before returning.\n\n"
        f"prompt_version={PROMPT_VERSION}; schema_version={SCHEMA_VERSION}\n"
        "Return ONLY structured JSON matching the schema."
    )


def extraction_user_prompt_single(document: str, doc_id: str) -> str:
    return (
        f"Document ID: {doc_id}\n"
        "Extract all valid entities from the original document below.\n\n"
        "<<<DOCUMENT>>>\n"
        f"{document}\n"
        "<<<END_DOCUMENT>>>"
    )


def extraction_user_prompt_batch(docs: list[tuple[str, str]]) -> str:
    parts = [
        "Extract entities for each document separately.",
        "Never assign an entity from one document to another.",
        "Return one entity list per document_id.\n",
    ]
    for doc_id, document in docs:
        parts.append(f"=== document_id={doc_id} ===")
        parts.append("<<<DOCUMENT>>>")
        parts.append(document)
        parts.append("<<<END_DOCUMENT>>>\n")
    return "\n".join(parts)


def group_documents_for_microbatch(
    doc_ids: list[str],
    documents: dict[str, str],
    microbatch_size: int = 1,
    alone_char_threshold: int = 12000,
) -> list[list[str]]:
    """Deterministic pairing by character count. Max 2 docs per request."""
    size = max(1, min(2, int(microbatch_size)))
    if size == 1:
        return [[d] for d in doc_ids]

    alone: list[str] = []
    pool: list[str] = []
    for d in doc_ids:
        if len(documents[d]) > alone_char_threshold:
            alone.append(d)
        else:
            pool.append(d)
    # shortest-first pairing for stability
    pool_sorted = sorted(pool, key=lambda x: (len(documents[x]), int(x)))
    batches: list[list[str]] = [[d] for d in alone]
    i = 0
    while i < len(pool_sorted):
        if i + 1 < len(pool_sorted):
            batches.append([pool_sorted[i], pool_sorted[i + 1]])
            i += 2
        else:
            batches.append([pool_sorted[i]])
            i += 1
    # stable order by first doc id
    batches.sort(key=lambda b: int(b[0]))
    return batches


def _trim_anchor(s: str, limit: int = 40) -> str:
    s = (s or "").strip()
    return s[:limit]


def competition_sort_key(e: dict[str, Any]) -> tuple:
    pos = e.get("position") or [e.get("start", 0), e.get("end", 0)]
    return (int(pos[0]), int(pos[1]), str(e.get("type") or ""), str(e.get("text") or ""))


def sanitize_final(
    document: str,
    entities: list[dict[str, Any]],
    allowed_ids: dict[tuple[str, int, int, str], set[str]] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in entities:
        pos = e.get("position")
        if not pos:
            start, end = e.get("start"), e.get("end")
            if not isinstance(start, int) or not isinstance(end, int):
                continue
            pos = [start, end]
        start, end = int(pos[0]), int(pos[1])
        if not (0 <= start < end <= len(document)):
            continue
        text = document[start:end]
        item: dict[str, Any] = {
            "text": text,
            "type": e["type"],
            "assertions": sorted(set(e.get("assertions") or [])),
            "position": [start, end],
        }
        if item["type"] in {"CHẨN_ĐOÁN", "THUỐC"}:
            key = (text, start, end, item["type"])
            allowed = (allowed_ids or {}).get(key)
            cands = [str(c) for c in (e.get("candidates") or [])]
            if allowed is not None:
                cands = [c for c in cands if c in allowed]
            item["candidates"] = cands
        # strip internal keys
        out.append(item)
    out.sort(key=competition_sort_key)
    return out


@dataclass
class ReducedConfig:
    output_dir: Path
    cache_root: Path
    test_dir: Path
    extractor_model: str = DEFAULT_EXTRACTOR
    judge_model: str = DEFAULT_JUDGE
    judge_fallback: str | None = None
    microbatch_size: int = 1
    alone_char_threshold: int = 12000
    candidate_batch_size: int = 15
    use_embeddings: bool = False
    enable_risk_review: bool = True
    enable_candidate_judge: bool = True
    document_workers: int = 1
    budget_usd: float | None = None


@dataclass
class RunStats:
    api_requests: int = 0
    cached_hits: int = 0
    retries: int = 0
    rate_limits_429: int = 0
    parse_failures: int = 0
    alignment_failures: int = 0
    extraction_requests: int = 0
    candidate_batches: int = 0
    documents_judged: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    wall_clock_seconds: float = 0.0
    judged_doc_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "api_requests": self.api_requests,
            "cached_hits": self.cached_hits,
            "retries": self.retries,
            "rate_limits_429": self.rate_limits_429,
            "parse_failures": self.parse_failures,
            "alignment_failures": self.alignment_failures,
            "extraction_requests": self.extraction_requests,
            "candidate_batches": self.candidate_batches,
            "documents_judged": self.documents_judged,
            "judged_doc_ids": self.judged_doc_ids,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "wall_clock_seconds": round(self.wall_clock_seconds, 3),
        }


class ReducedTeacherPipeline:
    def __init__(self, client: OpenRouterClient, config: ReducedConfig):
        self.client = client
        self.config = config
        self.scheduler = RateLimitScheduler(RateLimitConfig.from_env())
        self.retriever = LocalOntologyRetriever(use_embeddings=config.use_embeddings)
        self.thresholds = CandidateThresholds.from_env()
        self.extraction_schema = load_schema("reduced_extraction.schema.json")
        self.extraction_batch_schema = load_schema(
            "reduced_extraction_batch.schema.json"
        )
        self.cand_judge_schema = load_schema("reduced_candidate_judge.schema.json")
        self.doc_judge_schema = load_schema("reduced_document_judge.schema.json")
        self.stats = RunStats()
        self.risk_rows: list[dict[str, Any]] = []
        self.alignment_stats = AlignmentStats()
        self._entity_counts: list[int] = []
        self._pending_ambiguous: list[BatchItem] = []
        self._doc_states: dict[str, dict[str, Any]] = {}
        self.cache_dirs = {
            "extraction": config.cache_root / "extraction",
            "candidate_judge": config.cache_root / "candidate_judge",
            "document_judge": config.cache_root / "document_judge",
        }
        for p in self.cache_dirs.values():
            p.mkdir(parents=True, exist_ok=True)
        for sub in (
            "raw_extraction",
            "aligned",
            "local_candidates",
            "candidate_batches",
            "judged",
            "final",
            "traces",
        ):
            (config.output_dir / sub).mkdir(parents=True, exist_ok=True)
        self._validate_models()

    def _validate_models(self) -> None:
        catalog = {str(m.get("id")): m for m in self.client.list_models()}
        if self.config.extractor_model not in catalog:
            raise RuntimeError(
                f"Reduced extractor model unavailable: {self.config.extractor_model}"
            )
        if self.config.judge_model not in catalog:
            if self.config.judge_fallback and self.config.judge_fallback in catalog:
                raise RuntimeError(
                    f"Configured judge {self.config.judge_model} unavailable; "
                    f"explicit fallback {self.config.judge_fallback} exists but "
                    "automatic fallback is disabled unless OPENROUTER_REDUCED_ALLOW_JUDGE_FALLBACK=true"
                )
            if (
                self.config.judge_fallback
                and env_flag("OPENROUTER_REDUCED_ALLOW_JUDGE_FALLBACK", False)
                and self.config.judge_fallback in catalog
            ):
                self.config.judge_model = self.config.judge_fallback
            else:
                raise RuntimeError(
                    "Largest judge model unavailable: "
                    f"{self.config.judge_model}. Refusing silent smaller fallback."
                )
        self._model_meta = {
            mid: catalog[mid]
            for mid in {self.config.extractor_model, self.config.judge_model}
            if mid in catalog
        }

    def _chat(
        self,
        *,
        stage: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        schema_name: str,
        label: str,
    ) -> ChatResult:
        old = self.client.cache_dir
        self.client.cache_dir = self.cache_dirs[stage]
        self.scheduler.acquire(model)
        try:
            result = self.client.chat_structured(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                schema_name=schema_name,
                temperature=0.0,
                label=label,
                model_meta=self._model_meta.get(model),
            )
        except Exception:
            self.scheduler.release(model)
            raise
        self.scheduler.release(model)
        if result.cached:
            self.stats.cached_hits += 1
        else:
            self.stats.api_requests += 1
        self.stats.input_tokens += int(result.input_tokens or 0)
        self.stats.output_tokens += int(result.output_tokens or 0)
        if result.validation_status not in {"ok", "healed_json_extract", "cached"}:
            self.stats.parse_failures += 1
        return result

    def extract_batch(self, doc_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        docs = {
            d: read_document(self.config.test_dir, d) for d in doc_ids
        }
        self.stats.extraction_requests += 1
        if len(doc_ids) == 1:
            doc_id = doc_ids[0]
            chat = self._chat(
                stage="extraction",
                model=self.config.extractor_model,
                system_prompt=extraction_system_prompt(),
                user_prompt=extraction_user_prompt_single(docs[doc_id], doc_id),
                response_schema=self.extraction_schema,
                schema_name="reduced_extraction",
                label=f"extract:{doc_id}",
            )
            parsed = chat.parsed_response if isinstance(chat.parsed_response, dict) else {}
            entities = list(parsed.get("entities") or [])
            atomic_write_json(
                self.config.output_dir / "raw_extraction" / f"{doc_id}.json",
                {
                    "doc_id": doc_id,
                    "model": self.config.extractor_model,
                    "request_hash": chat.request_hash,
                    "validation_status": chat.validation_status,
                    "cached": chat.cached,
                    "entities": entities,
                },
            )
            return {doc_id: entities}

        chat = self._chat(
            stage="extraction",
            model=self.config.extractor_model,
            system_prompt=extraction_system_prompt(),
            user_prompt=extraction_user_prompt_batch(list(docs.items())),
            response_schema=self.extraction_batch_schema,
            schema_name="reduced_extraction_batch",
            label=f"extract_batch:{','.join(doc_ids)}",
        )
        parsed = chat.parsed_response if isinstance(chat.parsed_response, dict) else {}
        by_doc: dict[str, list[dict[str, Any]]] = {d: [] for d in doc_ids}
        for block in parsed.get("documents") or []:
            did = str(block.get("document_id") or "")
            if did in by_doc:
                by_doc[did] = list(block.get("entities") or [])
        for doc_id, entities in by_doc.items():
            atomic_write_json(
                self.config.output_dir / "raw_extraction" / f"{doc_id}.json",
                {
                    "doc_id": doc_id,
                    "model": self.config.extractor_model,
                    "batch": doc_ids,
                    "request_hash": chat.request_hash,
                    "validation_status": chat.validation_status,
                    "cached": chat.cached,
                    "entities": entities,
                },
            )
        return by_doc

    def align_and_gate(
        self, doc_id: str, document: str, entities: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[str, int], str]:
        cleaned = []
        for e in entities:
            item = dict(e)
            item["left_anchor"] = _trim_anchor(str(item.get("left_anchor") or ""))
            item["right_anchor"] = _trim_anchor(str(item.get("right_anchor") or ""))
            cleaned.append(item)
        local_stats = AlignmentStats()
        aligned, local_stats = align_entities(document, cleaned, local_stats)
        for k, v in local_stats.as_dict().items():
            setattr(
                self.alignment_stats,
                k,
                getattr(self.alignment_stats, k) + v,
            )
        fail = (
            local_stats.rejected_ambiguous
            + local_stats.rejected_not_found
            + local_stats.rejected_empty
        )
        self.stats.alignment_failures += fail
        gates = apply_schema_gates(document, aligned)
        atomic_write_json(
            self.config.output_dir / "aligned" / f"{doc_id}.json",
            {
                "doc_id": doc_id,
                "entities": gates.kept,
                "rejected": gates.rejected,
                "alignment": local_stats.as_dict(),
            },
        )
        return gates.kept, local_stats.as_dict(), "ok"

    def attach_local_candidates(
        self, doc_id: str, entities: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[tuple[str, int, int, str], set[str]]]:
        payload: dict[str, Any] = {"doc_id": doc_id, "entities": []}
        enriched: list[dict[str, Any]] = []
        allowed: dict[tuple[str, int, int, str], set[str]] = {}
        for i, ent in enumerate(entities):
            item = dict(ent)
            item["entity_id"] = f"{doc_id}:e{i}"
            cands: list[dict[str, Any]] = []
            if ent["type"] == "CHẨN_ĐOÁN":
                cands = [c.as_dict() for c in self.retriever.retrieve_icd(ent["text"])]
            elif ent["type"] == "THUỐC":
                cands = [
                    c.as_dict() for c in self.retriever.retrieve_rxnorm(ent["text"])
                ]
            item["local_candidates"] = cands
            key = (ent["text"], ent["start"], ent["end"], ent["type"])
            allowed[key] = {c["id"] for c in cands}
            payload["entities"].append(
                {
                    "entity_id": item["entity_id"],
                    "text": ent["text"],
                    "type": ent["type"],
                    "position": [ent["start"], ent["end"]],
                    "candidates": cands,
                }
            )
            enriched.append(item)
        atomic_write_json(
            self.config.output_dir / "local_candidates" / f"{doc_id}.json", payload
        )
        return enriched, allowed

    def flush_candidate_batches(self, force: bool = False) -> dict[str, list[str]]:
        """Judge ambiguous ontology items in cross-document batches."""
        selected: dict[str, list[str]] = {}
        if not self.config.enable_candidate_judge:
            self._pending_ambiguous.clear()
            return selected
        while self._pending_ambiguous and (
            force or len(self._pending_ambiguous) >= self.config.candidate_batch_size
        ):
            batch = self._pending_ambiguous[: self.config.candidate_batch_size]
            del self._pending_ambiguous[: self.config.candidate_batch_size]
            batch_id = f"batch_{self.stats.candidate_batches:04d}"
            self.stats.candidate_batches += 1
            items = []
            for it in batch:
                items.append(
                    {
                        "item_id": it.item_id,
                        "document_id": it.document_id,
                        "entity_text": it.entity_text,
                        "entity_type": it.entity_type,
                        "context": it.context,
                        "candidates": [
                            {
                                "id": c.get("id"),
                                "canonical_term": c.get("canonical_term"),
                                "aliases": (c.get("aliases") or [])[:5],
                                "ontology_type": c.get("ontology_type"),
                                "lexical_score": c.get("lexical_score"),
                                "embedding_score": c.get("embedding_score"),
                                "combined_score": c.get("combined_score"),
                            }
                            for c in it.candidates[:20]
                        ],
                    }
                )
            system = (
                "You are the ontology candidate judge.\n"
                "Select IDs ONLY from each item's supplied candidate list.\n"
                "Diagnosis (CHẨN_ĐOÁN): zero, one, or multiple ICD codes when justified.\n"
                "Drug (THUỐC): zero or one RxCUI. Never invent IDs.\n"
                "Do not explain.\n"
                f"prompt_version={CAND_JUDGE_PROMPT_VERSION}"
            )
            user = "Ambiguous ontology items (JSON):\n" + json.dumps(
                items, ensure_ascii=False
            )
            chat = self._chat(
                stage="candidate_judge",
                model=self.config.judge_model,
                system_prompt=system,
                user_prompt=user,
                response_schema=self.cand_judge_schema,
                schema_name="reduced_candidate_judge",
                label=f"cand_judge:{batch_id}",
            )
            parsed = chat.parsed_response if isinstance(chat.parsed_response, dict) else {}
            allowed_by_item = {
                it.item_id: {str(c.get("id")) for c in it.candidates} for it in batch
            }
            batch_selected: dict[str, list[str]] = {}
            for sel in parsed.get("selections") or []:
                iid = str(sel.get("item_id") or "")
                allowed = allowed_by_item.get(iid, set())
                ids = [str(x) for x in (sel.get("selected_ids") or []) if str(x) in allowed]
                # drugs: at most one
                et = next((it.entity_type for it in batch if it.item_id == iid), "")
                if et == "THUỐC":
                    ids = ids[:1]
                batch_selected[iid] = ids
                selected[iid] = ids
            atomic_write_json(
                self.config.output_dir / "candidate_batches" / f"{batch_id}.json",
                {
                    "batch_id": batch_id,
                    "model": self.config.judge_model,
                    "request_hash": chat.request_hash,
                    "validation_status": chat.validation_status,
                    "cached": chat.cached,
                    "n_items": len(items),
                    "items": items,
                    "selections": batch_selected,
                },
            )
        return selected

    def document_judge(
        self,
        doc_id: str,
        document: str,
        entities: list[dict[str, Any]],
        risk: RiskResult,
        allowed_ids: dict[tuple[str, int, int, str], set[str]],
    ) -> list[dict[str, Any]]:
        self.stats.documents_judged += 1
        self.stats.judged_doc_ids.append(doc_id)
        # attach candidate menus for diagnosis/drug
        menus = []
        for e in entities:
            if e.get("type") not in {"CHẨN_ĐOÁN", "THUỐC"}:
                continue
            key = (e["text"], e["position"][0], e["position"][1], e["type"])
            menus.append(
                {
                    "text": e["text"],
                    "type": e["type"],
                    "position": e["position"],
                    "allowed_ids": sorted(allowed_ids.get(key, set())),
                    "current_candidates": e.get("candidates") or [],
                }
            )
        compact = []
        for e in entities:
            item = {
                "text": e["text"],
                "type": e["type"],
                "assertions": e.get("assertions") or [],
                "start": e["position"][0],
                "end": e["position"][1],
            }
            if e.get("type") in {"CHẨN_ĐOÁN", "THUỐC"}:
                item["candidates"] = e.get("candidates") or []
            compact.append(item)
        system = (
            "You are the largest-model document judge for Vietnamese clinical NER.\n"
            "Review and correct the entity list in ONE response.\n"
            "Perform: false-positive removal, missed-entity recovery, type/boundary/"
            "assertion correction, and candidate correction using ONLY supplied IDs.\n"
            "You may leave the input unchanged.\n"
            "Do not explain at length. Return short issue tags.\n\n"
            f"{PROMPT_SCHEMA}\n"
            f"prompt_version={DOC_JUDGE_PROMPT_VERSION}"
        )
        user = (
            f"Document ID: {doc_id}\n"
            f"Risk score: {risk.risk_score}\n"
            f"Risk reasons: {risk.risk_reasons}\n\n"
            f"<<<DOCUMENT>>>\n{document}\n<<<END_DOCUMENT>>>\n\n"
            f"Current entities:\n{json.dumps(compact, ensure_ascii=False)}\n\n"
            f"Ontology menus:\n{json.dumps(menus, ensure_ascii=False)}"
        )
        chat = self._chat(
            stage="document_judge",
            model=self.config.judge_model,
            system_prompt=system,
            user_prompt=user,
            response_schema=self.doc_judge_schema,
            schema_name="reduced_document_judge",
            label=f"doc_judge:{doc_id}",
        )
        parsed = chat.parsed_response if isinstance(chat.parsed_response, dict) else {}
        raw_ents = list(parsed.get("entities") or [])
        aligned, _ = align_entities(document, raw_ents, AlignmentStats())
        # map to competition shape + filter invented IDs
        rebuilt = []
        for e in aligned:
            item = {
                "text": e["text"],
                "type": e["type"],
                "assertions": list(e.get("assertions") or []),
                "position": [e["start"], e["end"]],
                "start": e["start"],
                "end": e["end"],
            }
            if e["type"] in {"CHẨN_ĐOÁN", "THUỐC"}:
                key = (e["text"], e["start"], e["end"], e["type"])
                allowed = allowed_ids.get(key, set())
                # if span new, try local retrieval quickly
                if not allowed and e["type"] == "CHẨN_ĐOÁN":
                    allowed = {
                        c.id for c in self.retriever.retrieve_icd(e["text"])
                    }
                    allowed_ids[key] = allowed
                if not allowed and e["type"] == "THUỐC":
                    allowed = {
                        c.id for c in self.retriever.retrieve_rxnorm(e["text"])
                    }
                    allowed_ids[key] = allowed
                cands = [str(x) for x in (e.get("candidates") or []) if str(x) in allowed]
                if e["type"] == "THUỐC":
                    cands = cands[:1]
                item["candidates"] = cands
            rebuilt.append(item)
        gates = apply_schema_gates(document, rebuilt)
        final = sanitize_final(document, gates.kept, allowed_ids)
        atomic_write_json(
            self.config.output_dir / "judged" / f"{doc_id}.json",
            {
                "doc_id": doc_id,
                "model": self.config.judge_model,
                "request_hash": chat.request_hash,
                "validation_status": chat.validation_status,
                "cached": chat.cached,
                "issue_tags": parsed.get("issue_tags") or [],
                "risk": risk.as_dict(),
                "entities": final,
            },
        )
        return final

    def process_extraction_phase(self, doc_ids: list[str]) -> None:
        documents = {d: read_document(self.config.test_dir, d) for d in doc_ids}
        batches = group_documents_for_microbatch(
            doc_ids,
            documents,
            microbatch_size=self.config.microbatch_size,
            alone_char_threshold=self.config.alone_char_threshold,
        )
        for batch in batches:
            # skip if all finals exist
            if all(
                (self.config.output_dir / "final" / f"{d}.json").exists() for d in batch
            ):
                continue
            raw_by_doc = self.extract_batch(batch)
            for doc_id in batch:
                document = documents[doc_id]
                kept, align_stats, _ = self.align_and_gate(
                    doc_id, document, raw_by_doc.get(doc_id) or []
                )
                enriched, allowed = self.attach_local_candidates(doc_id, kept)
                state = apply_deterministic_selection(
                    doc_id, document, enriched, self.thresholds
                )
                self._pending_ambiguous.extend(state.ambiguous)
                # convert to competition entities (keep entity_id for batch judge map)
                comps = []
                for e in state.entities:
                    c = to_competition_entity(e)
                    if e.get("type") in {"CHẨN_ĐOÁN", "THUỐC"}:
                        c["candidates"] = list(e.get("candidates") or [])
                        if e.get("entity_id"):
                            c["entity_id"] = e["entity_id"]
                    comps.append(c)
                self._entity_counts.append(len(comps))
                self._doc_states[doc_id] = {
                    "document": document,
                    "entities": comps,
                    "allowed_ids": allowed,
                    "align_stats": align_stats,
                    "unresolved": state.unresolved_count,
                    "raw_status": "ok",
                }
                # opportunistic flush
                judged_map = self.flush_candidate_batches(force=False)
                if judged_map:
                    self._apply_candidate_selections(judged_map)

    def _apply_candidate_selections(self, selected: dict[str, list[str]]) -> None:
        for doc_id, st in self._doc_states.items():
            loc_path = self.config.output_dir / "local_candidates" / f"{doc_id}.json"
            id_by_span: dict[tuple[str, int, int, str], str] = {}
            if loc_path.exists():
                loc = json.loads(loc_path.read_text(encoding="utf-8"))
                for ent in loc.get("entities") or []:
                    pos = ent["position"]
                    id_by_span[(ent["text"], pos[0], pos[1], ent["type"])] = ent[
                        "entity_id"
                    ]
            applied = 0
            for e in st["entities"]:
                if e["type"] not in {"CHẨN_ĐOÁN", "THUỐC"}:
                    continue
                eid = e.get("entity_id")
                if not eid:
                    key = (e["text"], e["position"][0], e["position"][1], e["type"])
                    eid = id_by_span.get(key)
                if eid and eid in selected:
                    e["candidates"] = selected[eid]
                    e["entity_id"] = eid
                    applied += 1
            if applied:
                st["unresolved"] = max(0, int(st.get("unresolved") or 0) - applied)

    def process_judge_phase(self, doc_ids: list[str]) -> None:
        # flush remaining ambiguous
        judged_map = self.flush_candidate_batches(force=True)
        if judged_map:
            self._apply_candidate_selections(judged_map)

        for doc_id in doc_ids:
            final_path = self.config.output_dir / "final" / f"{doc_id}.json"
            if final_path.exists() and doc_id not in self._doc_states:
                continue
            if doc_id not in self._doc_states:
                # resume path: rebuild minimal state from aligned + local candidates
                document = read_document(self.config.test_dir, doc_id)
                aligned_path = self.config.output_dir / "aligned" / f"{doc_id}.json"
                if not aligned_path.exists():
                    continue
                aligned = json.loads(aligned_path.read_text(encoding="utf-8"))
                ents = aligned.get("entities") or []
                enriched, allowed = self.attach_local_candidates(doc_id, ents)
                state = apply_deterministic_selection(
                    doc_id, document, enriched, self.thresholds
                )
                comps = []
                for e in state.entities:
                    c = to_competition_entity(e)
                    if e.get("type") in {"CHẨN_ĐOÁN", "THUỐC"}:
                        c["candidates"] = list(e.get("candidates") or [])
                    comps.append(c)
                self._doc_states[doc_id] = {
                    "document": document,
                    "entities": comps,
                    "allowed_ids": allowed,
                    "align_stats": aligned.get("alignment") or {},
                    "unresolved": state.unresolved_count,
                    "raw_status": "ok",
                }
                self._pending_ambiguous.extend(state.ambiguous)

        # flush again after resume rebuild
        judged_map = self.flush_candidate_batches(force=True)
        if judged_map:
            self._apply_candidate_selections(judged_map)

        for doc_id in doc_ids:
            st = self._doc_states.get(doc_id)
            if not st:
                continue
            document = st["document"]
            entities = st["entities"]
            risk = score_document_risk(
                doc_id,
                document,
                entities,
                alignment_stats=st.get("align_stats"),
                parse_status=st.get("raw_status"),
                unresolved_candidates=int(st.get("unresolved") or 0),
                corpus_entity_counts=list(self._entity_counts) or None,
            )
            self.risk_rows.append(risk.as_dict())
            final = sanitize_final(document, entities, st["allowed_ids"])
            if (
                self.config.enable_risk_review
                and risk.requires_judge
                and env_flag("OPENROUTER_REDUCED_ENABLE_RISK_REVIEW", True)
            ):
                final = self.document_judge(
                    doc_id, document, final, risk, st["allowed_ids"]
                )
            else:
                atomic_write_json(
                    self.config.output_dir / "judged" / f"{doc_id}.json",
                    {
                        "doc_id": doc_id,
                        "skipped_judge": True,
                        "risk": risk.as_dict(),
                        "entities": final,
                    },
                )
            atomic_write_json(self.config.output_dir / "final" / f"{doc_id}.json", final)
            atomic_write_json(
                self.config.output_dir / "traces" / f"{doc_id}.json",
                {
                    "doc_id": doc_id,
                    "risk": risk.as_dict(),
                    "n_entities": len(final),
                    "extractor_model": self.config.extractor_model,
                    "judge_model": self.config.judge_model,
                },
            )

    def run(self, doc_ids: list[str]) -> dict[str, Any]:
        t0 = time.time()
        write_compliance(self.config.output_dir)
        # resume: drop docs already finalized unless force — default resume keeps finals
        pending = [
            d
            for d in doc_ids
            if not (self.config.output_dir / "final" / f"{d}.json").exists()
        ]
        # still need risk tsv for all; process pending extraction then judge all missing
        if pending:
            self.process_extraction_phase(pending)
        # For docs with final already, skip. For pending, judge phase writes final.
        need_judge = [
            d
            for d in doc_ids
            if not (self.config.output_dir / "final" / f"{d}.json").exists()
            or d in self._doc_states
        ]
        # Only run judge phase for docs we have state for / missing final
        targets = [d for d in doc_ids if d in self._doc_states] or pending
        if targets:
            self.process_judge_phase(targets)
        self.stats.wall_clock_seconds = time.time() - t0
        self.stats.retries = self.scheduler.stats.retries
        self.stats.rate_limits_429 = self.scheduler.stats.rate_limit_hits
        # merge client usage if available
        usage = self.client.usage_summary()
        # prefer client uncached count when larger (scheduler wraps each call)
        if usage.get("uncached_requests", 0) > self.stats.api_requests:
            self.stats.api_requests = int(usage["uncached_requests"])
        if usage.get("cached_hits", 0) > self.stats.cached_hits:
            self.stats.cached_hits = int(usage["cached_hits"])
        self._write_risk_tsv()
        summary = {
            "doc_ids": doc_ids,
            "n_docs": len(doc_ids),
            "n_final": sum(
                1
                for d in doc_ids
                if (self.config.output_dir / "final" / f"{d}.json").exists()
            ),
            "extractor_model": self.config.extractor_model,
            "judge_model": self.config.judge_model,
            "stats": self.stats.as_dict(),
            "scheduler": self.scheduler.as_dict(),
            "thresholds": {
                "diagnosis_top": self.thresholds.diagnosis_top,
                "diagnosis_margin": self.thresholds.diagnosis_margin,
                "drug_top": self.thresholds.drug_top,
                "drug_margin": self.thresholds.drug_margin,
            },
            "client_usage": usage,
        }
        atomic_write_json(self.config.output_dir / "traces" / "run_summary.json", summary)
        return summary

    def _write_risk_tsv(self) -> None:
        path = ROOT / "analysis" / "openrouter_reduced" / "document_risk.tsv"
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "document_id",
            "entity_count",
            "risk_score",
            "risk_reasons",
            "requires_judge",
        ]
        # merge prior rows for docs not in this run
        existing: dict[str, dict[str, Any]] = {}
        if path.exists():
            with path.open(encoding="utf-8") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    existing[row["document_id"]] = row
        for row in self.risk_rows:
            existing[row["document_id"]] = row
        rows = [existing[k] for k in sorted(existing, key=lambda x: int(x))]
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in fields})


def write_compliance(output_dir: Path) -> None:
    text = """# EXTERNAL_API_DIAGNOSTIC_ONLY

Outputs under `output/openrouter_schema_teacher_reduced/` used external OpenRouter API calls.

Do **not** submit as competition ZIP.
Do **not** train a final competition model unless organizers confirm external-API offline data is allowed.
"""
    (output_dir / "EXTERNAL_API_DIAGNOSTIC_ONLY.md").write_text(text, encoding="utf-8")


def config_from_env(output_dir: Path | None = None) -> ReducedConfig:
    load_dotenv_file()
    extractor = (
        os.environ.get("OPENROUTER_REDUCED_EXTRACTOR_MODEL", "").strip()
        or DEFAULT_EXTRACTOR
    )
    judge = (
        os.environ.get("OPENROUTER_REDUCED_JUDGE_MODEL", "").strip() or DEFAULT_JUDGE
    )
    fallback = os.environ.get("OPENROUTER_REDUCED_JUDGE_FALLBACK_MODEL", "").strip() or None
    budget = env_float("OPENROUTER_REDUCED_BUDGET_USD", None)
    if budget is None:
        budget = env_float("OPENROUTER_BUDGET_USD", None)
    return ReducedConfig(
        output_dir=output_dir
        or (ROOT / "output" / "openrouter_schema_teacher_reduced"),
        cache_root=ROOT / "cache" / "openrouter_reduced",
        test_dir=ProjectPaths().test_dir,
        extractor_model=extractor,
        judge_model=judge,
        judge_fallback=fallback,
        microbatch_size=env_int("OPENROUTER_REDUCED_MICROBATCH_SIZE", 1),
        alone_char_threshold=env_int("OPENROUTER_REDUCED_ALONE_CHAR_THRESHOLD", 12000),
        candidate_batch_size=env_int("OPENROUTER_REDUCED_CANDIDATE_BATCH_SIZE", 15),
        enable_risk_review=env_flag("OPENROUTER_REDUCED_ENABLE_RISK_REVIEW", True),
        enable_candidate_judge=env_flag("OPENROUTER_REDUCED_ENABLE_CANDIDATE_JUDGE", True),
        document_workers=env_int("OPENROUTER_REDUCED_DOCUMENT_WORKERS", 1),
        budget_usd=budget,
    )
