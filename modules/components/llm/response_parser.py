from __future__ import annotations

import json
import re
from typing import Any

from modules.components.llm.schemas import ALLOWED_LLM_TYPES, LLMProposal, VerifierDecision

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", flags=re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", flags=re.DOTALL | re.IGNORECASE)


class ResponseParseError(ValueError):
    """Raised when an LLM response cannot be parsed into the expected schema."""


def strip_think_blocks(text: str) -> str:
    return _THINK_BLOCK_RE.sub("", text).strip()


def _extract_json_object(text: str) -> Any:
    cleaned = strip_think_blocks(text)
    fence = _FENCE_RE.search(cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Attempt to locate the outermost JSON object.
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def _validate_line_id(line_id: Any) -> str:
    if not isinstance(line_id, str) or not line_id.strip():
        raise ResponseParseError(f"Invalid line_id: {line_id!r}")
    value = line_id.strip()
    if not re.fullmatch(r"L\d{3,}", value):
        raise ResponseParseError(f"line_id must look like L001, got {value!r}")
    return value


def parse_proposer_response(text: str) -> list[LLMProposal]:
    data = _extract_json_object(text)
    if not isinstance(data, dict):
        raise ResponseParseError("Root JSON must be an object")
    entities = data.get("entities")
    if not isinstance(entities, list):
        raise ResponseParseError("Root must contain an 'entities' array")

    proposals: list[LLMProposal] = []
    for i, item in enumerate(entities):
        if not isinstance(item, dict):
            raise ResponseParseError(f"entities[{i}] must be an object")
        line_id = _validate_line_id(item.get("line_id"))
        raw_text = item.get("text")
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ResponseParseError(f"entities[{i}].text must be a non-empty string")
        ent_type = item.get("type")
        if not isinstance(ent_type, str) or ent_type not in ALLOWED_LLM_TYPES:
            raise ResponseParseError(
                f"entities[{i}].type must be one of {sorted(ALLOWED_LLM_TYPES)}, "
                f"got {ent_type!r}"
            )
        # Reject accidental offset fields if the model emits them.
        for forbidden in ("start", "end", "position", "offset", "candidates", "assertions"):
            if forbidden in item:
                raise ResponseParseError(
                    f"entities[{i}] must not include '{forbidden}'"
                )
        proposals.append(
            LLMProposal(line_id=line_id, text=raw_text, type=ent_type)
        )
    return proposals


def parse_verifier_response(text: str) -> list[VerifierDecision]:
    data = _extract_json_object(text)
    if not isinstance(data, dict):
        raise ResponseParseError("Root JSON must be an object")
    entities = data.get("entities")
    if not isinstance(entities, list):
        raise ResponseParseError("Root must contain an 'entities' array")

    decisions: list[VerifierDecision] = []
    for i, item in enumerate(entities):
        if not isinstance(item, dict):
            raise ResponseParseError(f"entities[{i}] must be an object")
        proposal_id = item.get("proposal_id")
        if not isinstance(proposal_id, int):
            # Allow numeric strings.
            try:
                proposal_id = int(proposal_id)
            except (TypeError, ValueError) as exc:
                raise ResponseParseError(
                    f"entities[{i}].proposal_id must be an int"
                ) from exc
        accept = item.get("accept")
        if not isinstance(accept, bool):
            raise ResponseParseError(f"entities[{i}].accept must be a boolean")
        ent_type = item.get("type")
        if ent_type is not None:
            if not isinstance(ent_type, str) or ent_type not in ALLOWED_LLM_TYPES:
                raise ResponseParseError(
                    f"entities[{i}].type must be one of {sorted(ALLOWED_LLM_TYPES)} "
                    f"or omitted, got {ent_type!r}"
                )
        decisions.append(
            VerifierDecision(
                proposal_id=proposal_id,
                accept=accept,
                type=ent_type,
            )
        )
    return decisions


PROPOSER_SCHEMA_HINT = """{
  "entities": [
    {
      "line_id": "L003",
      "text": "tăng huyết áp",
      "type": "CHẨN_ĐOÁN"
    }
  ]
}"""

VERIFIER_SCHEMA_HINT = """{
  "entities": [
    {
      "proposal_id": 0,
      "accept": true,
      "type": "TRIỆU_CHỨNG"
    }
  ]
}"""


def build_repair_messages(
    *,
    role: str,
    invalid_response: str,
    schema_hint: str,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You repair malformed JSON for a clinical entity extraction pipeline. "
                "Return ONLY valid JSON matching the schema. No markdown. No prose."
            ),
        },
        {
            "role": "user",
            "content": (
                f"The previous {role} response was invalid.\n\n"
                f"Invalid response:\n{invalid_response}\n\n"
                f"Expected JSON schema:\n{schema_hint}\n\n"
                "Return only the repaired JSON object."
            ),
        },
    ]
