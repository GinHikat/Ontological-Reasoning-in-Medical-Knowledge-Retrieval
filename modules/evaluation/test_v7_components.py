from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.components.assertions.rule_based import RuleBasedAssertionDetector
from modules.components.postprocessing.lab_pair_recall import LabPairRecallPostProcessor
from modules.components.postprocessing.ontology_drug_recall import (
    OntologyDrugRecallPostProcessor,
    normalize_with_map,
)
from modules.components.postprocessing.section_recall import (
    SectionAwareRecallPostProcessor,
)
from modules.components.structure.section_parser import VietnameseClinicalSectionParser
from modules.core.constants import (
    TARGET_LABEL_DIAGNOSIS,
    TARGET_LABEL_DRUG,
    TARGET_LABEL_SYMPTOM,
    TARGET_LABEL_TEST_NAME,
    TARGET_LABEL_TEST_RESULT,
)
from modules.core.schemas import Document, FinalEntity, Span


class SectionParserTests(unittest.TestCase):
    def test_parses_major_and_minor_sections(self):
        text = (
            "1. Tiền sử bệnh\n"
            "Các bệnh lý mãn tính\n"
            "- cường cận giáp nguyên phát\n"
            "2. Bệnh sử hiện tại\n"
            "Lý do nhập viện: buồn nôn\n"
            "Triệu chứng hiện tại\n"
            "- đau ngực\n"
            "3. Đánh giá tại bệnh viện\n"
            "Kết quả xét nghiệm\n"
            "kali là 6.6\n"
        )
        parser = VietnameseClinicalSectionParser()
        sections = parser.parse(text)
        names = [s.name for s in sections]
        self.assertIn("Tiền sử bệnh", names)
        self.assertIn("Bệnh lý mãn tính", names)
        self.assertIn("Triệu chứng hiện tại", names)
        self.assertIn("Kết quả xét nghiệm", names)
        # Offsets refer to original text
        for s in sections:
            self.assertGreaterEqual(s.start, 0)
            self.assertLessEqual(s.end, len(text))
            self.assertLessEqual(s.start, s.end)


class SectionRecallTests(unittest.TestCase):
    def test_symptom_bullets_exact_offsets(self):
        text = (
            "Triệu chứng hiện tại\n"
            "- buồn nôn\n"
            "- đau dai dẳng\n"
            "- táo bón\n"
        )
        doc = Document(doc_id="t", text=text)
        out = SectionAwareRecallPostProcessor().apply(doc, [])
        phrases = {m.text: (m.span.start, m.span.end) for m in out}
        for phrase in ("buồn nôn", "đau dai dẳng", "táo bón"):
            self.assertIn(phrase, phrases)
            s, e = phrases[phrase]
            self.assertEqual(text[s:e], phrase)
            self.assertEqual(out[0].source, "section_recall")

    def test_negated_symptom_strips_cue(self):
        text = "Triệu chứng hiện tại\n- Không có đau ngực\n"
        doc = Document(doc_id="t", text=text)
        out = SectionAwareRecallPostProcessor().apply(doc, [])
        self.assertTrue(any(m.text == "đau ngực" for m in out))
        m = next(m for m in out if m.text == "đau ngực")
        self.assertEqual(text[m.span.start : m.span.end], "đau ngực")


class LabPairTests(unittest.TestCase):
    def test_kali_pair(self):
        text = "kali là 6.6 mmol/l"
        doc = Document(doc_id="t", text=text)
        out = LabPairRecallPostProcessor().apply(doc, [])
        by_label = {}
        for m in out:
            by_label.setdefault(m.label, []).append(m)
        self.assertTrue(any(m.text == "kali" for m in by_label.get(TARGET_LABEL_TEST_NAME, [])))
        self.assertTrue(
            any(m.text == "6.6 mmol/l" for m in by_label.get(TARGET_LABEL_TEST_RESULT, []))
        )
        for m in out:
            self.assertEqual(text[m.span.start : m.span.end], m.text)

    def test_decimal_comma(self):
        text = "WBC:14,43"
        doc = Document(doc_id="t", text=text)
        out = LabPairRecallPostProcessor().apply(doc, [])
        results = [m for m in out if m.label == TARGET_LABEL_TEST_RESULT]
        self.assertTrue(any(m.text == "14,43" for m in results))
        m = next(m for m in results if m.text == "14,43")
        self.assertEqual(text[m.span.start : m.span.end], "14,43")


class DrugRecallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.processor = OntologyDrugRecallPostProcessor()
        # Force load once
        cls.processor._ensure_loaded()

    def test_normalize_index_map(self):
        text = "Dùngmethadonekéo dài"
        norm, index_map = normalize_with_map(text)
        self.assertEqual(len(norm), len(index_map))
        # Round-trip characters
        rebuilt = "".join(text[i] for i in index_map if not text[i].isspace())
        self.assertTrue(rebuilt.lower().replace(" ", "").startswith("d"))

    def test_concatenated_methadone(self):
        text = "- Dùngmethadonekéo dài"
        doc = Document(doc_id="t", text=text)
        # Put in drug section context
        full = "Thuốc trước khi nhập viện\n" + text + "\n"
        doc = Document(doc_id="t", text=full)
        out = self.processor.apply(doc, [])
        hits = [m for m in out if m.label == TARGET_LABEL_DRUG and "methadone" in m.text.lower()]
        self.assertTrue(hits, msg=f"No methadone in {[m.text for m in out]}")
        m = hits[0]
        self.assertEqual(full[m.span.start : m.span.end], m.text)
        self.assertIn("methadone", m.text.lower())
        self.assertEqual(m.text.lower(), "methadone")


class AssertionTests(unittest.TestCase):
    def setUp(self):
        self.detector = RuleBasedAssertionDetector(
            restrict_to_eligible_labels=True,
            use_section_parser=True,
            detect_family=True,
        )

    def _entity(self, text: str, phrase: str, etype: str) -> FinalEntity:
        start = text.index(phrase)
        end = start + len(phrase)
        return FinalEntity(
            text=phrase,
            type=etype,
            span=Span(start, end),
            candidates=[],
            assertions=[],
        )

    def test_negated_symptoms(self):
        cases = [
            "Không chảy máu mũi",
            "Không có đau ngực",
            "Không có khó thở",
            "Không có đau bụng",
        ]
        for line in cases:
            # extract expected phrase after negation
            phrase = line
            for prefix in ("Không có ", "Không "):
                if phrase.startswith(prefix):
                    phrase = phrase[len(prefix) :]
                    break
            doc = Document(doc_id="t", text=line)
            ent = self._entity(line, phrase, TARGET_LABEL_SYMPTOM)
            out = self.detector.apply(doc, [ent])
            self.assertIn("isNegated", out[0].assertions, msg=line)

    def test_contrastive_negation(self):
        text = "Không sốt nhưng có ho"
        doc = Document(doc_id="t", text=text)
        sot = self._entity(text, "sốt", TARGET_LABEL_SYMPTOM)
        ho = self._entity(text, "ho", TARGET_LABEL_SYMPTOM)
        out = self.detector.apply(doc, [sot, ho])
        by_text = {e.text: e.assertions for e in out}
        self.assertIn("isNegated", by_text["sốt"])
        self.assertEqual(by_text["ho"], [])

    def test_informant_not_family(self):
        text = "Theo lời người nhà kể bệnh nhân bị đau bụng"
        doc = Document(doc_id="t", text=text)
        ent = self._entity(text, "đau bụng", TARGET_LABEL_SYMPTOM)
        out = self.detector.apply(doc, [ent])
        self.assertNotIn("isFamily", out[0].assertions)

    def test_historical_diagnosis_section(self):
        text = "Các bệnh lý mãn tính\n- cường cận giáp nguyên phát\n"
        doc = Document(doc_id="t", text=text)
        phrase = "cường cận giáp nguyên phát"
        ent = self._entity(text, phrase, TARGET_LABEL_DIAGNOSIS)
        out = self.detector.apply(doc, [ent])
        self.assertIn("isHistorical", out[0].assertions)

    def test_historical_drug_section(self):
        text = "Thuốc trước khi nhập viện: coumadin 3.0 mg /ngày"
        doc = Document(doc_id="t", text=text)
        ent = self._entity(text, "coumadin", TARGET_LABEL_DRUG)
        out = self.detector.apply(doc, [ent])
        self.assertIn("isHistorical", out[0].assertions)


class NegationMultiTests(unittest.TestCase):
    def test_multi_negation_line(self):
        text = "Không có buồn nôn, không nôn"
        detector = RuleBasedAssertionDetector(restrict_to_eligible_labels=True)
        doc = Document(doc_id="t", text=text)
        entities = []
        for phrase in ("buồn nôn", "nôn"):
            # second nôn is the last one
            if phrase == "nôn":
                start = text.rfind(phrase)
            else:
                start = text.index(phrase)
            entities.append(
                FinalEntity(
                    text=phrase,
                    type=TARGET_LABEL_SYMPTOM,
                    span=Span(start, start + len(phrase)),
                )
            )
        out = detector.apply(doc, entities)
        for e in out:
            self.assertIn("isNegated", e.assertions, msg=e.text)


if __name__ == "__main__":
    unittest.main()
