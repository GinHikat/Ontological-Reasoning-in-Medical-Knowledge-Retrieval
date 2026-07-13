from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.components.linking.hybrid import HybridEntityLinker
from modules.components.postprocessing.drug_ontology_provenance import (
    DrugOntologyProvenanceTransferPostProcessor,
)
from modules.core.constants import TARGET_LABEL_DRUG, TARGET_LABEL_SYMPTOM
from modules.core.schemas import Document, EntityMention, Span
from modules.pipelines.factory import available_pipelines


def _drug(
    text: str,
    start: int,
    end: int,
    metadata: dict | None = None,
    source: str = "ner",
    label: str = TARGET_LABEL_DRUG,
) -> EntityMention:
    return EntityMention(
        text=text,
        label=label,
        span=Span(start, end),
        confidence=0.9,
        source=source,
        metadata=dict(metadata or {}),
    )


class RescueLinkerTests(unittest.TestCase):
    def _linker(self, mode: str = "rescue_unlinked") -> HybridEntityLinker:
        store = MagicMock()
        bundle = MagicMock()
        bundle.drugs = MagicMock()
        bundle.drugs.empty = False
        bundle.drug_embeddings = np.zeros((1, 2))
        store.load.return_value = bundle
        return HybridEntityLinker(
            dictionary_store=store,
            preset_drug_link_mode=mode,
        )

    def _run_with_v7(
        self,
        linker: HybridEntityLinker,
        mention: EntityMention,
        v7_candidates: list[str],
    ):
        with patch.object(
            linker, "_sapbert_drug_candidates", return_value=list(v7_candidates)
        ) as sap:
            out = linker.link(Document("d", mention.text), [mention])
            return out, sap

    def test_a_preserve_existing_v7_candidate(self):
        linker = self._linker("rescue_unlinked")
        mention = _drug(
            "methadone",
            0,
            9,
            {
                "ontology_drug_recall": True,
                "match": "exact_norm",
                "preset_rxcui_candidates": ["222"],
            },
            source="ontology_drug_recall",
        )
        out, sap = self._run_with_v7(linker, mention, ["111"])
        sap.assert_called_once()
        self.assertEqual(out[0].candidates, ["111"])
        self.assertNotEqual(out[0].candidates, ["222"])
        self.assertEqual(out[0].metadata.get("drug_link"), "v7_candidate_preserved")

    def test_b_direct_rescue(self):
        linker = self._linker("rescue_unlinked")
        mention = _drug(
            "methadone",
            0,
            9,
            {
                "ontology_drug_recall": True,
                "match": "exact_norm",
                "preset_rxcui_candidates": ["222"],
            },
            source="ontology_drug_recall",
        )
        out, sap = self._run_with_v7(linker, mention, [])
        sap.assert_called_once()
        self.assertEqual(out[0].candidates, ["222"])
        self.assertEqual(out[0].metadata.get("drug_link"), "preset_rescue")
        self.assertEqual(
            out[0].metadata.get("drug_link_rescue_kind"), "direct_preset_rescue"
        )

    def test_c_transferred_rescue(self):
        linker = self._linker("rescue_unlinked")
        text = "coumadin 3.0 mg /ngày"
        mention = _drug(
            text,
            0,
            len(text),
            {
                "ontology_drug_evidence_transferred": True,
                "ontology_drug_evidence_source": "contained_donor",
                "ontology_drug_donor_text": "coumadin",
                "transferred_preset_rxcui_candidates": ["12345"],
                "transferred_preset_rxcui_count": 1,
            },
        )
        out, sap = self._run_with_v7(linker, mention, [])
        sap.assert_called_once()
        self.assertEqual(out[0].candidates, ["12345"])
        self.assertEqual(
            out[0].metadata.get("drug_link_rescue_kind"), "transferred_preset_rescue"
        )

    def test_d_ambiguous_donor(self):
        linker = self._linker("rescue_unlinked")
        mention = _drug(
            "methadone",
            0,
            9,
            {
                "ontology_drug_recall": True,
                "match": "exact_norm",
                "preset_rxcui_candidates": ["111", "222"],
            },
            source="ontology_drug_recall",
        )
        out, _ = self._run_with_v7(linker, mention, [])
        self.assertEqual(out[0].candidates, [])
        self.assertEqual(
            out[0].metadata.get("drug_link"), "unlinked_after_v7_and_rescue"
        )

    def test_e_conflicting_donors(self):
        linker = self._linker("rescue_unlinked")
        mention = _drug(
            "combo drug span",
            0,
            15,
            {
                "ontology_drug_evidence_conflict": True,
                "ontology_drug_evidence_candidate_ids": ["111", "222"],
                "ontology_drug_evidence_transferred": False,
            },
        )
        out, _ = self._run_with_v7(linker, mention, [])
        self.assertEqual(out[0].candidates, [])

    def test_f_same_id_multiple_donors_via_transfer_meta(self):
        linker = self._linker("rescue_unlinked")
        mention = _drug(
            "drug A and A again",
            0,
            18,
            {
                "ontology_drug_evidence_transferred": True,
                "transferred_preset_rxcui_candidates": ["111"],
                "ontology_drug_donor_texts": ["A", "A"],
            },
        )
        out, _ = self._run_with_v7(linker, mention, [])
        self.assertEqual(out[0].candidates, ["111"])

    def test_i_al_pain_no_override(self):
        linker = self._linker("rescue_unlinked")
        mention = _drug(
            "al pain",
            0,
            7,
            {
                "ontology_drug_recall": True,
                "match": "embedded_compact",
                "alias": "alpain",
                "preset_rxcui_candidates": ["602512"],
            },
            source="ontology_drug_recall",
        )
        out, sap = self._run_with_v7(linker, mention, ["152220"])
        sap.assert_called_once()
        self.assertEqual(out[0].candidates, ["152220"])
        self.assertNotEqual(out[0].candidates, ["602512"])

    def test_j_v7_disabled_mode(self):
        linker = self._linker("disabled")
        mention = _drug(
            "methadone",
            0,
            9,
            {
                "ontology_drug_recall": True,
                "match": "exact_norm",
                "preset_rxcui_candidates": ["12345"],
            },
            source="ontology_drug_recall",
        )
        mock_enc = MagicMock()
        mock_enc.encode_text.return_value = np.array([[0.1, 0.2]])
        with patch.object(linker, "_get_sapbert_en", return_value=mock_enc):
            with patch.object(
                linker, "_best_hybrid_match", return_value=("555", 0.9)
            ) as hybrid:
                out = linker.link(Document("d", "methadone"), [mention])
                hybrid.assert_called_once()
        self.assertEqual(out[0].candidates, ["555"])
        self.assertNotEqual(out[0].metadata.get("drug_link"), "preset_rescue")
        self.assertNotEqual(
            out[0].metadata.get("drug_link"), "preset_unambiguous_rxcui"
        )

    def test_k_old_v8_override_mode(self):
        linker = self._linker("override_unambiguous")
        mention = _drug(
            "methadone",
            0,
            9,
            {
                "ontology_drug_recall": True,
                "match": "exact_norm",
                "preset_rxcui_candidates": ["12345"],
            },
            source="ontology_drug_recall",
        )
        with patch.object(linker, "_get_sapbert_en") as sap:
            out = linker.link(Document("d", "methadone"), [mention])
            sap.assert_not_called()
        self.assertEqual(out[0].candidates, ["12345"])
        self.assertEqual(out[0].metadata.get("drug_link"), "preset_unambiguous_rxcui")

    def test_legacy_boolean_maps_to_override(self):
        store = MagicMock()
        store.load.return_value = MagicMock()
        linker = HybridEntityLinker(
            dictionary_store=store,
            use_unambiguous_preset_drug_rxcui=True,
        )
        self.assertEqual(linker.preset_drug_link_mode, "override_unambiguous")

    def test_defaults(self):
        sig = inspect.signature(HybridEntityLinker.__init__)
        self.assertFalse(sig.parameters["use_unambiguous_preset_drug_rxcui"].default)
        self.assertIsNone(sig.parameters["preset_drug_link_mode"].default)
        store = MagicMock()
        store.load.return_value = MagicMock()
        linker = HybridEntityLinker(dictionary_store=store)
        self.assertEqual(linker.preset_drug_link_mode, "disabled")


