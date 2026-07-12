"""OpenRouter schema teacher orchestrator (EXTERNAL_API_DIAGNOSTIC_ONLY)."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from modules.core.config import ProjectPaths
from modules.external.cluster_model_proposals import (
    Proposal,
    cluster_proposals,
    clusters_to_judge_payload,
    write_disagreements_tsv,
)
from modules.external.exact_span_aligner import AlignmentStats, align_entities, align_span
from modules.external.ontology_retrieval import LocalOntologyRetriever
from modules.external.openrouter_client import (
    OpenRouterClient,
    atomic_write_json,
    load_dotenv_file,
)
from modules.external.schema_gates import apply_schema_gates, to_competition_entity
from modules.external.select_openrouter_models import select_models

ROOT = ProjectPaths().root
SCHEMA_DIR = ROOT / "modules" / "external" / "schemas"
PROMPT_SCHEMA = (
    ROOT / "modules" / "external" / "prompts" / "competition_schema.md"
).read_text(encoding="utf-8")

EXTRACTOR_ROLES = {
    "A": {
        "name": "Precision specialist",
        "emphasis": (
            "Only output concepts clearly supported by the five classes. "
            "Omit procedures, devices, headings, demographics and generic status. "
            "Do not force uncertain phrases into a class."
        ),
    },
    "B": {
        "name": "Coverage specialist",
        "emphasis": (
            "Find all valid concepts while strictly respecting the five-class schema. "
            "Repeated mentions at different offsets must remain separate. "
            "Coverage does not permit schema-incompatible entities."
        ),
    },
    "C": {
        "name": "Boundary and clinical-schema specialist",
        "emphasis": (
            "Pay special attention to: minimal symptom spans; maximal drug spans; "
            "test-name/result separation; symptom-versus-diagnosis distinctions; "
            "assertion scope."
        ),
    },
}

PILOT_DEFAULT = ["75", "36", "20", "37", "51"]


def load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def safe_model_dirname(model_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model_id)


def select_pilot_docs(audit_dir: Path | None = None) -> list[str]:
    """Auto-select 5 docs from schema audit; fall back to curated defaults.

    Curated defaults (from schema-audit aggregates) are preferred when auto
    selection yields invalid file ids:
      75 procedure | 36 lab | 20 sym/dx | 37 drug | 51 clean
    """
    audit_dir = audit_dir or (ROOT / "analysis" / "schema_audit")
    try:
        import collections

        def _fid(raw: object) -> str | None:
            s = str(raw or "").replace(".json", "").replace(".txt", "").strip()
            return s if s.isdigit() else None

        proc_counts: dict[str, int] = collections.Counter()
        test_audit = audit_dir / "test_name_audit.tsv"
        if test_audit.exists():
            with test_audit.open(encoding="utf-8") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    if row.get("risk_status") == "LIKELY_PROCEDURE_NOT_TEST":
                        fid = _fid(row.get("file"))
                        if fid:
                            proc_counts[fid] += 1
        collision_counts: dict[str, int] = collections.Counter()
        coll = audit_dir / "type_collisions.tsv"
        if coll.exists():
            with coll.open(encoding="utf-8") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    pair = row.get("pair") or ""
                    if "TRIỆU_CHỨNG" in pair and "CHẨN_ĐOÁN" in pair:
                        fid = _fid(row.get("file"))
                        if fid:
                            collision_counts[fid] += 1
        manifest = audit_dir / "artifact_manifest.json"
        lab_scores: dict[str, int] = {}
        drug_scores: dict[str, int] = {}
        totals: dict[str, int] = {}
        if manifest.exists():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for item in data.get("per_file") or []:
                fid = _fid(item.get("file"))
                if not fid:
                    continue
                types = item.get("types") or {}
                lab_scores[fid] = int(types.get("TÊN_XÉT_NGHIỆM", 0)) + int(
                    types.get("KẾT_QUẢ_XÉT_NGHIỆM", 0)
                )
                drug_scores[fid] = int(types.get("THUỐC", 0))
                totals[fid] = int(item.get("n_entities") or sum(types.values()))
        procedure = max(proc_counts, key=proc_counts.get) if proc_counts else "75"
        lab = max(lab_scores, key=lab_scores.get) if lab_scores else "36"
        collision = (
            max(collision_counts, key=collision_counts.get) if collision_counts else "20"
        )
        drug = max(drug_scores, key=drug_scores.get) if drug_scores else "37"
        clean = "51"
        best = None
        for fid, total in totals.items():
            if total < 15:
                continue
            score = proc_counts.get(fid, 0) * 10 + collision_counts.get(fid, 0) * 5
            if best is None or score < best[0] or (score == best[0] and total < best[1]):
                best = (score, total, fid)
        if best:
            clean = best[2]
        chosen: list[str] = []
        for x in [procedure, lab, collision, drug, clean]:
            if x and x not in chosen and Path(ProjectPaths().test_dir / f"{x}.txt").exists():
                chosen.append(x)
        for d in PILOT_DEFAULT:
            if len(chosen) >= 5:
                break
            if d not in chosen and Path(ProjectPaths().test_dir / f"{d}.txt").exists():
                chosen.append(d)
        if len(chosen) < 5:
            return list(PILOT_DEFAULT)
        return chosen[:5]
    except Exception:
        return list(PILOT_DEFAULT)


def list_all_doc_ids(test_dir: Path) -> list[str]:
    ids = sorted(
        p.stem for p in test_dir.glob("*.txt") if p.stem.isdigit()
    )
    # numeric sort
    return sorted(ids, key=lambda x: int(x))


def read_document(test_dir: Path, doc_id: str) -> str:
    return (test_dir / f"{doc_id}.txt").read_text(encoding="utf-8")


def extraction_system_prompt(role_key: str) -> str:
    role = EXTRACTOR_ROLES[role_key]
    return (
        f"You are Extractor {role_key} — {role['name']}.\n"
        f"Role emphasis: {role['emphasis']}\n\n"
        "Follow the official competition schema exactly.\n\n"
        f"{PROMPT_SCHEMA}\n\n"
        "Return ONLY structured JSON matching the schema. "
        "Offsets must refer to the original document characters."
    )


def extraction_user_prompt(document: str, doc_id: str) -> str:
    return (
        f"Document ID: {doc_id}\n"
        "Extract all valid entities from the original document below.\n"
        "Do not invent ontology IDs.\n\n"
        "<<<DOCUMENT>>>\n"
        f"{document}\n"
        "<<<END_DOCUMENT>>>"
    )


@dataclass
class TeacherConfig:
    output_dir: Path
    cache_dir: Path
    test_dir: Path
    use_embeddings: bool = False
    max_workers: int = 3


class SchemaTeacherRunner:
    def __init__(self, client: OpenRouterClient, config: TeacherConfig, models: dict[str, Any]):
        self.client = client
        self.config = config
        self.models = models
        self.extractors = models["extractors"]
        self.judge = models["judge"]
        self.retriever = LocalOntologyRetriever(use_embeddings=config.use_embeddings)
        self.extraction_schema = load_schema("extraction.schema.json")
        self.adjudication_schema = load_schema("adjudication.schema.json")
        self.omission_schema = load_schema("omission.schema.json")
        self.icd_schema = load_schema("icd_selection.schema.json")
        self.rx_schema = load_schema("rxnorm_selection.schema.json")
        self.critic_schema = load_schema("critic.schema.json")
        self.critic_adj_schema = load_schema("critic_adjudication.schema.json")
        self.alignment_stats = AlignmentStats()
        self.disagreement_clusters: list = []
        self.parse_failures = 0
        self.parse_attempts = 0
        self.meta_by_model: dict[str, dict[str, Any]] = {}
        for e in self.extractors:
            self.meta_by_model[e["model_id"]] = {
                "pricing": e.get("pricing") or {},
                "context_length": e.get("context_length"),
                "supported_parameters": e.get("supported_parameters") or [],
            }
        self.meta_by_model[self.judge["model_id"]] = {
            "pricing": self.judge.get("pricing") or {},
            "context_length": self.judge.get("context_length"),
            "supported_parameters": self.judge.get("supported_parameters") or [],
        }

        for sub in (
            "raw",
            "aligned",
            "clusters",
            "adjudicated_spans",
            "ontology_candidates",
            "diagnostic_pseudo_gold",
            "critic",
            "logs",
        ):
            (self.config.output_dir / sub).mkdir(parents=True, exist_ok=True)

    def _model_meta(self, model_id: str) -> dict[str, Any]:
        return self.meta_by_model.get(model_id) or {}

    def run_extraction(self, doc_id: str, document: str) -> list[dict[str, Any]]:
        results = []
        for idx, ext in enumerate(self.extractors):
            role_key = chr(ord("A") + idx)
            model_id = ext["model_id"]
            self.parse_attempts += 1
            try:
                chat = self.client.chat_structured(
                    model=model_id,
                    system_prompt=extraction_system_prompt(role_key),
                    user_prompt=extraction_user_prompt(document, doc_id),
                    response_schema=self.extraction_schema,
                    schema_name="extraction",
                    temperature=0.0,
                    label=f"extract:{role_key}:{doc_id}",
                    model_meta=self._model_meta(model_id),
                )
            except Exception as exc:
                self.parse_failures += 1
                err = {
                    "error": str(exc.__class__.__name__),
                    "message": "extraction_failed",
                    "doc_id": doc_id,
                    "role": role_key,
                }
                atomic_write_json(
                    self.config.output_dir
                    / "raw"
                    / safe_model_dirname(model_id)
                    / f"{doc_id}.json",
                    err,
                )
                results.append(
                    {
                        "role": role_key,
                        "model": model_id,
                        "entities": [],
                        "validation_status": "request_error",
                    }
                )
                continue

            parsed = chat.parsed_response if isinstance(chat.parsed_response, dict) else {}
            entities = list(parsed.get("entities") or [])
            if chat.validation_status not in {"ok", "healed_json_extract", "cached"}:
                self.parse_failures += 1
            raw_path = (
                self.config.output_dir
                / "raw"
                / safe_model_dirname(model_id)
                / f"{doc_id}.json"
            )
            atomic_write_json(
                raw_path,
                {
                    "doc_id": doc_id,
                    "role": role_key,
                    "model": model_id,
                    "request_hash": chat.request_hash,
                    "validation_status": chat.validation_status,
                    "entities": entities,
                },
            )
            aligned, self.alignment_stats = align_entities(
                document, entities, self.alignment_stats
            )
            atomic_write_json(
                self.config.output_dir
                / "aligned"
                / safe_model_dirname(model_id)
                / f"{doc_id}.json",
                {"doc_id": doc_id, "role": role_key, "model": model_id, "entities": aligned},
            )
            results.append(
                {
                    "role": role_key,
                    "model": model_id,
                    "entities": aligned,
                    "validation_status": chat.validation_status,
                }
            )
        return results

    def build_proposals(
        self, doc_id: str, extractions: list[dict[str, Any]]
    ) -> list[Proposal]:
        proposals: list[Proposal] = []
        for ext in extractions:
            for i, ent in enumerate(ext["entities"]):
                # Free models occasionally omit required fields; skip rather than abort the doc.
                etype = ent.get("type")
                text = ent.get("text")
                start, end = ent.get("start"), ent.get("end")
                if not etype or not text or not isinstance(start, int) or not isinstance(end, int):
                    continue
                proposals.append(
                    Proposal(
                        proposal_id=f"{doc_id}:{ext['role']}:{i}",
                        document=doc_id,
                        model=ext["model"],
                        role=ext["role"],
                        text=str(text),
                        start=int(start),
                        end=int(end),
                        type=str(etype),
                        assertions=list(ent.get("assertions") or []),
                        confidence=float(ent.get("confidence") or 0.0),
                        brief_reason=str(ent.get("brief_reason") or ""),
                        raw=ent,
                    )
                )
        return proposals

    def adjudicate(
        self, doc_id: str, document: str, clusters_payload: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        system = (
            "You are an independent adjudicator for Vietnamese clinical entity extraction.\n"
            "Resolve disagreements among extractor proposals using the official schema.\n"
            "You must return exact source substrings and character offsets.\n\n"
            f"{PROMPT_SCHEMA}"
        )
        user = (
            f"Document ID: {doc_id}\n\n<<<DOCUMENT>>>\n{document}\n<<<END_DOCUMENT>>>\n\n"
            "Proposal clusters (JSON):\n"
            f"{json.dumps(clusters_payload, ensure_ascii=False)}\n\n"
            "For each cluster choose an action and emit final entities for that cluster. "
            "REJECT_ALL when proposals violate the five-class schema (e.g. procedures)."
        )
        self.parse_attempts += 1
        chat = self.client.chat_structured(
            model=self.judge["model_id"],
            system_prompt=system,
            user_prompt=user,
            response_schema=self.adjudication_schema,
            schema_name="adjudication",
            temperature=0.0,
            label=f"judge_adj:{doc_id}",
            model_meta=self._model_meta(self.judge["model_id"]),
        )
        if chat.validation_status not in {"ok", "healed_json_extract", "cached"}:
            self.parse_failures += 1
        parsed = chat.parsed_response if isinstance(chat.parsed_response, dict) else {}
        entities: list[dict[str, Any]] = []
        by_id = {c["cluster_id"]: c for c in clusters_payload}
        for dec in parsed.get("cluster_decisions") or []:
            action = dec.get("action")
            cid = dec.get("cluster_id")
            if action == "REJECT_ALL":
                continue
            if action == "ACCEPT_PROPOSAL":
                pid = dec.get("accepted_proposal_id")
                cluster = by_id.get(cid) or {}
                chosen = None
                for p in cluster.get("proposals") or []:
                    if p.get("proposal_id") == pid:
                        chosen = p
                        break
                if chosen is None and cluster.get("proposals"):
                    chosen = cluster["proposals"][0]
                if chosen:
                    entities.append(
                        {
                            "text": chosen["text"],
                            "start": chosen["start"],
                            "end": chosen["end"],
                            "type": chosen["type"],
                            "assertions": chosen.get("assertions") or [],
                            "left_anchor": "",
                            "right_anchor": "",
                            "source": "ACCEPT_PROPOSAL",
                            "judge_action": action,
                        }
                    )
                continue
            for ent in dec.get("entities") or []:
                entities.append(
                    {
                        **ent,
                        "left_anchor": ent.get("left_anchor") or "",
                        "right_anchor": ent.get("right_anchor") or "",
                        "source": "JUDGE",
                        "judge_action": action,
                    }
                )
        aligned, self.alignment_stats = align_entities(
            document, entities, self.alignment_stats
        )
        return aligned

    def omission_recovery(
        self, doc_id: str, document: str, current: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        system = (
            "You recover omissions for Vietnamese clinical NER under a strict five-class schema.\n"
            "Are there valid target entities in this document that none of the extractors proposed?\n"
            "Only propose exact source spans. Do not invent ontology IDs.\n\n"
            f"{PROMPT_SCHEMA}"
        )
        user = (
            f"Document ID: {doc_id}\n\n<<<DOCUMENT>>>\n{document}\n<<<END_DOCUMENT>>>\n\n"
            "Already adjudicated entities:\n"
            f"{json.dumps([{k: e.get(k) for k in ('text','start','end','type','assertions')} for e in current], ensure_ascii=False)}\n\n"
            "Return only missing valid entities."
        )
        self.parse_attempts += 1
        chat = self.client.chat_structured(
            model=self.judge["model_id"],
            system_prompt=system,
            user_prompt=user,
            response_schema=self.omission_schema,
            schema_name="omission",
            temperature=0.0,
            label=f"omission:{doc_id}",
            model_meta=self._model_meta(self.judge["model_id"]),
        )
        if chat.validation_status not in {"ok", "healed_json_extract", "cached"}:
            self.parse_failures += 1
        parsed = chat.parsed_response if isinstance(chat.parsed_response, dict) else {}
        recovered = []
        for ent in parsed.get("entities") or []:
            ent = dict(ent)
            ent["recovery"] = "JUDGE_OMISSION_RECOVERY"
            ent["source"] = "JUDGE_OMISSION_RECOVERY"
            recovered.append(ent)
        aligned, self.alignment_stats = align_entities(
            document, recovered, self.alignment_stats
        )
        for e in aligned:
            e["recovery"] = "JUDGE_OMISSION_RECOVERY"
            e["source"] = "JUDGE_OMISSION_RECOVERY"
        return aligned

    def attach_ontology_candidates(
        self, doc_id: str, document: str, entities: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        payload: dict[str, Any] = {"doc_id": doc_id, "entities": []}
        enriched = []
        for i, ent in enumerate(entities):
            item = dict(ent)
            item["entity_id"] = f"{doc_id}:e{i}"
            cands: list[dict[str, Any]] = []
            if ent["type"] == "CHẨN_ĐOÁN":
                cands = [c.as_dict() for c in self.retriever.retrieve_icd(ent["text"])]
            elif ent["type"] == "THUỐC":
                cands = [c.as_dict() for c in self.retriever.retrieve_rxnorm(ent["text"])]
            item["local_candidates"] = cands
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
            self.config.output_dir / "ontology_candidates" / f"{doc_id}.json", payload
        )
        return enriched, payload

    def select_candidates(
        self, doc_id: str, document: str, entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        diagnoses = [e for e in entities if e["type"] == "CHẨN_ĐOÁN"]
        drugs = [e for e in entities if e["type"] == "THUỐC"]
        id_to_selected: dict[str, list[str]] = {}

        if diagnoses:
            system = (
                "Select ICD-10 codes ONLY from the provided local candidate lists. "
                "You may return zero, one, or multiple codes when clinically justified. "
                "Never invent IDs absent from the list. Do not add multiple codes merely because they are similar."
            )
            items = []
            for e in diagnoses:
                start, end = e["start"], e["end"]
                ctx = document[max(0, start - 120) : min(len(document), end + 120)]
                items.append(
                    {
                        "entity_id": e["entity_id"],
                        "span": e["text"],
                        "context": ctx,
                        "candidates": e.get("local_candidates") or [],
                    }
                )
            user = (
                f"Document ID: {doc_id}\nDiagnoses to code:\n"
                f"{json.dumps(items, ensure_ascii=False)}"
            )
            self.parse_attempts += 1
            chat = self.client.chat_structured(
                model=self.judge["model_id"],
                system_prompt=system,
                user_prompt=user,
                response_schema=self.icd_schema,
                schema_name="icd_selection",
                temperature=0.0,
                label=f"icd:{doc_id}",
                model_meta=self._model_meta(self.judge["model_id"]),
            )
            if chat.validation_status not in {"ok", "healed_json_extract", "cached"}:
                self.parse_failures += 1
            parsed = chat.parsed_response if isinstance(chat.parsed_response, dict) else {}
            for sel in parsed.get("selections") or []:
                eid = sel.get("entity_id")
                allowed = {
                    c["id"]
                    for e in diagnoses
                    if e["entity_id"] == eid
                    for c in (e.get("local_candidates") or [])
                }
                chosen = [x for x in (sel.get("selected_ids") or []) if x in allowed]
                id_to_selected[eid] = chosen

        if drugs:
            system = (
                "Select zero or one RxCUI ONLY from the provided local candidate list. "
                "Do not use ingredient-first hedging. Never invent IDs."
            )
            items = []
            for e in drugs:
                start, end = e["start"], e["end"]
                ctx = document[max(0, start - 80) : min(len(document), end + 80)]
                items.append(
                    {
                        "entity_id": e["entity_id"],
                        "span": e["text"],
                        "context": ctx,
                        "candidates": e.get("local_candidates") or [],
                    }
                )
            user = (
                f"Document ID: {doc_id}\nDrugs to code:\n"
                f"{json.dumps(items, ensure_ascii=False)}"
            )
            self.parse_attempts += 1
            chat = self.client.chat_structured(
                model=self.judge["model_id"],
                system_prompt=system,
                user_prompt=user,
                response_schema=self.rx_schema,
                schema_name="rxnorm_selection",
                temperature=0.0,
                label=f"rx:{doc_id}",
                model_meta=self._model_meta(self.judge["model_id"]),
            )
            if chat.validation_status not in {"ok", "healed_json_extract", "cached"}:
                self.parse_failures += 1
            parsed = chat.parsed_response if isinstance(chat.parsed_response, dict) else {}
            for sel in parsed.get("selections") or []:
                eid = sel.get("entity_id")
                allowed = {
                    c["id"]
                    for e in drugs
                    if e["entity_id"] == eid
                    for c in (e.get("local_candidates") or [])
                }
                sid = sel.get("selected_id")
                if sid in (None, "", "null", "None"):
                    id_to_selected[eid] = []
                else:
                    id_to_selected[eid] = [sid] if sid in allowed else []

        out = []
        for e in entities:
            final = to_competition_entity(e)
            if e["type"] in {"CHẨN_ĐOÁN", "THUỐC"}:
                final["candidates"] = id_to_selected.get(e["entity_id"], [])
            elif "candidates" in final:
                del final["candidates"]
            out.append(final)
        return out

    def critic_pass(
        self, doc_id: str, document: str, final_entities: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        system = (
            "You are an adversarial critic for Vietnamese clinical NER. "
            "Identify false positives, missed entities, wrong types/boundaries/assertions/"
            "candidates, procedure-as-test errors, and test-name/result segmentation errors. "
            "Do NOT modify the final output yourself; only report issues.\n\n"
            f"{PROMPT_SCHEMA}"
        )
        user = (
            f"Document ID: {doc_id}\n<<<DOCUMENT>>>\n{document}\n<<<END_DOCUMENT>>>\n\n"
            f"Final output:\n{json.dumps(final_entities, ensure_ascii=False)}"
        )
        self.parse_attempts += 1
        chat = self.client.chat_structured(
            model=self.judge["model_id"],
            system_prompt=system,
            user_prompt=user,
            response_schema=self.critic_schema,
            schema_name="critic",
            temperature=0.0,
            label=f"critic:{doc_id}",
            model_meta=self._model_meta(self.judge["model_id"]),
        )
        if chat.validation_status not in {"ok", "healed_json_extract", "cached"}:
            self.parse_failures += 1
        issues = []
        parsed = chat.parsed_response if isinstance(chat.parsed_response, dict) else {}
        for issue in parsed.get("issues") or []:
            issues.append({**issue, "file": doc_id})
        atomic_write_json(
            self.config.output_dir / "critic" / f"{doc_id}_issues.json",
            {"doc_id": doc_id, "issues": issues},
        )
        if not issues:
            return final_entities, issues

        # final adjudication only for critic-raised issues
        system2 = (
            "Adjudicate critic-raised issues. APPLY_FIX only when the issue is clearly valid "
            "under the official schema; otherwise IGNORE. Exact source spans required.\n\n"
            f"{PROMPT_SCHEMA}"
        )
        user2 = (
            f"Document:\n{document}\n\nCurrent entities:\n"
            f"{json.dumps(final_entities, ensure_ascii=False)}\n\nIssues:\n"
            f"{json.dumps(issues, ensure_ascii=False)}"
        )
        self.parse_attempts += 1
        chat2 = self.client.chat_structured(
            model=self.judge["model_id"],
            system_prompt=system2,
            user_prompt=user2,
            response_schema=self.critic_adj_schema,
            schema_name="critic_adjudication",
            temperature=0.0,
            label=f"critic_adj:{doc_id}",
            model_meta=self._model_meta(self.judge["model_id"]),
        )
        if chat2.validation_status not in {"ok", "healed_json_extract", "cached"}:
            self.parse_failures += 1
        parsed2 = chat2.parsed_response if isinstance(chat2.parsed_response, dict) else {}
        updated = [dict(e) for e in final_entities]
        for act in parsed2.get("actions") or []:
            if act.get("action") != "APPLY_FIX":
                continue
            ent = act.get("entity")
            if not ent:
                # treat as removal request via remove_existing alone is insufficient; skip
                continue
            result = align_span(
                document,
                str(ent.get("text") or ""),
                ent.get("start"),
                ent.get("end"),
            )
            if result.start is None:
                continue
            new_ent = {
                "text": document[result.start : result.end],
                "type": ent["type"],
                "assertions": list(ent.get("assertions") or []),
                "position": [result.start, result.end],
            }
            if ent.get("remove_existing"):
                updated = [
                    e
                    for e in updated
                    if not (
                        e["position"][0] == result.start
                        and e["position"][1] == result.end
                        and e["type"] == ent["type"]
                    )
                ]
            # replace overlapping same-type or append
            replaced = False
            for i, e in enumerate(updated):
                if (
                    e["position"][0] == new_ent["position"][0]
                    and e["position"][1] == new_ent["position"][1]
                ):
                    # preserve candidates if type unchanged diagnosis/drug
                    if e.get("type") == new_ent["type"] and "candidates" in e:
                        new_ent["candidates"] = e["candidates"]
                    updated[i] = new_ent
                    replaced = True
                    break
            if not replaced and not ent.get("remove_existing"):
                if new_ent["type"] in {"CHẨN_ĐOÁN", "THUỐC"}:
                    new_ent["candidates"] = []
                updated.append(new_ent)
        updated.sort(key=lambda e: (e["position"][0], e["position"][1], e["type"]))
        # drop diagnostic-only keys if any
        cleaned = []
        for e in updated:
            item = {
                "text": e["text"],
                "type": e["type"],
                "assertions": e.get("assertions") or [],
                "position": e["position"],
            }
            if "candidates" in e:
                item["candidates"] = e["candidates"]
            cleaned.append(item)
        return cleaned, issues

    def process_document(self, doc_id: str) -> dict[str, Any]:
        gold_path = self.config.output_dir / "diagnostic_pseudo_gold" / f"{doc_id}.json"
        if gold_path.exists():
            return {
                "doc_id": doc_id,
                "status": "resumed",
                "n_entities": len(json.loads(gold_path.read_text(encoding="utf-8"))),
            }

        document = read_document(self.config.test_dir, doc_id)
        extractions = self.run_extraction(doc_id, document)
        proposals = self.build_proposals(doc_id, extractions)
        clusters = cluster_proposals(proposals, doc_id)
        self.disagreement_clusters.extend(clusters)
        atomic_write_json(
            self.config.output_dir / "clusters" / f"{doc_id}.json",
            {"doc_id": doc_id, "clusters": clusters_to_judge_payload(clusters)},
        )
        adjudicated = self.adjudicate(
            doc_id, document, clusters_to_judge_payload(clusters)
        )
        recovered = self.omission_recovery(doc_id, document, adjudicated)
        combined = adjudicated + recovered
        gates = apply_schema_gates(document, combined)
        atomic_write_json(
            self.config.output_dir / "adjudicated_spans" / f"{doc_id}.json",
            {
                "doc_id": doc_id,
                "entities": gates.kept,
                "rejected": gates.rejected,
                "overlaps": gates.overlaps,
            },
        )
        enriched, _ = self.attach_ontology_candidates(doc_id, document, gates.kept)
        final_entities = self.select_candidates(doc_id, document, enriched)
        before_critic = [dict(e) for e in final_entities]
        # Persist pre-critic gold so budget stop during critic does not lose the doc
        gold_path = self.config.output_dir / "diagnostic_pseudo_gold" / f"{doc_id}.json"
        atomic_write_json(gold_path, self._sanitize_final(document, final_entities, doc_id))
        try:
            final_entities, issues = self.critic_pass(doc_id, document, final_entities)
        except Exception as exc:
            issues = [{"error": exc.__class__.__name__, "message": str(exc)[:300]}]
            # keep pre-critic gold
            atomic_write_json(
                self.config.output_dir / "critic" / f"{doc_id}_before_after.json",
                {"before": before_critic, "after": before_critic, "issues": issues},
            )
            return {
                "doc_id": doc_id,
                "status": "ok_pre_critic",
                "n_entities": len(before_critic),
                "n_critic_issues": 0,
                "critic_error": exc.__class__.__name__,
            }
        atomic_write_json(
            self.config.output_dir / "critic" / f"{doc_id}_before_after.json",
            {"before": before_critic, "after": final_entities, "issues": issues},
        )
        sanitized = self._sanitize_final(document, final_entities, doc_id)
        atomic_write_json(gold_path, sanitized)
        return {
            "doc_id": doc_id,
            "status": "ok",
            "n_entities": len(sanitized),
            "n_critic_issues": len(issues),
        }

    def _sanitize_final(
        self, document: str, final_entities: list[dict[str, Any]], doc_id: str
    ) -> list[dict[str, Any]]:
        cand_file = self.config.output_dir / "ontology_candidates" / f"{doc_id}.json"
        allowed_by_span = {}
        if cand_file.exists():
            for ent in (json.loads(cand_file.read_text(encoding="utf-8")).get("entities") or []):
                key = (ent["text"], tuple(ent["position"]), ent["type"])
                allowed_by_span[key] = {c["id"] for c in (ent.get("candidates") or [])}

        sanitized = []
        for e in final_entities:
            item = {
                "text": e["text"],
                "type": e["type"],
                "assertions": e.get("assertions") or [],
                "position": e["position"],
            }
            s, en = item["position"]
            if not (0 <= s < en <= len(document)) or document[s:en] != item["text"]:
                continue
            if item["type"] in {"CHẨN_ĐOÁN", "THUỐC"}:
                key = (item["text"], tuple(item["position"]), item["type"])
                allowed = allowed_by_span.get(key, set())
                cands = [c for c in (e.get("candidates") or []) if c in allowed]
                item["candidates"] = cands
            sanitized.append(item)
        sanitized.sort(key=lambda e: (e["position"][0], e["position"][1], e["type"]))
        return sanitized

    def process_many(self, doc_ids: list[str]) -> list[dict[str, Any]]:
        results = []
        # sequential documents; internal client has concurrency semaphore for requests
        for doc_id in doc_ids:
            try:
                results.append(self.process_document(doc_id))
                # persist disagreement tsv incrementally
                write_disagreements_tsv(
                    self.disagreement_clusters,
                    ROOT / "analysis" / "openrouter_teacher" / "model_disagreements.tsv",
                )
            except Exception as exc:
                err_path = self.config.output_dir / "logs" / f"{doc_id}_error.json"
                atomic_write_json(
                    err_path,
                    {
                        "doc_id": doc_id,
                        "error": exc.__class__.__name__,
                        "message": str(exc)[:500],
                    },
                )
                results.append(
                    {"doc_id": doc_id, "status": "error", "error": exc.__class__.__name__}
                )
                if "Budget stop" in str(exc):
                    break
        return results


def write_compliance_manifest(output_dir: Path) -> None:
    text = """# EXTERNAL_API_DIAGNOSTIC_ONLY

