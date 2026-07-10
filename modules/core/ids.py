from __future__ import annotations


def normalize_rxcui(value: object) -> str | None:
    """Normalize an RxCUI identifier to a clean digit string.

    RxCUIs are identifiers, not numerical measurements. Never cast through float.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() == "nan":
        return None
    # Reject float-like artifacts such as "12345.0" by requiring pure digits
    # after optional whitespace already stripped. If the value looks like an
    # integer with a trailing ".0", strip that safely without float casting.
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    if not text.isdigit():
        return None
    return text
