"""Training entry for the task-specific five-label + NONE NER model.

Design constraints (from schema audit):
  - direct competition labels
  - explicit NONE class
  - no Procedure → TÊN_XÉT_NGHIỆM remapping
  - type-specific span policies
"""

from __future__ import annotations

from pathlib import Path


def training_notes() -> str:
    return (
        "Train a token/span/GLiNER model on competition labels + NONE. "
        "Do not reuse RAW_LABEL_TO_TARGET Procedure→test remapping. "
        "Weak labels may be distilled from baseline_hybrid and/or the "
        "archived OpenRouter diagnostic gold "
        "(archives/openrouter_schema_teacher_free_2026-07-12/). "
        f"Legacy generic trainer still lives at "
        f"{Path('modules/model/training/train_ner.py')} — replace with "
        "direct five-label data before scoring this track."
    )


def main() -> None:
    print(training_notes())


if __name__ == "__main__":
    main()