All outputs under `output/openrouter_schema_teacher/` were produced with **external
OpenRouter API calls**.

## Competition compliance

The competition description states that external APIs are not allowed for LLM/agent
solutions.

Therefore:

- Do **not** use these outputs in a competition submission.
- Do **not** use them to train the final competition model unless the organizers
  explicitly confirm that external-API-generated offline training data is allowed.

## Purpose

Diagnostic only: measure whether frontier models infer the organizer's intended schema
substantially better than frozen v7 / v10 pipelines.

Project name: `openrouter_schema_teacher` (not a competition pipeline version / not v11).
"""
    (output_dir / "EXTERNAL_API_DIAGNOSTIC_ONLY.md").write_text(text, encoding="utf-8")


PROFILES: dict[str, dict[str, Any]] = {
    "default": {
        "output_name": "openrouter_schema_teacher",
        "cache_name": "openrouter_schema_teacher",
        "analysis_subdir": "openrouter_teacher",
        # uses OPENROUTER_EXTRACTOR_MODELS / OPENROUTER_JUDGE_MODEL from env
        "extractors": None,
        "judge": None,
    },
    "free_first": {
        "output_name": "openrouter_schema_teacher_free",
        "cache_name": "openrouter_schema_teacher_free",
        "analysis_subdir": "openrouter_teacher_free",
        "extractors": [
            "tencent/hy3:free",
            "nvidia/nemotron-3-ultra-550b-a55b:free",
            "poolside/laguna-m.1:free",
        ],
        # Prefer the free model that advertises structured outputs.
        "judge": "tencent/hy3:free",
    },
}


def _models_from_ids(
    client: OpenRouterClient, extractor_ids: list[str], judge_id: str
) -> dict[str, Any]:
    from modules.external.select_openrouter_models import (
        SelectedModel,
        _context_len,
        _family_of,
        _supports_structured,
        validate_configured_models,
        write_model_selection_md,
    )
    from dataclasses import asdict

    metas = validate_configured_models(client, extractor_ids + [judge_id])
    extractors = []
    for i, (mid, meta) in enumerate(zip(extractor_ids, metas[:3])):
        extractors.append(
            SelectedModel(
                model_id=mid,
                family=_family_of(mid),
                context_length=_context_len(meta) or None,
                supports_structured_outputs=_supports_structured(meta),
                pricing=dict(meta.get("pricing") or {}),
                reason="Profile-configured free_first / explicit IDs; validated via Models API.",
                role=f"extractor_{chr(ord('A') + i)}",
            )
        )
        # stash supported_parameters on dict later
    jmeta = metas[3]
    judge = SelectedModel(
        model_id=judge_id,
        family=_family_of(judge_id),
        context_length=_context_len(jmeta) or None,
        supports_structured_outputs=_supports_structured(jmeta),
        pricing=dict(jmeta.get("pricing") or {}),
        reason="Profile-configured judge; validated via Models API.",
        role="judge",
    )
    out = {
        "mode": "profile",
        "extractors": [asdict(e) for e in extractors],
        "judge": asdict(judge),
        "_raw_metas": {m["id"]: m for m in metas},
    }
    # attach supported_parameters into pricing-adjacent meta used by runner
    for e, meta in zip(out["extractors"], metas[:3]):
        e["supported_parameters"] = list(meta.get("supported_parameters") or [])
        e["pricing"] = dict(meta.get("pricing") or {})
    out["judge"]["supported_parameters"] = list(
        jmeta.get("supported_parameters") or []
    )
    return out


def main(argv: list[str] | None = None) -> int:
    load_dotenv_file()
    parser = argparse.ArgumentParser(description="Run openrouter_schema_teacher")
    parser.add_argument("--pilot-only", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument(
        "--full-only",
        action="store_true",
        help="Skip pilot gates; process all docs missing diagnostic_pseudo_gold",
    )
    parser.add_argument("--docs", nargs="*", default=None)
    parser.add_argument("--use-embeddings", action="store_true")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES.keys()),
        default=os.environ.get("OPENROUTER_TEACHER_PROFILE", "default"),
        help="default=frontier paid mix from env; free_first=all-free OpenRouter models",
    )
    args = parser.parse_args(argv)

    profile = PROFILES[args.profile]
    output_dir = ROOT / "output" / profile["output_name"]
    cache_dir = ROOT / "cache" / profile["cache_name"]
    analysis_dir = ROOT / "analysis" / profile["analysis_subdir"]
    analysis_dir.mkdir(parents=True, exist_ok=True)
    test_dir = ProjectPaths().test_dir
    write_compliance_manifest(output_dir)
    print(f"Profile: {args.profile}")
    print(f"Output: {output_dir}")
    print(f"Cache:  {cache_dir}")

    with OpenRouterClient(cache_dir=cache_dir) as client:
        print(f"OpenRouter API keys loaded: {client.key_count}")
        if profile["extractors"] and profile["judge"]:
            # temporarily set env so select_models path stays consistent if needed
            os.environ["OPENROUTER_EXTRACTOR_MODELS"] = ",".join(profile["extractors"])
            os.environ["OPENROUTER_JUDGE_MODEL"] = profile["judge"]
            models = _models_from_ids(
                client, list(profile["extractors"]), str(profile["judge"])
            )
            from modules.external.select_openrouter_models import (
                SelectedModel,
                write_model_selection_md,
            )
            from dataclasses import asdict

            # write selection report into profile analysis dir
            write_model_selection_md(
                analysis_dir / "model_selection.md",
                [
                    SelectedModel(**{k: e[k] for k in (
                        "model_id", "family", "context_length",
                        "supports_structured_outputs", "pricing", "reason", "role"
                    )})
                    for e in models["extractors"]
                ],
                SelectedModel(**{k: models["judge"][k] for k in (
                    "model_id", "family", "context_length",
                    "supports_structured_outputs", "pricing", "reason", "role"
                )}),
                mode=f"profile:{args.profile}",
            )
            atomic_write_json(analysis_dir / "model_selection.json", {
                "mode": f"profile:{args.profile}",
                "extractors": models["extractors"],
                "judge": models["judge"],
            })
        else:
            # Paid / default profile: require explicit model IDs from the user.
            ext_env = os.environ.get("OPENROUTER_EXTRACTOR_MODELS", "").strip()
            judge_env = os.environ.get("OPENROUTER_JUDGE_MODEL", "").strip()
            if not ext_env or not judge_env:
                raise SystemExit(
                    "profile=default requires OPENROUTER_EXTRACTOR_MODELS and "
                    "OPENROUTER_JUDGE_MODEL.\n"
                    "TODO: ask the user for NEW paid model IDs — do not reuse the "
                    "old opus/gemini/gpt-5.5 placeholders without confirmation.\n"
                    "Or run: --profile free_first"
                )
            models = select_models(
                client=client,
                report_path=analysis_dir / "model_selection.md",
            )
            # enrich supported_parameters from a fresh catalog lookup
            catalog = {str(m.get("id")): m for m in client.list_models()}
            for e in models["extractors"]:
                meta = catalog.get(e["model_id"]) or {}
                e["supported_parameters"] = list(meta.get("supported_parameters") or [])
            jmeta = catalog.get(models["judge"]["model_id"]) or {}
            models["judge"]["supported_parameters"] = list(
                jmeta.get("supported_parameters") or []
            )

        extractor_ids = [e["model_id"] for e in models["extractors"]]
        print("Extractors:", ", ".join(extractor_ids))
        print("Judge:", models["judge"]["model_id"])

        runner = SchemaTeacherRunner(
            client,
            TeacherConfig(
                output_dir=output_dir,
                cache_dir=cache_dir,
                test_dir=test_dir,
                use_embeddings=args.use_embeddings,
            ),
            models,
        )

        if args.docs:
            doc_ids = [d.replace(".json", "").replace(".txt", "") for d in args.docs]
            results = runner.process_many(doc_ids)
            atomic_write_json(output_dir / "logs" / "last_run.json", {"results": results})
            return 0

        if args.full_only:
            all_ids = list_all_doc_ids(test_dir)
            missing = [
                d
                for d in all_ids
                if not (output_dir / "diagnostic_pseudo_gold" / f"{d}.json").exists()
            ]
            print(
                f"full-only: {len(missing)} missing of {len(all_ids)} "
                f"(skipping existing gold)"
            )
            full_results = runner.process_many(missing)
            atomic_write_json(
                output_dir / "logs" / "full_results.json",
                {
                    "mode": "full_only",
                    "missing_at_start": missing,
                    "full": full_results,
                    "usage": client.usage_summary(),
                    "alignment": runner.alignment_stats.as_dict(),
                },
            )
            return 0

        pilot_ids = select_pilot_docs()
        # Prefer curated audit set for free_first reproducibility
        if args.profile == "free_first":
            pilot_ids = list(PILOT_DEFAULT)
        print("Pilot docs:", pilot_ids)
        pilot_results = runner.process_many(pilot_ids)
        atomic_write_json(
            output_dir / "logs" / "pilot_results.json",
            {"docs": pilot_ids, "results": pilot_results, "usage": client.usage_summary()},
        )

        # pilot gates
        budget = os.environ.get("OPENROUTER_BUDGET_USD", "").strip()
        valid_final = 0
        for d in pilot_ids:
            p = output_dir / "diagnostic_pseudo_gold" / f"{d}.json"
            if not p.exists():
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                assert isinstance(data, list)
                valid_final += 1
            except Exception:
                pass
        usage = client.usage_summary()
        parse_rate = usage.get("parse_ok_rate", 0.0)
        # also use runner counters
        if runner.parse_attempts:
            parse_rate = 1.0 - (runner.parse_failures / max(1, runner.parse_attempts))

        # Free profile: budget may be 0-cost; require budget env only if >0 configured
        budget_ok = True
        if budget:
            try:
                budget_ok = float(budget) >= 0
            except ValueError:
                budget_ok = False
        # For free_first, allow continuing when budget unset (all $0 models)
        if args.profile == "free_first":
            budget_ok = True
        # free_first: softer parse gate (Nemotron occasionally fails JSON); still require all pilot gold
        parse_floor = 0.90 if args.profile == "free_first" else 0.95
        pilot_ok = valid_final == len(pilot_ids) and parse_rate >= parse_floor
        gate = {
            "profile": args.profile,
            "budget_set": bool(budget) or args.profile == "free_first",
            "valid_final": valid_final,
            "pilot_n": len(pilot_ids),
            "parse_ok_rate": parse_rate,
            "parse_floor": parse_floor,
            "pilot_ok": pilot_ok,
            "continue_full": budget_ok
            and pilot_ok
            and (args.full or not args.pilot_only),
        }
        atomic_write_json(output_dir / "logs" / "pilot_gates.json", gate)
        print("Pilot gates:", gate)

        if args.pilot_only:
            return 0
        if not gate["continue_full"]:
            print("Stopping after pilot — gates not satisfied or budget unset.")
            return 0

        all_ids = list_all_doc_ids(test_dir)
        remaining = [
            d
            for d in all_ids
            if d not in set(pilot_ids)
            and not (output_dir / "diagnostic_pseudo_gold" / f"{d}.json").exists()
        ]
        print(f"Full run: {len(remaining)} remaining docs (+ {len(pilot_ids)} pilot)")
        full_results = runner.process_many(remaining)
        atomic_write_json(
            output_dir / "logs" / "full_results.json",
            {
                "pilot": pilot_results,
                "full": full_results,
                "usage": client.usage_summary(),
                "alignment": runner.alignment_stats.as_dict(),
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
