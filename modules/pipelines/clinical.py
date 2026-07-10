from __future__ import annotations

import copy
from typing import Any

from modules.components.assertions.base import BaseAssertionDetector
from modules.components.classification.base import BaseEntityClassifier
from modules.components.linking.base import BaseEntityLinker
from modules.components.ner.base import BaseNERExtractor
from modules.components.normalization.base import BaseDocumentNormalizer
from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.core.schemas import Document, EntityMention, FinalEntity
from modules.pipelines.base import BasePipeline


class ClinicalEntityLinkingPipeline(BasePipeline):
    """Stable interface implemented by all versioned pipelines."""

    def __init__(
        self,
        ner: BaseNERExtractor,
        classifier: BaseEntityClassifier,
        linker: BaseEntityLinker,
        assertion_detector: BaseAssertionDetector,
        normalizer: BaseDocumentNormalizer | None = None,
        pre_classification_postprocessors: list[BaseMentionPostProcessor] | None = None,
        post_classification_postprocessors: list[BaseMentionPostProcessor]
        | None = None,
    ):
        self.normalizer = normalizer
        self.ner = ner
        self.pre_classification_postprocessors = pre_classification_postprocessors or []
        self.classifier = classifier
        self.post_classification_postprocessors = (
            post_classification_postprocessors or []
        )
        self.linker = linker
        self.assertion_detector = assertion_detector

    @staticmethod
    def _snapshot_entity(m: EntityMention | FinalEntity) -> dict[str, Any]:
        """Immutable serialized snapshot so later mutations cannot rewrite traces."""
        if hasattr(m, "span"):
            start, end = m.span.start, m.span.end
        else:
            start, end = None, None

        text = getattr(m, "text", "")
        label = getattr(m, "label", getattr(m, "type", ""))
        candidates = getattr(m, "candidates", [])
        assertions = getattr(m, "assertions", [])
        confidence = getattr(m, "confidence", None)
        source = getattr(m, "source", None)
        metadata = getattr(m, "metadata", {}) or {}

        return {
            "text": text,
            "label": label,
            "start": start,
            "end": end,
            "confidence": confidence,
            "source": source,
            "candidates": list(candidates) if candidates else [],
            "assertions": list(assertions) if assertions else [],
            "metadata": copy.deepcopy(metadata),
        }

    @staticmethod
    def _snapshot_entities(
        mentions: list[EntityMention] | list[FinalEntity],
    ) -> list[dict[str, Any]]:
        return [ClinicalEntityLinkingPipeline._snapshot_entity(m) for m in mentions]

    @staticmethod
    def _span_iou(a: dict[str, Any], b: dict[str, Any]) -> float:
        if (
            a["start"] is None
            or a["end"] is None
            or b["start"] is None
            or b["end"] is None
        ):
            return 0.0
        inter = max(0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
        if inter <= 0:
            return 0.0
        union = max(a["end"], b["end"]) - min(a["start"], b["start"])
        if union <= 0:
            return 0.0
        return inter / union

    @staticmethod
    def _boundary_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
        if (
            a["start"] is None
            or a["end"] is None
            or b["start"] is None
            or b["end"] is None
        ):
            return float("inf")
        return abs(a["start"] - b["start"]) + abs(a["end"] - b["end"])

    def _diff_mentions(
        self,
        before: list[EntityMention] | list[FinalEntity] | list[dict[str, Any]],
        after: list[EntityMention] | list[FinalEntity] | list[dict[str, Any]],
    ) -> dict[str, list[Any]]:
        def to_item(m: Any) -> dict[str, Any]:
            if isinstance(m, dict) and "text" in m and "label" in m:
                return {
                    "start": m.get("start"),
                    "end": m.get("end"),
                    "text": m.get("text", ""),
                    "label": m.get("label", ""),
                    "candidates": list(m.get("candidates") or []),
                    "assertions": list(m.get("assertions") or []),
                    "source": m.get("source"),
                    "metadata": copy.deepcopy(m.get("metadata") or {}),
                }
            return self._snapshot_entity(m)

        b_items = [to_item(m) for m in before]
        a_items = [to_item(m) for m in after]

        matched_a: set[int] = set()
        matched_b: set[int] = set()

        modified: list[tuple[dict[str, Any], dict[str, Any]]] = []
        unchanged: list[tuple[dict[str, Any], dict[str, Any]]] = []

        def _record_match(i: int, j: int) -> None:
            b, a = b_items[i], a_items[j]
            if b["candidates"] == a["candidates"] and b["assertions"] == a["assertions"]:
                if (
                    b["text"] == a["text"]
                    and b["label"] == a["label"]
                    and b["start"] == a["start"]
                    and b["end"] == a["end"]
                ):
                    unchanged.append((b, a))
                else:
                    modified.append((b, a))
            else:
                modified.append((b, a))
            matched_b.add(i)
            matched_a.add(j)

        # Priority 1: exact same [start, end]
        for i, b in enumerate(b_items):
            for j, a in enumerate(a_items):
                if j in matched_a:
                    continue
                if b["start"] == a["start"] and b["end"] == a["end"]:
                    _record_match(i, j)
                    break

        # Priority 2: exact same text and label
        for i, b in enumerate(b_items):
            if i in matched_b:
                continue
            for j, a in enumerate(a_items):
                if j in matched_a:
                    continue
                if b["text"] == a["text"] and b["label"] == a["label"]:
                    _record_match(i, j)
                    break

        # Priority 3–5: best IoU, then same source, then closest boundaries
        IOU_THRESHOLD = 0.3
        for i, b in enumerate(b_items):
            if i in matched_b:
                continue
            best_j = None
            best_key = None
            for j, a in enumerate(a_items):
                if j in matched_a:
                    continue
                iou = self._span_iou(b, a)
                if iou < IOU_THRESHOLD:
                    continue
                same_source = 1 if (b.get("source") == a.get("source")) else 0
                dist = self._boundary_distance(b, a)
                # Maximize IoU, then same source, then minimize boundary distance
                key = (iou, same_source, -dist)
                if best_key is None or key > best_key:
                    best_key = key
                    best_j = j
            if best_j is not None:
                _record_match(i, best_j)

        removed = [b for i, b in enumerate(b_items) if i not in matched_b]
        added = [a for j, a in enumerate(a_items) if j not in matched_a]

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged": unchanged,
        }

    def _format_diff(self, diff: dict[str, list[Any]]) -> str:
        lines = []
        if diff["added"]:
            lines.append("  [+] Added:")
            for a in diff["added"]:
                cand_str = f", candidates: {a['candidates']}" if a["candidates"] else ""
                asrt_str = f", assertions: {a['assertions']}" if a["assertions"] else ""
                lines.append(
                    f"      - \"{a['text']}\" [{a['start']}, {a['end']}] ({a['label']}){cand_str}{asrt_str}"
                )
        if diff["removed"]:
            lines.append("  [-] Removed:")
            for r in diff["removed"]:
                lines.append(
                    f"      - \"{r['text']}\" [{r['start']}, {r['end']}] ({r['label']})"
                )
        if diff["modified"]:
            lines.append("  [*] Modified:")
            for b, a in diff["modified"]:
                changes = []
                if b["text"] != a["text"]:
                    changes.append(f"text: \"{b['text']}\" -> \"{a['text']}\"")
                if b["start"] != a["start"] or b["end"] != a["end"]:
                    changes.append(
                        f"span: [{b['start']}, {b['end']}] -> [{a['start']}, {a['end']}]"
                    )
                if b["label"] != a["label"]:
                    changes.append(f"label: {b['label']} -> {a['label']}")
                if b["candidates"] != a["candidates"]:
                    changes.append(
                        f"candidates: {b['candidates']} -> {a['candidates']}"
                    )
                if b["assertions"] != a["assertions"]:
                    changes.append(
                        f"assertions: {b['assertions']} -> {a['assertions']}"
                    )

                lines.append(
                    f"      - \"{b['text']}\" [{b['start']}, {b['end']}] ({b['label']})"
                )
                lines.append(f"        -> {', '.join(changes)}")

        if not diff["added"] and not diff["removed"] and not diff["modified"]:
            lines.append("  (No changes)")
        return "\n".join(lines)

    def _format_linker_diagnostics(self, entity_snap: dict[str, Any]) -> str:
        """Extra diagnostics for linker-stage traces (not competition JSON)."""
        meta = entity_snap.get("metadata") or {}
        label = entity_snap.get("label", "")
        lines: list[str] = []

        if label == "THUỐC" or meta.get("ontology_drug_recall"):
            lines.append("      drug diagnostics:")
            lines.append(f"        drug_link: {meta.get('drug_link', '')}")
            lines.append(
                f"        ontology_drug_recall: {meta.get('ontology_drug_recall', False)}"
            )
            lines.append(f"        match: {meta.get('match', '')}")
            lines.append(f"        alias: {meta.get('alias', '')}")
            lines.append(
                f"        preset_rxcui_candidates: {meta.get('preset_rxcui_candidates', [])}"
            )
            lines.append(
                f"        preset_rxcui_count: {meta.get('preset_rxcui_count', '')}"
            )
            lines.append(f"        preset_used: {meta.get('preset_used', '')}")
            lines.append(
                f"        fallback_reason: {meta.get('drug_link_fallback_reason', '')}"
            )
            lines.append(f"        drug_similarity: {meta.get('drug_similarity', '')}")
            lines.append(f"        final_candidates: {entity_snap.get('candidates', [])}")

        if meta.get("is_disease_like") or "diagnosis_similarity" in meta:
            lines.append("      disease/symptom diagnostics:")
            lines.append(
                f"        best_diagnosis_id: {entity_snap.get('candidates', [])}"
            )
            lines.append(
                f"        diagnosis_similarity: {meta.get('diagnosis_similarity', '')}"
            )
            lines.append(
                f"        symptom_similarity: {meta.get('symptom_similarity', '')}"
            )
            lines.append(f"        final_type: {label}")

        return "\n".join(lines)

    def _format_all_mentions(
        self,
        mentions: list[EntityMention] | list[FinalEntity] | list[dict[str, Any]],
        include_linker_diagnostics: bool = False,
    ) -> str:
        if not mentions:
            return "  (No mentions)"
        lines = []

        snaps = [
            m
            if isinstance(m, dict) and "text" in m
            else self._snapshot_entity(m)
            for m in mentions
        ]

        sorted_mentions = sorted(
            snaps,
            key=lambda m: (
                m.get("start") if m.get("start") is not None else 0,
                m.get("end") if m.get("end") is not None else 0,
            ),
        )
        for m in sorted_mentions:
            start, end = m.get("start"), m.get("end")
            text = m.get("text", "")
            label = m.get("label", "")
            candidates = m.get("candidates", [])
            assertions = m.get("assertions", [])

            cand_str = f", candidates: {candidates}" if candidates else ""
            asrt_str = f", assertions: {assertions}" if assertions else ""
            lines.append(
                f"  - \"{text}\" [{start}, {end}] ({label}){cand_str}{asrt_str}"
            )
            if include_linker_diagnostics:
                diag = self._format_linker_diagnostics(m)
                if diag:
                    lines.append(diag)
        return "\n".join(lines)

    def process_document(self, document: Document) -> list[FinalEntity]:
        trace_steps = []

        # 0. Raw Input
        trace_steps.append({
            "step": "Input Document",
            "type": "input",
            "text_len": len(document.text),
            "text_preview": document.text[:200] + "..." if len(document.text) > 200 else document.text
        })

        # 1. Normalizer
        if self.normalizer:
            working_document = self.normalizer.normalize(document)
            norm_desc = f"Normalizer: {self.normalizer.__class__.__name__}"
            text_changed = working_document.text != document.text
            trace_steps.append({
                "step": norm_desc,
                "type": "normalization",
                "text_changed": text_changed,
                "text_len": len(working_document.text)
            })
        else:
            working_document = document

        # 2. NER
        mentions = self.ner.extract(working_document)
        snap = self._snapshot_entities(mentions)
        trace_steps.append({
            "step": f"NER Extraction: {self.ner.__class__.__name__}",
            "type": "ner",
            "mentions_count": len(mentions),
            "mentions": snap,
            "diff": self._diff_mentions([], snap)
        })

        # 3. Pre-classification postprocessors
        prev_snap = snap
        for postprocessor in self.pre_classification_postprocessors:
            mentions = postprocessor.apply(working_document, mentions)
            snap = self._snapshot_entities(mentions)
            trace_steps.append({
                "step": f"Pre-classification Postprocessor: {postprocessor.__class__.__name__}",
                "type": "postprocessor",
                "mentions_count": len(mentions),
                "mentions": snap,
                "diff": self._diff_mentions(prev_snap, snap)
            })
            prev_snap = snap

        # 4. Classifier
        mentions = self.classifier.classify(working_document, mentions)
        snap = self._snapshot_entities(mentions)
        trace_steps.append({
            "step": f"Classifier: {self.classifier.__class__.__name__}",
            "type": "classifier",
            "mentions_count": len(mentions),
            "mentions": snap,
            "diff": self._diff_mentions(prev_snap, snap)
        })
        prev_snap = snap

        # 5. Post-classification postprocessors
        for postprocessor in self.post_classification_postprocessors:
            mentions = postprocessor.apply(working_document, mentions)
            snap = self._snapshot_entities(mentions)
            trace_steps.append({
                "step": f"Post-classification Postprocessor: {postprocessor.__class__.__name__}",
                "type": "postprocessor",
                "mentions_count": len(mentions),
                "mentions": snap,
                "diff": self._diff_mentions(prev_snap, snap)
            })
            prev_snap = snap

        # 6. Linker
        final_entities = self.linker.link(working_document, mentions)
        entity_snap = self._snapshot_entities(final_entities)
        trace_steps.append({
            "step": f"Entity Linker: {self.linker.__class__.__name__}",
            "type": "linker",
            "entities_count": len(final_entities),
            "entities": entity_snap,
            "diff": self._diff_mentions(prev_snap, entity_snap)
        })
        prev_entity_snap = entity_snap

        # 7. Assertion detector
        final_entities = self.assertion_detector.apply(working_document, final_entities)
        entity_snap = self._snapshot_entities(final_entities)
        trace_steps.append({
            "step": f"Assertion Detector: {self.assertion_detector.__class__.__name__}",
            "type": "assertion_detector",
            "entities_count": len(final_entities),
            "entities": entity_snap,
            "diff": self._diff_mentions(prev_entity_snap, entity_snap)
        })

        # Build human-readable text trace
        txt_trace = []
        txt_trace.append("=" * 80)
        txt_trace.append(f"PIPELINE TRACE LOG FOR DOCUMENT: {document.doc_id}")
        txt_trace.append("=" * 80)

        for idx, step in enumerate(trace_steps):
            txt_trace.append(f"\n[Step {idx}] {step['step']}")
            txt_trace.append("-" * 40)
            if step["type"] == "input":
                txt_trace.append(f"  Length: {step['text_len']} characters")
                txt_trace.append("  Content Preview:")
                txt_trace.append(f"  \"\"\"\n  {step['text_preview']}\n  \"\"\"")
            elif step["type"] == "normalization":
                txt_trace.append(f"  Text changed: {step['text_changed']}")
                txt_trace.append(f"  Length after normalization: {step['text_len']} characters")
            elif step["type"] in ("ner", "postprocessor", "classifier", "linker", "assertion_detector"):
                count_lbl = "mentions" if step["type"] not in ("linker", "assertion_detector") else "entities"
                item_lbl = "Mentions" if step["type"] not in ("linker", "assertion_detector") else "Entities"
                txt_trace.append(f"  Total {count_lbl}: {step.get('mentions_count', step.get('entities_count', 0))}")
                txt_trace.append("  Changes in this step:")
                txt_trace.append(self._format_diff(step["diff"]))
                txt_trace.append(f"  All current {item_lbl.lower()}:")
                txt_trace.append(
                    self._format_all_mentions(
                        step.get("mentions", step.get("entities", [])),
                        include_linker_diagnostics=(step["type"] == "linker"),
                    )
                )

        txt_trace.append("\n" + "=" * 80)
        txt_trace.append("END OF TRACE")
        txt_trace.append("=" * 80)

        trace_str = "\n".join(txt_trace)

        # Save to document metadata
        document.metadata["trace_steps"] = trace_steps
        document.metadata["trace_txt"] = trace_str

        return final_entities