class ProvenanceTransferTests(unittest.TestCase):
    def setUp(self):
        self.proc = DrugOntologyProvenanceTransferPostProcessor()

    def _donor(self, text: str, start: int, end: int, rxcui: str = "12345"):
        return _drug(
            text,
            start,
            end,
            {
                "ontology_drug_recall": True,
                "match": "exact_norm",
                "alias": text,
                "preset_rxcui_candidates": [rxcui],
                "preset_rxcui_count": 1,
                "preset_rxcui_unambiguous": True,
            },
            source="ontology_drug_recall",
        )

    def test_c_transfer_to_dose_span(self):
        text = "coumadin 3.0 mg /ngày"
        donor = self._donor("coumadin", 0, 8, "12345")
        recipient = _drug(text, 0, len(text), source="ner")
        doc = Document("d", text)
        out = self.proc.apply(doc, [donor, recipient])
        self.assertEqual(len(out), 2)
        self.assertTrue(recipient.metadata.get("ontology_drug_evidence_transferred"))
        self.assertEqual(
            recipient.metadata.get("transferred_preset_rxcui_candidates"), ["12345"]
        )
        # Must not change identity fields
        self.assertEqual(recipient.text, text)
        self.assertEqual(recipient.label, TARGET_LABEL_DRUG)
        self.assertEqual(recipient.source, "ner")

    def test_e_conflicting_donors(self):
        recipient_text = "aspirin lasix"
        donor_a = self._donor("aspirin", 0, 7, "111")
        donor_b = self._donor("lasix", 8, 13, "222")
        recipient = _drug(recipient_text, 0, len(recipient_text), source="ner")
        doc = Document("d", recipient_text)
        self.proc.apply(doc, [donor_a, donor_b, recipient])
        self.assertTrue(recipient.metadata.get("ontology_drug_evidence_conflict"))
        self.assertFalse(
            recipient.metadata.get("ontology_drug_evidence_transferred", False)
        )
        self.assertEqual(
            recipient.metadata.get("ontology_drug_evidence_candidate_ids"),
            ["111", "222"],
        )

    def test_f_same_id_multiple_donors(self):
        text = "coumadin coumadin 5 mg"
        donor_a = self._donor("coumadin", 0, 8, "111")
        donor_b = self._donor("coumadin", 9, 17, "111")
        recipient = _drug(text, 0, len(text), source="ner")
        doc = Document("d", text)
        self.proc.apply(doc, [donor_a, donor_b, recipient])
        self.assertTrue(recipient.metadata.get("ontology_drug_evidence_transferred"))
        self.assertEqual(
            recipient.metadata.get("transferred_preset_rxcui_candidates"), ["111"]
        )

    def test_g_unsafe_giant_container(self):
        donor = self._donor("coumadin", 20, 28, "12345")
        sentence = (
            "Patient was given coumadin yesterday. Then the nurse noted bleeding "
            "and called the doctor about next steps for care."
        )
        # Place donor inside the sentence
        start = sentence.index("coumadin")
        end = start + len("coumadin")
        donor = self._donor("coumadin", start, end, "12345")
        recipient = _drug(sentence, 0, len(sentence), source="ner")
        doc = Document("d", sentence)
        self.proc.apply(doc, [donor, recipient])
        self.assertFalse(
            recipient.metadata.get("ontology_drug_evidence_transferred", False)
        )

    def test_h_different_labels(self):
        text = "coumadin pain"
        donor = self._donor("coumadin", 0, 8, "12345")
        recipient = _drug(
            text, 0, len(text), source="ner", label=TARGET_LABEL_SYMPTOM
        )
        doc = Document("d", text)
        self.proc.apply(doc, [donor, recipient])
        self.assertFalse(
            recipient.metadata.get("ontology_drug_evidence_transferred", False)
        )


class PipelineRegistrationTests(unittest.TestCase):
    def test_pipelines_registered(self):
        names = available_pipelines()
        self.assertIn("v7_structured", names)
        self.assertIn("v8_candidate_integrity", names)
        self.assertIn("v8_candidate_rescue", names)


if __name__ == "__main__":
    unittest.main()
