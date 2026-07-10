from __future__ import annotations

import re
from typing import Any

from modules.components.postprocessing.base import BaseMentionPostProcessor
from modules.core.constants import TARGET_LABEL_DRUG
from modules.core.ids import normalize_rxcui
from modules.core.schemas import Document, EntityMention

# Hard expansion limits (characters). Do not loosen without new diagnostics.
MAX_PREFIX_EXTRA = 15
MAX_SUFFIX_EXTRA = 60
MAX_TOTAL_EXTRA = 70
MAX_RECIPIENT_LENGTH = 80

# Sentence-sized container markers outside a plausible medication expression.
_SENTENCE_MARKERS = ("\n", ". ", "; ", ": ")

# Allowed characters / tokens in the recipient text outside the donor span.
_MED_EXTENSION_TOKEN = re.compile(
    r"(?:"
    r"\d+(?:[.,]\d+)?"
    r"|mg|mcg|g|ml|%|iu|ui"
    r"|po|iv|im|sc"
    r"|bid|tid|qid|prn"
    r"|oral|tablet|capsule|injection|solution"
    r"|viên|ống|lọ|gói|ngày|giờ|lần"
    r"|dùng|uống|tiêm|truyền"
    r"|asa|qd|qhs|qam|qpm|qh|hr|hour|hours|day|daily|week"
    r"|x|lần/ngày|/ngày|/giờ"
    r")",
    flags=re.IGNORECASE,
)

_MED_CUE_PREFIX = re.compile(
    r"^(?:dùng|uống|tiêm|truyền)\s*",
    flags=re.IGNORECASE,
)


def _valid_unique_rxcuis(raw: object) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, (list, tuple, set)):
        return []
    unique: set[str] = set()
    for item in raw:
        normalized = normalize_rxcui(item)
        if normalized is not None:
            unique.add(normalized)
    return sorted(unique)


def _is_eligible_donor(mention: EntityMention) -> tuple[bool, list[str], str]:
    """Return (ok, unique_rxcuis, reject_reason)."""
    if mention.label != TARGET_LABEL_DRUG:
        return False, [], "not_drug"
    meta = mention.metadata or {}
    if meta.get("ontology_drug_recall") is not True:
        return False, [], "not_ontology_recall"
    if meta.get("match") not in {"exact_norm", "embedded_compact"}:
        return False, [], "bad_match_type"
    if "preset_rxcui_candidates" not in meta:
        return False, [], "missing_preset"
    valid = _valid_unique_rxcuis(meta.get("preset_rxcui_candidates"))
    if len(valid) == 0:
        return False, [], "invalid_rxcui"
    if len(valid) > 1:
        return False, valid, "ambiguous_rxcui"
    return True, valid, ""


def _extension_looks_like_medication(extension: str) -> bool:
    """True if text outside the donor looks compatible with a medication mention."""
    if not extension or not extension.strip():
        return True
    # Strip a small medication cue prefix once from the whole extension blob.
    remainder = extension
    # Remove allowed tokens / punctuation / whitespace iteratively.
    cleaned = remainder
    cleaned = _MED_CUE_PREFIX.sub(" ", cleaned)
    cleaned = _MED_EXTENSION_TOKEN.sub(" ", cleaned)
    cleaned = re.sub(r"[\s\-_/.,;:()\[\]{}+*%]+", " ", cleaned)
    cleaned = cleaned.strip()
    # Reject if leftover alphabetic content remains (likely non-dose words).
    letters = re.sub(r"[^A-Za-zÀ-ỹ]", "", cleaned)
    return len(letters) == 0


def _has_sentence_marker_outside_donor(
    recipient_text: str, donor_start: int, donor_end: int, recipient_start: int
) -> bool:
    """Reject if sentence markers appear in the recipient outside the donor span."""
    local_donor_start = donor_start - recipient_start
    local_donor_end = donor_end - recipient_start
    prefix = recipient_text[:local_donor_start]
    suffix = recipient_text[local_donor_end:]
    for marker in _SENTENCE_MARKERS:
        if marker in prefix or marker in suffix:
            return True
    return False


def _safe_geometry(
    recipient: EntityMention, donor: EntityMention
) -> tuple[bool, str]:
    """Geometric + size + sentence-marker checks (no extension text yet)."""
    rs, re_ = recipient.span.start, recipient.span.end
    ds, de = donor.span.start, donor.span.end
    if rs is None or re_ is None or ds is None or de is None:
        return False, "invalid_span"
    if not (rs <= ds and de <= re_):
        return False, "not_contained"
    if rs == ds and re_ == de:
        return False, "identical_span"

    prefix_extra = ds - rs
    suffix_extra = re_ - de
    total_extra = (re_ - rs) - (de - ds)
    if prefix_extra > MAX_PREFIX_EXTRA:
        return False, "prefix_too_long"
    if suffix_extra > MAX_SUFFIX_EXTRA:
        return False, "suffix_too_long"
    if total_extra > MAX_TOTAL_EXTRA:
        return False, "total_extra_too_long"
    if (re_ - rs) > MAX_RECIPIENT_LENGTH:
        return False, "recipient_too_long"

    if _has_sentence_marker_outside_donor(recipient.text, ds, de, rs):
        return False, "sentence_marker"

    return True, ""


