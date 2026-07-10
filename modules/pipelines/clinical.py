from __future__ import annotations

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

    def _diff_mentions(
        self,
        before: list[EntityMention] | list[FinalEntity],
        after: list[EntityMention] | list[FinalEntity],
    ) -> dict[str, list[Any]]:
        def to_item(m: EntityMention | FinalEntity) -> dict[str, Any]:
            if hasattr(m, "span"):
                start, end = m.span.start, m.span.end
            else:
                start, end = None, None

            text = getattr(m, "text", "")
            label = getattr(m, "label", getattr(m, "type", ""))
            candidates = getattr(m, "candidates", [])
            assertions = getattr(m, "assertions", [])

            return {
                "start": start,
                "end": end,
                "text": text,
                "label": label,
                "candidates": list(candidates) if candidates else [],
                "assertions": list(assertions) if assertions else [],
            }

        b_items = [to_item(m) for m in before]
        a_items = [to_item(m) for m in after]

        matched_a = set()
        matched_b = set()

        modified = []
        unchanged = []

        # Pass 1: exact matches
        for i, b in enumerate(b_items):
            for j, a in enumerate(a_items):
                if j in matched_a:
                    continue
                if (
                    b["start"] == a["start"]
                    and b["end"] == a["end"]
                    and b["text"] == a["text"]
                    and b["label"] == a["label"]
                ):
                    if b["candidates"] == a["candidates"] and b["assertions"] == a["assertions"]:
                        unchanged.append((b, a))
                    else:
                        modified.append((b, a))
                    matched_b.add(i)
                    matched_a.add(j)
                    break

        # Pass 2: overlapping matches
        for i, b in enumerate(b_items):
            if i in matched_b:
                continue
            for j, a in enumerate(a_items):
                if j in matched_a:
                    continue
                if (
                    b["start"] is not None
                    and b["end"] is not None
                    and a["start"] is not None
                    and a["end"] is not None
                ):
                    overlap = max(
                        0, min(b["end"], a["end"]) - max(b["start"], a["start"])
                    )
                    if overlap > 0:
                        modified.append((b, a))
                        matched_b.add(i)
                        matched_a.add(j)
                        break

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
                    changes.append(f"candidates: {b['candidates']} -> {a['candidates']}")
                if b["assertions"] != a["assertions"]:
                    changes.append(f"assertions: {b['assertions']} -> {a['assertions']}")

                lines.append(
                    f"      - \"{b['text']}\" [{b['start']}, {b['end']}] ({b['label']})"
                )
                lines.append(f"        -> {', '.join(changes)}")

        if not diff["added"] and not diff["removed"] and not diff["modified"]:
            lines.append("  (No changes)")
        return "\n".join(lines)

    def _format_all_mentions(
        self, mentions: list[EntityMention] | list[FinalEntity]
    ) -> str:
        if not mentions:
            return "  (No mentions)"
        lines = []

        def get_span_start(m: EntityMention | FinalEntity) -> int:
            if hasattr(m, "span") and m.span.start is not None:
                return m.span.start
            return 0

        def get_span_end(m: EntityMention | FinalEntity) -> int:
            if hasattr(m, "span") and m.span.end is not None:
                return m.span.end
            return 0

        sorted_mentions = sorted(
            mentions, key=lambda m: (get_span_start(m), get_span_end(m))
        )
        for m in sorted_mentions:
            if hasattr(m, "span"):
                start, end = m.span.start, m.span.end
            else:
                start, end = None, None

            text = getattr(m, "text", "")
            label = getattr(m, "label", getattr(m, "type", ""))
            candidates = getattr(m, "candidates", [])
            assertions = getattr(m, "assertions", [])

            cand_str = f", candidates: {candidates}" if candidates else ""
            asrt_str = f", assertions: {assertions}" if assertions else ""
            lines.append(
                f"  - \"{text}\" [{start}, {end}] ({label}){cand_str}{asrt_str}"
            )
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
        trace_steps.append({
            "step": f"NER Extraction: {self.ner.__class__.__name__}",
            "type": "ner",
            "mentions_count": len(mentions),
            "mentions": list(mentions),
            "diff": self._diff_mentions([], mentions)
        })

        # 3. Pre-classification postprocessors
        prev_mentions = list(mentions)
        for postprocessor in self.pre_classification_postprocessors:
            mentions = postprocessor.apply(working_document, mentions)
            trace_steps.append({
                "step": f"Pre-classification Postprocessor: {postprocessor.__class__.__name__}",
                "type": "postprocessor",
                "mentions_count": len(mentions),
                "mentions": list(mentions),
                "diff": self._diff_mentions(prev_mentions, mentions)
            })
            prev_mentions = list(mentions)

        # 4. Classifier
        mentions = self.classifier.classify(working_document, mentions)
        trace_steps.append({
            "step": f"Classifier: {self.classifier.__class__.__name__}",
            "type": "classifier",
            "mentions_count": len(mentions),
            "mentions": list(mentions),
            "diff": self._diff_mentions(prev_mentions, mentions)
        })
        prev_mentions = list(mentions)

        # 5. Post-classification postprocessors
        for postprocessor in self.post_classification_postprocessors:
            mentions = postprocessor.apply(working_document, mentions)
            trace_steps.append({
                "step": f"Post-classification Postprocessor: {postprocessor.__class__.__name__}",
                "type": "postprocessor",
                "mentions_count": len(mentions),
                "mentions": list(mentions),
                "diff": self._diff_mentions(prev_mentions, mentions)
            })
            prev_mentions = list(mentions)

        # 6. Linker
        final_entities = self.linker.link(working_document, mentions)
        trace_steps.append({
            "step": f"Entity Linker: {self.linker.__class__.__name__}",
            "type": "linker",
            "entities_count": len(final_entities),
            "entities": list(final_entities),
            "diff": self._diff_mentions(prev_mentions, final_entities)
        })
        prev_entities = list(final_entities)

        # 7. Assertion detector
        final_entities = self.assertion_detector.apply(working_document, final_entities)
        trace_steps.append({
            "step": f"Assertion Detector: {self.assertion_detector.__class__.__name__}",
            "type": "assertion_detector",
            "entities_count": len(final_entities),
            "entities": list(final_entities),
            "diff": self._diff_mentions(prev_entities, final_entities)
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
                txt_trace.append(self._format_all_mentions(step.get("mentions", step.get("entities", []))))

        txt_trace.append("\n" + "=" * 80)
        txt_trace.append("END OF TRACE")
        txt_trace.append("=" * 80)

        trace_str = "\n".join(txt_trace)

        # Save to document metadata
        document.metadata["trace_steps"] = trace_steps
        document.metadata["trace_txt"] = trace_str

        return final_entities

