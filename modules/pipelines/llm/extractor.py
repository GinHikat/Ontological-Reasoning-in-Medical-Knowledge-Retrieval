"""One-pass schema-aware LLM extractor (shared prompts for diagnostic + competition)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from modules.core.config import ProjectPaths

LLMMode = Literal["diagnostic", "competition"]

TRACK_ROOT = Path(__file__).resolve().parent
PROMPT_SCHEMA_PATH = TRACK_ROOT / "prompts" / "competition_schema.md"
SCHEMA_DIR = TRACK_ROOT / "schemas"


def load_competition_schema_prompt() -> str:
    return PROMPT_SCHEMA_PATH.read_text(encoding="utf-8")


def load_json_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def extraction_system_prompt() -> str:
    """Same prompt text for OpenRouter diagnostic and self-hosted competition."""
    return (
        "You are the primary clinical entity extractor for a Vietnamese medical "
        "competition schema.\n"
        "Return a complete final entity list for the document.\n"
        "Do not invent ontology IDs.\n"
        "Do not explain. Do not write long reasoning.\n\n"
        f"{load_competition_schema_prompt()}\n\n"
        "Internal checklist before returning:\n"
        "1. Find all valid entities belonging to the five output classes.\n"
        "2. Omit procedures, interventions, devices, headings, demographics, "
        "anatomy alone and generic status.\n"
        "3. Use minimal meaningful symptom spans.\n"
        "4. Use diagnosis spans with clinically meaningful specificity.\n"
        "5. Use maximal contiguous medication spans.\n"
    )


def mode_banner(mode: LLMMode) -> str:
    if mode == "diagnostic":
        return (
            "EXTERNAL_API_DIAGNOSTIC_ONLY — OpenRouter frontier teacher. "
            "Not competition-compliant."
        )
    return (
        "COMPETITION mode — self-hosted model ≤9B on localhost only. "
        "No external LLM APIs."
    )


def default_output_dir(mode: LLMMode) -> Path:
    root = ProjectPaths().root
    if mode == "diagnostic":
        return root / "output" / "llm_diagnostic"
    return root / "output" / "llm_competition"