def _remainder_after_donors(
    recipient: EntityMention, donors: list[EntityMention]
) -> str:
    """Recipient text with all donor spans removed (for medication-extension check)."""
    rs = int(recipient.span.start)
    chars = list(recipient.text)
    # Mask donor character ranges (relative to recipient).
    mask = [False] * len(chars)
    for donor in donors:
        local_s = int(donor.span.start) - rs
        local_e = int(donor.span.end) - rs
        for i in range(max(0, local_s), min(len(chars), local_e)):
            mask[i] = True
    return "".join(ch for ch, m in zip(chars, mask) if not m)


def _safe_containment(
    recipient: EntityMention, donor: EntityMention
) -> tuple[bool, str]:
    """Single-donor convenience check (geometry + extension)."""
    ok, reason = _safe_geometry(recipient, donor)
    if not ok:
        return False, reason
    rs = int(recipient.span.start)
    ds, de = int(donor.span.start), int(donor.span.end)
    extension = recipient.text[: ds - rs] + recipient.text[de - rs :]
    if not _extension_looks_like_medication(extension):
        return False, "unsafe_extension"
    return True, ""


class DrugOntologyProvenanceTransferPostProcessor(BaseMentionPostProcessor):
    """Transfer unambiguous ontology RxCUI evidence from short donors to longer recipients.

    Does NOT add/remove entities or change text/span/label/confidence.
    Only attaches diagnostic/transfer metadata to existing THUỐC mentions.
    """

    def apply(
        self, document: Document, mentions: list[EntityMention]
    ) -> list[EntityMention]:
        drugs = [
            m
            for m in mentions
            if m.label == TARGET_LABEL_DRUG
            and m.span.start is not None
            and m.span.end is not None
        ]

        donors: list[tuple[EntityMention, list[str]]] = []
        for m in drugs:
            ok, rxcuis, _reason = _is_eligible_donor(m)
            if ok:
                donors.append((m, rxcuis))

        rejections: list[dict[str, Any]] = []
        transfers: list[dict[str, Any]] = []

        for recipient in drugs:
            # Recipients that already carry direct ontology evidence do not need transfer.
            if (recipient.metadata or {}).get("ontology_drug_recall") is True:
                continue

            if recipient.label != TARGET_LABEL_DRUG:
                continue

            geometric: list[tuple[EntityMention, list[str]]] = []
            for donor, rxcuis in donors:
                if donor is recipient:
                    continue
                ok, reason = _safe_geometry(recipient, donor)
                if not ok:
                    if reason not in {"not_contained", "identical_span"}:
                        rejections.append(
                            {
                                "recipient_text": recipient.text,
                                "recipient_start": recipient.span.start,
                                "recipient_end": recipient.span.end,
                                "donor_text": donor.text,
                                "donor_start": donor.span.start,
                                "donor_end": donor.span.end,
                                "reason": reason,
                            }
                        )
                    continue
                geometric.append((donor, rxcuis))

            if not geometric:
                continue

            # Medication-extension check after removing ALL geometrically valid donors.
            donor_mentions = [d for d, _ in geometric]
            remainder = _remainder_after_donors(recipient, donor_mentions)
            if not _extension_looks_like_medication(remainder):
                rejections.append(
                    {
                        "recipient_text": recipient.text,
                        "recipient_start": recipient.span.start,
                        "recipient_end": recipient.span.end,
                        "reason": "unsafe_extension",
                        "n_donors": len(geometric),
                    }
                )
                continue

            matching = geometric
            rxcui_set: set[str] = set()
            for _d, rxcuis in matching:
                rxcui_set.update(rxcuis)

            meta = dict(recipient.metadata or {})

            if len(rxcui_set) > 1:
                meta["ontology_drug_evidence_conflict"] = True
                meta["ontology_drug_evidence_candidate_ids"] = sorted(rxcui_set)
                recipient.metadata = meta
                rejections.append(
                    {
                        "recipient_text": recipient.text,
                        "recipient_start": recipient.span.start,
                        "recipient_end": recipient.span.end,
                        "reason": "conflicting_donors",
                        "candidate_ids": sorted(rxcui_set),
                    }
                )
                continue

            unique = next(iter(rxcui_set))
            donor_texts = [d.text for d, _ in matching]
            donor_spans = [[d.span.start, d.span.end] for d, _ in matching]
            primary = matching[0][0]
            primary_meta = primary.metadata or {}

            meta["ontology_drug_evidence_transferred"] = True
            meta["ontology_drug_evidence_source"] = "contained_donor"
            meta["ontology_drug_donor_text"] = primary.text
            meta["ontology_drug_donor_start"] = primary.span.start
            meta["ontology_drug_donor_end"] = primary.span.end
            meta["ontology_drug_donor_match"] = primary_meta.get("match", "")
            meta["ontology_drug_donor_alias"] = primary_meta.get("alias", "")
            meta["transferred_preset_rxcui_candidates"] = [unique]
            meta["transferred_preset_rxcui_count"] = 1
            if len(matching) > 1:
                meta["ontology_drug_donor_texts"] = donor_texts
                meta["ontology_drug_donor_spans"] = donor_spans
            recipient.metadata = meta

            transfers.append(
                {
                    "recipient_text": recipient.text,
                    "recipient_start": recipient.span.start,
                    "recipient_end": recipient.span.end,
                    "donor_text": primary.text,
                    "donor_start": primary.span.start,
                    "donor_end": primary.span.end,
                    "donor_alias": primary_meta.get("alias", ""),
                    "rxcui": unique,
                    "n_donors": len(matching),
                }
            )

        document.metadata.setdefault("provenance_transfer_log", [])
        document.metadata["provenance_transfer_log"].extend(transfers)
        document.metadata.setdefault("provenance_rejection_log", [])
        document.metadata["provenance_rejection_log"].extend(rejections)

        return mentions
