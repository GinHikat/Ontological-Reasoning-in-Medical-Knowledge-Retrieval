"""Select reproducible OpenRouter model IDs for the schema teacher.

EXTERNAL_API_DIAGNOSTIC_ONLY.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from modules.external.openrouter_client import OpenRouterClient, atomic_write_json, load_dotenv_file

PREFERRED_FAMILIES = [
    ("anthropic", ["claude", "anthropic"]),
    ("google", ["gemini", "google"]),
    ("openai", ["openai", "gpt-"]),
]

FALLBACK_FAMILIES = [
    ("qwen", ["qwen"]),
    ("deepseek", ["deepseek"]),
    ("other", []),
]

# Heuristic exclusions for economy / tiny / router aliases
EXCLUDE_PATTERNS = re.compile(
    r"(^~|auto|router|free|nano|mini|lite|tiny|flash-lite|haiku|small|embed|moderation|whisper|tts|image|vision-preview|customtools|-fast$|/fast$)",
    re.I,
)

HIGH_CAPABILITY_HINTS = re.compile(
    r"(opus|sonnet-4|sonnet-3\.7|sonnet-4|gemini-2\.5-pro|gemini-3|gpt-4\.1|gpt-5|o3|o4|qwen3|deepseek-r1|deepseek-v3)",
    re.I,
)


@dataclass
class SelectedModel:
    model_id: str
    family: str
    context_length: int | None
    supports_structured_outputs: bool | None
    pricing: dict[str, Any]
    reason: str
    role: str


def _family_of(model_id: str) -> str:
    mid = model_id.lower()
    for name, needles in PREFERRED_FAMILIES + FALLBACK_FAMILIES[:-1]:
        if any(n in mid for n in needles):
            return name
    if mid.startswith("anthropic/"):
        return "anthropic"
    if mid.startswith("google/"):
        return "google"
    if mid.startswith("openai/"):
        return "openai"
    if mid.startswith("qwen/") or "qwen" in mid:
        return "qwen"
    if "deepseek" in mid:
        return "deepseek"
    return mid.split("/", 1)[0] if "/" in mid else "other"


def _supports_structured(meta: dict[str, Any]) -> bool | None:
    params = meta.get("supported_parameters") or meta.get("supported_parameter") or []
    if isinstance(params, list):
        joined = " ".join(str(p) for p in params).lower()
        if "structured" in joined or "response_format" in joined or "json_schema" in joined:
            return True
    arch = meta.get("architecture") or {}
    modality = str(arch.get("modality") or arch.get("input_modalities") or "")
    # unknown → None
    _ = modality
    return None


def _is_text_chat(meta: dict[str, Any]) -> bool:
    arch = meta.get("architecture") or {}
    modality = str(arch.get("modality") or "").lower()
    if modality and "text" not in modality and "->" not in modality:
        # e.g. image->text only
        if modality.startswith("image") or modality.startswith("audio"):
            return False
    output_mods = arch.get("output_modalities") or []
    if output_mods and "text" not in output_mods:
        return False
    mid = str(meta.get("id") or "")
    if EXCLUDE_PATTERNS.search(mid) and not HIGH_CAPABILITY_HINTS.search(mid):
        return False
    return True


def _context_len(meta: dict[str, Any]) -> int:
    for key in ("context_length", "top_provider"):
        val = meta.get(key)
        if isinstance(val, int):
            return val
        if isinstance(val, dict) and isinstance(val.get("context_length"), int):
            return int(val["context_length"])
    return int(meta.get("context_length") or 0)


def _score_model(meta: dict[str, Any]) -> float:
    mid = str(meta.get("id") or "")
    score = 0.0
    if HIGH_CAPABILITY_HINTS.search(mid):
        score += 50
    ctx = _context_len(meta)
    score += min(ctx / 10000.0, 20)
    if _supports_structured(meta):
        score += 5
    # prefer newer / higher pricing as rough capability proxy without selecting economy
    pricing = meta.get("pricing") or {}
    try:
        prompt = float(pricing.get("prompt") or 0)
        score += min(prompt * 1e6, 15)  # higher prompt price → often stronger
    except (TypeError, ValueError):
        pass
    if EXCLUDE_PATTERNS.search(mid):
        score -= 40
    return score


def _pick_best_for_family(
    models: list[dict[str, Any]], family: str, used_ids: set[str]
) -> dict[str, Any] | None:
    cands = []
    for m in models:
        mid = str(m.get("id") or "")
        if mid in used_ids:
            continue
        if _family_of(mid) != family:
            continue
        if not _is_text_chat(m):
            continue
        if _context_len(m) < 32000 and not HIGH_CAPABILITY_HINTS.search(mid):
            # require decent context for full clinical docs
            continue
        cands.append(m)
    if not cands:
        return None
    cands.sort(key=_score_model, reverse=True)
    return cands[0]


def validate_configured_models(
    client: OpenRouterClient, model_ids: list[str]
) -> list[dict[str, Any]]:
    catalog = {str(m.get("id")): m for m in client.list_models()}
    missing = [mid for mid in model_ids if mid not in catalog]
    if missing:
        raise RuntimeError(
            "Configured OpenRouter model(s) not found in Models API: "
            + ", ".join(missing)
            + ". Do not silently replace explicitly selected models."
        )
    return [catalog[mid] for mid in model_ids]


def auto_select_models(client: OpenRouterClient) -> tuple[list[SelectedModel], SelectedModel]:
    catalog = client.list_models()
    used: set[str] = set()
    extractors: list[SelectedModel] = []

    family_order = [f for f, _ in PREFERRED_FAMILIES] + [f for f, _ in FALLBACK_FAMILIES]
    for family in family_order:
        if len(extractors) >= 3:
            break
        pick = _pick_best_for_family(catalog, family, used)
        if pick is None:
            continue
        mid = str(pick["id"])
        used.add(mid)
        extractors.append(
            SelectedModel(
                model_id=mid,
                family=_family_of(mid),
                context_length=_context_len(pick) or None,
                supports_structured_outputs=_supports_structured(pick),
                pricing=dict(pick.get("pricing") or {}),
                reason=f"Auto-selected high-capability {family} family model "
                f"(score={_score_model(pick):.1f}, ctx={_context_len(pick)}).",
                role=f"extractor_{chr(ord('A') + len(extractors))}",
            )
        )

    if len(extractors) < 3:
        # fill from remaining high-scoring distinct families
        remaining = sorted(
            [m for m in catalog if str(m.get("id")) not in used and _is_text_chat(m)],
            key=_score_model,
            reverse=True,
        )
        for m in remaining:
            if len(extractors) >= 3:
                break
            mid = str(m["id"])
            fam = _family_of(mid)
            if any(e.family == fam for e in extractors):
                continue
            used.add(mid)
            extractors.append(
                SelectedModel(
                    model_id=mid,
                    family=fam,
                    context_length=_context_len(m) or None,
                    supports_structured_outputs=_supports_structured(m),
                    pricing=dict(m.get("pricing") or {}),
                    reason=f"Fallback fill from family {fam}.",
                    role=f"extractor_{chr(ord('A') + len(extractors))}",
                )
            )

    if len(extractors) < 3:
        raise RuntimeError(
            f"Could not select 3 distinct-family extractor models; got {len(extractors)}"
        )

    # Judge: strongest among extractors or a stronger unused model of same/other family
    judge_cand = max(
        [e for e in extractors],
        key=lambda e: _score_model({"id": e.model_id, "pricing": e.pricing, "context_length": e.context_length or 0}),
    )
    # Prefer a separate stronger model if available
    stronger = None
    for m in sorted(catalog, key=_score_model, reverse=True)[:30]:
        mid = str(m.get("id") or "")
        if not _is_text_chat(m):
            continue
        if _context_len(m) < 32000:
            continue
        if mid in {e.model_id for e in extractors}:
            continue
        stronger = m
        break
    if stronger is not None and _score_model(stronger) >= _score_model(
        {"id": judge_cand.model_id, "pricing": judge_cand.pricing, "context_length": judge_cand.context_length or 0}
    ):
        mid = str(stronger["id"])
        judge = SelectedModel(
            model_id=mid,
            family=_family_of(mid),
            context_length=_context_len(stronger) or None,
            supports_structured_outputs=_supports_structured(stronger),
            pricing=dict(stronger.get("pricing") or {}),
            reason="Selected as separate high-capability judge (independent call).",
            role="judge",
        )
    else:
        judge = SelectedModel(
            model_id=judge_cand.model_id,
            family=judge_cand.family,
            context_length=judge_cand.context_length,
            supports_structured_outputs=judge_cand.supports_structured_outputs,
            pricing=judge_cand.pricing,
            reason="Judge reuses strongest extractor model ID; judge call is independent.",
            role="judge",
        )
    return extractors, judge


def write_model_selection_md(
    path: Path,
    extractors: list[SelectedModel],
    judge: SelectedModel,
    mode: str,
) -> None:
    lines = [
        "# OpenRouter model selection",
        "",
        "**Compliance:** `EXTERNAL_API_DIAGNOSTIC_ONLY`",
        "",
        f"**Selection mode:** `{mode}`",
        "",
        "## Extractors",
        "",
        "| Role | Model ID | Family | Context | Structured outputs | Reason |",
        "|------|----------|--------|--------:|--------------------|--------|",
    ]
    for e in extractors:
        lines.append(
            f"| {e.role} | `{e.model_id}` | {e.family} | {e.context_length or 'n/a'} | "
            f"{e.supports_structured_outputs} | {e.reason} |"
        )
    lines += [
        "",
        "## Judge",
        "",
        f"- **Model ID:** `{judge.model_id}`",
        f"- **Family:** {judge.family}",
        f"- **Context:** {judge.context_length or 'n/a'}",
        f"- **Structured outputs:** {judge.supports_structured_outputs}",
        f"- **Reason:** {judge.reason}",
        "",
        "## Pricing metadata",
        "",
    ]
    for e in extractors + [judge]:
        lines.append(f"### `{e.model_id}`")
        lines.append("```json")
        lines.append(json.dumps(e.pricing, indent=2))
        lines.append("```")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def select_models(
    client: OpenRouterClient | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    load_dotenv_file()
    own_client = client is None
    client = client or OpenRouterClient()
    try:
        extractors_env = os.environ.get("OPENROUTER_EXTRACTOR_MODELS", "").strip()
        judge_env = os.environ.get("OPENROUTER_JUDGE_MODEL", "").strip()
        if extractors_env and judge_env:
            ids = [x.strip() for x in extractors_env.split(",") if x.strip()]
            if len(ids) != 3:
                raise RuntimeError(
                    "OPENROUTER_EXTRACTOR_MODELS must list exactly 3 model IDs when set"
                )
            metas = validate_configured_models(client, ids + [judge_env])
            extractors = []
            for i, (mid, meta) in enumerate(zip(ids, metas[:3])):
                extractors.append(
                    SelectedModel(
                        model_id=mid,
                        family=_family_of(mid),
                        context_length=_context_len(meta) or None,
                        supports_structured_outputs=_supports_structured(meta),
                        pricing=dict(meta.get("pricing") or {}),
                        reason="Explicitly configured via OPENROUTER_EXTRACTOR_MODELS; validated against Models API.",
                        role=f"extractor_{chr(ord('A') + i)}",
                    )
                )
            jmeta = metas[3]
            judge = SelectedModel(
                model_id=judge_env,
                family=_family_of(judge_env),
                context_length=_context_len(jmeta) or None,
                supports_structured_outputs=_supports_structured(jmeta),
                pricing=dict(jmeta.get("pricing") or {}),
                reason="Explicitly configured via OPENROUTER_JUDGE_MODEL; validated against Models API.",
                role="judge",
            )
            mode = "explicit_env"
        else:
            extractors, judge = auto_select_models(client)
            mode = "auto_models_api"
            # persist selection into env file? no — write analysis only; runner uses returned IDs

        report = report_path or Path("analysis/openrouter_teacher/model_selection.md")
        write_model_selection_md(report, extractors, judge, mode)
        out = {
            "mode": mode,
            "extractors": [asdict(e) for e in extractors],
            "judge": asdict(judge),
        }
        atomic_write_json(
            Path("analysis/openrouter_teacher/model_selection.json"), out
        )
        return out
    finally:
        if own_client:
            client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Select OpenRouter models")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("analysis/openrouter_teacher/model_selection.md"),
    )
    args = parser.parse_args()
    result = select_models(report_path=args.report)
    # print IDs only (no secrets)
    print("mode:", result["mode"])
    for e in result["extractors"]:
        print(f"{e['role']}: {e['model_id']}")
    print("judge:", result["judge"]["model_id"])


if __name__ == "__main__":
    main()
