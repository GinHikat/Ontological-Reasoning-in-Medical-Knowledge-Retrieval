from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.components.linking.hybrid import HybridEntityLinker
from modules.core.constants import TARGET_LABEL_DRUG
from modules.core.ids import normalize_rxcui
from modules.core.schemas import Document, EntityMention, Span


class NormalizeRxcuiTests(unittest.TestCase):
    def test_int_and_str(self):
        self.assertEqual(normalize_rxcui(12345), "12345")
        self.assertEqual(normalize_rxcui("12345"), "12345")
        self.assertEqual(normalize_rxcui(" 12345 "), "12345")

    def test_invalid(self):
        self.assertIsNone(normalize_rxcui(None))
        self.assertIsNone(normalize_rxcui(""))
        self.assertIsNone(normalize_rxcui(" "))
        self.assertIsNone(normalize_rxcui("nan"))
        self.assertIsNone(normalize_rxcui("NaN"))

    def test_no_float_artifact(self):
        self.assertEqual(normalize_rxcui("12345.0"), "12345")
        self.assertNotEqual(normalize_rxcui(12345), "12345.0")
        self.assertNotEqual(normalize_rxcui("12345"), "12345.0")


class PresetDrugLinkingTests(unittest.TestCase):
    def _mention(self, metadata: dict, text: str = "methadone") -> EntityMention:
        return EntityMention(
            text=text,
            label=TARGET_LABEL_DRUG,
            span=Span(0, len(text)),
            confidence=0.9,
            source="ontology_drug_recall",
            metadata=metadata,
        )

    def _linker(self, enabled: bool = True) -> HybridEntityLinker:
        store = MagicMock()
        bundle = MagicMock()
        bundle.drugs = MagicMock()
        bundle.drugs.empty = False
        bundle.drug_embeddings = np.zeros((1, 2))
        store.load.return_value = bundle
        return HybridEntityLinker(
            dictionary_store=store,
            use_unambiguous_preset_drug_rxcui=enabled,
        )

    def test_a_unambiguous_exact(self):
        linker = self._linker(True)
        mention = self._mention(
            {
                "ontology_drug_recall": True,
                "match": "exact_norm",
                "preset_rxcui_candidates": ["12345"],
            }
        )
        with patch.object(linker, "_get_sapbert_en") as sap:
            out = linker.link(Document("d", "methadone"), [mention])
            sap.assert_not_called()
        self.assertEqual(out[0].candidates, ["12345"])
        self.assertEqual(out[0].metadata.get("drug_link"), "preset_unambiguous_rxcui")

    def test_b_unambiguous_embedded(self):
        linker = self._linker(True)
        mention = self._mention(
            {
                "ontology_drug_recall": True,
                "match": "embedded_compact",
                "preset_rxcui_candidates": ["67890"],
            }
        )
        with patch.object(linker, "_get_sapbert_en") as sap:
            out = linker.link(Document("d", "methadone"), [mention])
            sap.assert_not_called()
        self.assertEqual(out[0].candidates, ["67890"])

    def test_c_ambiguous_alias_falls_back(self):
        linker = self._linker(True)
        mention = self._mention(
            {
                "ontology_drug_recall": True,
                "match": "exact_norm",
                "preset_rxcui_candidates": ["111", "222"],
            }
        )
        mock_enc = MagicMock()
        mock_enc.encode_text.return_value = np.array([[0.1, 0.2]])
        with patch.object(linker, "_get_sapbert_en", return_value=mock_enc):
            with patch.object(
                linker, "_best_hybrid_match", return_value=("999", 0.95)
            ) as hybrid:
                out = linker.link(Document("d", "methadone"), [mention])
                hybrid.assert_called_once()
        self.assertEqual(out[0].candidates, ["999"])
        self.assertEqual(out[0].metadata.get("drug_link"), "sapbert_fallback")
        self.assertEqual(
            out[0].metadata.get("drug_link_fallback_reason"), "ambiguous_alias"
        )
        # Must not silently pick the first preset ID
        self.assertNotEqual(out[0].candidates, ["111"])

    def test_d_feature_disabled(self):
        linker = self._linker(False)
        mention = self._mention(
            {
                "ontology_drug_recall": True,
                "match": "exact_norm",
                "preset_rxcui_candidates": ["12345"],
            }
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
        self.assertNotEqual(out[0].metadata.get("drug_link"), "preset_unambiguous_rxcui")

    def test_e_fake_metadata_provenance(self):
        linker = self._linker(True)
        mention = EntityMention(
            text="methadone",
            label=TARGET_LABEL_DRUG,
            span=Span(0, 9),
            confidence=0.9,
            source="vihealthbert",
            metadata={
                "rxcui": "12345",
                "preset_rxcui_candidates": ["12345"],
            },
        )
        mock_enc = MagicMock()
        mock_enc.encode_text.return_value = np.array([[0.1, 0.2]])
        with patch.object(linker, "_get_sapbert_en", return_value=mock_enc):
            with patch.object(
                linker, "_best_hybrid_match", return_value=("777", 0.88)
            ) as hybrid:
                out = linker.link(Document("d", "methadone"), [mention])
                hybrid.assert_called_once()
        self.assertEqual(out[0].candidates, ["777"])
        self.assertEqual(
            out[0].metadata.get("drug_link_fallback_reason"), "not_ontology_recall"
        )

    def test_f_invalid_ids(self):
        linker = self._linker(True)
        mention = self._mention(
            {
                "ontology_drug_recall": True,
                "match": "exact_norm",
                "preset_rxcui_candidates": [None, "", " ", "nan", "NaN"],
            }
        )
        mock_enc = MagicMock()
        mock_enc.encode_text.return_value = np.array([[0.1, 0.2]])
        with patch.object(linker, "_get_sapbert_en", return_value=mock_enc):
            with patch.object(
                linker, "_best_hybrid_match", return_value=("888", 0.91)
            ) as hybrid:
                out = linker.link(Document("d", "methadone"), [mention])
                hybrid.assert_called_once()
        self.assertEqual(out[0].candidates, ["888"])
        self.assertEqual(
            out[0].metadata.get("drug_link_fallback_reason"), "invalid_preset"
        )

    def test_g_rxcui_string_integrity_in_preset(self):
        linker = self._linker(True)
        mention = self._mention(
            {
                "ontology_drug_recall": True,
                "match": "exact_norm",
                "preset_rxcui_candidates": [12345],
            }
        )
        with patch.object(linker, "_get_sapbert_en") as sap:
            out = linker.link(Document("d", "methadone"), [mention])
            sap.assert_not_called()
        self.assertEqual(out[0].candidates, ["12345"])
        self.assertNotIn("12345.0", out[0].candidates)


class DrugRecallOptInDefaultsTests(unittest.TestCase):
    def test_track_rxcui_sets_default_false(self):
        from modules.components.postprocessing.ontology_drug_recall import (
            OntologyDrugRecallPostProcessor,
        )

        proc = OntologyDrugRecallPostProcessor.__new__(OntologyDrugRecallPostProcessor)
        # Inspect signature default via constructor kwargs
        import inspect

        sig = inspect.signature(OntologyDrugRecallPostProcessor.__init__)
        self.assertFalse(sig.parameters["track_rxcui_sets"].default)

    def test_linker_flag_default_false(self):
        import inspect

        sig = inspect.signature(HybridEntityLinker.__init__)
        self.assertFalse(sig.parameters["use_unambiguous_preset_drug_rxcui"].default)


if __name__ == "__main__":
    unittest.main()
