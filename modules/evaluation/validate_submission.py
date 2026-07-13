"""Validate a competition submission directory (offsets, types, candidates)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.common.validation import validate_competition_entity


def validate_submission_dir(
    submission_dir: Path,
    *,
    notes_dir: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    for path in sorted(submission_dir.glob("*.json")):
        rows = json.loads(path.read_text(encoding="utf-8"))
        text = None
        if notes_dir is not None:
            note = notes_dir / f"{path.stem}.txt"
            if note.exists():
                text = note.read_text(encoding="utf-8")
        if not isinstance(rows, list):
            errors.append(f"{path.name}: root must be a list")
            continue
        for i, ent in enumerate(rows):
            for err in validate_competition_entity(ent, document_text=text):
                errors.append(f"{path.name}[{i}]: {err}")
    return errors


def main() -> None:
    p = argparse.ArgumentParser(description="Validate competition JSON submission dir")
    p.add_argument("submission_dir", type=Path)
    p.add_argument(
        "--notes-dir",
        type=Path,
        default=PROJECT_ROOT / "v_dataset" / "var" / "test",
    )
    args = p.parse_args()
    errs = validate_submission_dir(args.submission_dir, notes_dir=args.notes_dir)
    if errs:
        print(f"FAILED ({len(errs)} issues)")
        for e in errs[:50]:
            print(e)
        if len(errs) > 50:
            print(f"... and {len(errs) - 50} more")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
