"""OpenRouter OpenAI-compatible client for EXTERNAL_API_DIAGNOSTIC_ONLY use.

Never logs or persists authentication headers or API keys.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_CACHE_DIR = Path("cache/openrouter_schema_teacher")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_secrets(
    text: str,
    api_key: str | None = None,
    extra_keys: list[str] | None = None,
) -> str:
    out = text
    for k in [api_key, *(extra_keys or [])]:
        if k:
            out = out.replace(k, "[REDACTED_API_KEY]")
    out = re.sub(r"sk-or-v1-[A-Za-z0-9]+", "[REDACTED_API_KEY]", out)
    out = re.sub(
        r"(?i)(authorization\s*[:=]\s*bearer\s+)(\S+)",
        r"\1[REDACTED]",
        out,
    )
    return out


def load_dotenv_file(path: Path | None = None) -> dict[str, str]:
    """Minimal .env loader (no python-dotenv dependency). Does not print values."""
    env_path = path or Path(".env")
    loaded: dict[str, str] = {}
    if not env_path.exists():
        return loaded
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        loaded[key] = val
        if key not in os.environ or not os.environ.get(key):
            os.environ[key] = val
    return loaded


def stable_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


_SCHEMA_UNSUPPORTED_KEYS = {
    "$schema",
    "description",
    "uniqueItems",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "pattern",
    "format",
}


def sanitize_response_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Strip JSON Schema keywords rejected by Anthropic/Azure structured output."""

    def _walk(o: Any) -> Any:
        if isinstance(o, dict):
            out: dict[str, Any] = {}
            for k, v in o.items():
                if k in _SCHEMA_UNSUPPORTED_KEYS:
                    continue
                out[k] = _walk(v)
            t = out.get("type")
            if isinstance(t, list):
                non_null = [x for x in t if x != "null"]
                if len(non_null) == 1:
                    out["type"] = non_null[0]
                elif non_null:
                    out["type"] = non_null
            if "enum" in out and isinstance(out["enum"], list):
                out["enum"] = [x for x in out["enum"] if x is not None]
                if not out["enum"]:
                    out.pop("enum")
            return out
        if isinstance(o, list):
            return [_walk(x) for x in o]
        return o

    return _walk(schema)


def extract_json_object(text: str) -> Any | None:
    """Best-effort JSON object extraction from model content / reasoning dumps."""
    if not text or not str(text).strip():
        return None
    raw = str(text).strip()
    # strip markdown fences
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Prefer object containing "entities" / "cluster_decisions" / "issues"
    for key in (
        "entities",
        "cluster_decisions",
        "selections",
        "issues",
        "actions",
    ):
        idx = raw.find(f'"{key}"')
        if idx < 0:
            continue
        start = raw.rfind("{", 0, idx)
        if start < 0:
            continue
        snippet = raw[start:]
        # balance braces
        depth = 0
        for i, ch in enumerate(snippet):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(snippet[: i + 1])
                    except json.JSONDecodeError:
                        break
    # fallback: greedy outermost object
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def is_free_model(model_id: str) -> bool:
    return ":free" in (model_id or "").lower() or (model_id or "").endswith("/free")


def default_reasoning_for_model(
    model_id: str, model_meta: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Free/reasoning endpoints often burn the whole budget on CoT unless constrained."""
    params = list((model_meta or {}).get("supported_parameters") or [])
    if "reasoning" not in params and "reasoning_effort" not in params and not is_free_model(
        model_id
    ):
        return None
    # Prefer none; some endpoints (gpt-oss:free) require reasoning and reject none.
    return {"effort": "low"}


def default_max_tokens_for_model(model_id: str) -> int:
    # Reasoning free models need headroom so JSON still fits after CoT.
    if is_free_model(model_id):
        return 24000
    return 8192



def request_hash(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_schema: dict[str, Any] | None,
    temperature: float,
    reasoning: dict[str, Any] | None = None,
) -> str:
    payload = {
        "model": model,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "response_schema": response_schema,
        "temperature": temperature,
        "reasoning": reasoning or {},
    }
    digest = hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()
    return digest


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{uuid.uuid4().hex}")
    try:
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


@dataclass
class UsageRecord:
    request_hash: str
    requested_model: str
    actual_model: str | None
    provider: str | None
    created_at: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    finish_reason: str | None
    cached: bool
    validation_status: str
    label: str = ""


@dataclass
class BudgetTracker:
    budget_usd: float | None
    spent_usd: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def remaining(self) -> float | None:
        if self.budget_usd is None:
            return None
        with self._lock:
            return max(0.0, self.budget_usd - self.spent_usd)

    def can_afford(self, estimated: float) -> bool:
        rem = self.remaining()
        if rem is None:
            return True
        return estimated <= rem

    def add(self, cost: float) -> None:
        with self._lock:
            self.spent_usd += max(0.0, cost)


@dataclass
class ChatResult:
    request_hash: str
    requested_model: str
    actual_model: str | None
    provider: str | None
    created_at: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    finish_reason: str | None
    raw_response: dict[str, Any]
    parsed_response: Any
    validation_status: str
    cached: bool
    content_text: str


class OpenRouterClient:
    """Bearer-auth chat-completions client with cache, retries, and cost tracking."""

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: Path | None = None,
        timeout_seconds: float = 300.0,
        max_retries: int = 4,
        max_concurrency: int = 3,
        budget_usd: float | None = None,
        usage_log_path: Path | None = None,
        pricing_hint: dict[str, dict[str, float]] | None = None,
    ) -> None:
        load_dotenv_file()
        primary = (api_key or os.environ.get("OPENROUTER_API_KEY") or "").strip()
        fallback = (os.environ.get("OPENROUTER_API_KEY_FALLBACK") or "").strip()
        self.api_keys: list[str] = []
        for k in (primary, fallback):
            if k and k not in self.api_keys:
                self.api_keys.append(k)
        if not self.api_keys:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        self._key_index = 0
        self.api_key = self.api_keys[0]
        self.cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = float(
            os.environ.get("OPENROUTER_REQUEST_TIMEOUT_SECONDS", timeout_seconds)
        )
        self.max_retries = int(os.environ.get("OPENROUTER_MAX_RETRIES", max_retries))
        self.semaphore = threading.Semaphore(
            int(os.environ.get("OPENROUTER_MAX_CONCURRENCY", max_concurrency))
        )
        budget_env = os.environ.get("OPENROUTER_BUDGET_USD", "").strip()
        if budget_usd is None and budget_env:
            budget_usd = float(budget_env)
        # Cap configured budget by live key remaining credits when available
        key_remaining = self._fetch_key_remaining()
        if key_remaining is not None and budget_usd is not None:
            budget_usd = min(budget_usd, max(0.0, key_remaining - 0.05))
        elif key_remaining is not None and budget_usd is None:
            budget_usd = max(0.0, key_remaining - 0.05)
        self.budget = BudgetTracker(budget_usd=budget_usd)
        self.usage_log_path = usage_log_path or (
            self.cache_dir / "usage_ledger.jsonl"
        )
        self.pricing_hint = pricing_hint or {}
        self._usage: list[UsageRecord] = []
        self._lock = threading.Lock()
        self._client = httpx.Client(
            base_url=OPENROUTER_BASE_URL,
            timeout=httpx.Timeout(self.timeout_seconds),
            headers=self._auth_headers(),
        )

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/local/openrouter_schema_teacher",
            "X-Title": "openrouter_schema_teacher_diagnostic",
        }

    def _rotate_api_key(self) -> bool:
        """Switch to next fallback key. Returns True if a different key is now active."""
        if len(self.api_keys) < 2:
            return False
        prev = self._key_index
        self._key_index = (self._key_index + 1) % len(self.api_keys)
        self.api_key = self.api_keys[self._key_index]
        self._client.headers.update(self._auth_headers())
        return self._key_index != prev

    def _redact(self, text: str) -> str:
        return _redact_secrets(text, extra_keys=self.api_keys)

    @property
    def key_count(self) -> int:
        return len(self.api_keys)

    def close(self) -> None:
        self._client.close()

    def _fetch_key_remaining(self) -> float | None:
        try:
            # temporary client headers without full init recursion
            import httpx as _httpx

            resp = _httpx.get(
                f"{OPENROUTER_BASE_URL}/key",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30.0,
            )
            if resp.status_code != 200:
                return None
            data = (resp.json() or {}).get("data") or {}
            rem = data.get("limit_remaining")
            return float(rem) if rem is not None else None
        except Exception:
            return None

    def __enter__(self) -> "OpenRouterClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def list_models(self) -> list[dict[str, Any]]:
        resp = self._request_with_retries("GET", "/models")
        data = resp.json()
        return list(data.get("data") or [])

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        model_meta: dict[str, Any] | None = None,
    ) -> float:
        """Estimate USD cost from pricing hint or OpenRouter model metadata."""
        prompt_price = None
        completion_price = None
        hint = self.pricing_hint.get(model)
        if hint:
            prompt_price = hint.get("prompt")
            completion_price = hint.get("completion")
        if model_meta:
            pricing = model_meta.get("pricing") or {}
            if prompt_price is None and pricing.get("prompt") is not None:
                prompt_price = float(pricing["prompt"])
            if completion_price is None and pricing.get("completion") is not None:
                completion_price = float(pricing["completion"])
        # OpenRouter pricing is typically USD per token as a string float
        if prompt_price is None:
            prompt_price = 0.0
        if completion_price is None:
            completion_price = 0.0
        return float(input_tokens) * float(prompt_price) + float(output_tokens) * float(
            completion_price
        )

    def preflight_cost_estimate(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        model_meta: dict[str, Any] | None = None,
        assumed_output_tokens: int = 2500,
    ) -> float:
        # rough char/4 token estimate for budget gate
        approx_in = max(1, (len(system_prompt) + len(user_prompt)) // 4)
        return self.estimate_cost(
            model, approx_in, assumed_output_tokens, model_meta=model_meta
        )

    def chat_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        schema_name: str = "response",
        temperature: float = 0.0,
        reasoning: dict[str, Any] | None = None,
        label: str = "",
        use_response_healing: bool = True,
        model_meta: dict[str, Any] | None = None,
        force: bool = False,
        structured_mode: str | None = None,
    ) -> ChatResult:
        """Chat with structured JSON.

        structured_mode:
          - None/"auto": try json_schema; on provider 400 fall back to prompt JSON
          - "json_schema": strict schema only
          - "prompt_json": schema in prompt + optional json_object / healing
        """
        safe_schema = sanitize_response_schema(response_schema)
        mode = structured_mode or "auto"
        params = []
        if model_meta:
            params = list(model_meta.get("supported_parameters") or [])
        supports_structured = (
            "structured_outputs" in params or "response_format" in params
        )
        if mode == "auto" and model_meta is not None and not supports_structured:
            mode = "prompt_json"

        if reasoning is None:
            reasoning = default_reasoning_for_model(model, model_meta)

        no_cot = (
            "\n\nCRITICAL OUTPUT RULES:\n"
            "- Put the final answer ONLY as JSON in the assistant content.\n"
            "- Do not put chain-of-thought in the content field.\n"
            "- No markdown fences.\n"
        )
        system_for_hash = system_prompt + no_cot
        user_for_hash = user_prompt
        if mode == "prompt_json":
            system_for_hash = (
                system_for_hash
                + "\n\nReturn ONLY valid JSON matching this schema "
                + f"(name={schema_name}):\n"
                + stable_json(safe_schema)
            )

        rh = request_hash(
            model=model,
            system_prompt=system_for_hash
            + f"|mode={mode}|reasoning={stable_json(reasoning or {})}",
            user_prompt=user_for_hash,
            response_schema=safe_schema,
            temperature=temperature,
            reasoning=reasoning,
        )
        cache_path = self.cache_dir / f"{rh}.json"
        if cache_path.exists() and not force:
            record = json.loads(cache_path.read_text(encoding="utf-8"))
            if (
                record.get("validation_status")
                in {"ok", "healed_json_extract", "cached"}
                and record.get("parsed_response") is not None
            ):
                result = ChatResult(
                    request_hash=rh,
                    requested_model=record.get("requested_model", model),
                    actual_model=record.get("actual_model"),
                    provider=record.get("provider"),
                    created_at=record.get("created_at", _utcnow_iso()),
                    input_tokens=int(record.get("input_tokens") or 0),
                    output_tokens=int(record.get("output_tokens") or 0),
                    estimated_cost=float(record.get("estimated_cost") or 0.0),
                    finish_reason=record.get("finish_reason"),
                    raw_response=record.get("raw_response") or {},
                    parsed_response=record.get("parsed_response"),
                    validation_status=record.get("validation_status", "cached"),
                    cached=True,
                    content_text=str(record.get("content_text") or ""),
                )
                self._record_usage(result, label=label or "cached")
                return result

        est = self.preflight_cost_estimate(
            model, system_for_hash, user_for_hash, model_meta=model_meta
        )
        if not self.budget.can_afford(est):
            raise RuntimeError(
                f"Budget stop: estimated ${est:.4f} would exceed remaining "
                f"${self.budget.remaining():.4f} of OPENROUTER_BUDGET_USD"
            )

        max_tokens = default_max_tokens_for_model(model)

        def _build_body(
            use_schema: bool, reasoning_cfg: dict[str, Any] | None
        ) -> dict[str, Any]:
            body_local: dict[str, Any] = {
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_for_hash},
                    {"role": "user", "content": user_prompt},
                ],
            }
            if use_schema:
                body_local["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "strict": True,
                        "schema": safe_schema,
                    },
                }
            elif supports_structured or "response_format" in params:
                body_local["response_format"] = {"type": "json_object"}
            if use_response_healing:
                body_local["plugins"] = [{"id": "response-healing"}]
            if reasoning_cfg:
                body_local["reasoning"] = reasoning_cfg
            return body_local

        try_schema = mode in {"auto", "json_schema"}
        reasoning_attempts: list[dict[str, Any] | None]
        if is_free_model(model):
            reasoning_attempts = [{"effort": "none"}, {"effort": "low"}, reasoning]
        else:
            reasoning_attempts = [reasoning]

        last_exc: Exception | None = None
        resp = None
        used_reasoning = reasoning
        content = ""
        raw: dict[str, Any] = {}
        finish_reason = None
        input_tokens = 0
        output_tokens = 0
        estimated_cost = 0.0
        actual_model = model
        provider = None
        parsed: Any = None
        validation_status = "parse_error"

        for rcfg in reasoning_attempts:
            body = _build_body(use_schema=try_schema, reasoning_cfg=rcfg)
            try:
                with self.semaphore:
                    resp = self._request_with_retries(
                        "POST", "/chat/completions", json_body=body
                    )
            except RuntimeError as exc:
                last_exc = exc
                msg = str(exc)
                if try_schema and mode == "auto" and "HTTP 400" in msg:
                    try:
                        body = _build_body(use_schema=False, reasoning_cfg=rcfg)
                        with self.semaphore:
                            resp = self._request_with_retries(
                                "POST", "/chat/completions", json_body=body
                            )
                        try_schema = False
                    except RuntimeError as exc2:
                        last_exc = exc2
                        msg = str(exc2)
                        resp = None
                if resp is None:
                    if "Reasoning is mandatory" in msg or "cannot be disabled" in msg:
                        continue
                    if "HTTP 400" in msg and is_free_model(model):
                        continue
                    if "HTTP 429" in msg and is_free_model(model):
                        continue
                    raise
            if resp is None:
                continue

            used_reasoning = rcfg
            raw = resp.json()
            raw_text = self._redact(stable_json(raw))
            raw = json.loads(raw_text)

            choice = (raw.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            content = message.get("content") or ""
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            if not content:
                for k in ("reasoning", "reasoning_content"):
                    alt = message.get(k)
                    if isinstance(alt, str) and alt.strip():
                        content = alt
                        break
            finish_reason = choice.get("finish_reason")
            usage = raw.get("usage") or {}
            input_tokens = int(
                usage.get("prompt_tokens") or usage.get("input_tokens") or 0
            )
            output_tokens = int(
                usage.get("completion_tokens") or usage.get("output_tokens") or 0
            )
            native_cost = None
            if isinstance(usage.get("cost"), (int, float)):
                native_cost = float(usage["cost"])
            estimated_cost = (
                native_cost
                if native_cost is not None
                else self.estimate_cost(
                    model, input_tokens, output_tokens, model_meta=model_meta
                )
            )
            actual_model = raw.get("model") or model
            provider = None
            meta = raw.get("provider")
            if isinstance(meta, str):
                provider = meta
            elif isinstance(raw.get("meta"), dict):
                provider = (raw["meta"] or {}).get("provider")

            parsed = extract_json_object(content)
            if parsed is None:
                validation_status = "empty_content" if not content else "parse_error"
                # free models: try next reasoning setting
                if is_free_model(model):
                    continue
                break
            try:
                json.loads(content.strip())
                validation_status = "ok"
            except Exception:
                validation_status = "healed_json_extract"
            break
        else:
            if last_exc is not None and parsed is None and not raw:
                raise RuntimeError(self._redact(str(last_exc)))

        result = ChatResult(
            request_hash=rh,
            requested_model=model,
            actual_model=actual_model,
            provider=provider,
            created_at=_utcnow_iso(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=estimated_cost,
            finish_reason=finish_reason,
            raw_response=raw,
            parsed_response=parsed,
            validation_status=validation_status,
            cached=False,
            content_text=content,
        )
        if validation_status in {"ok", "healed_json_extract"} and parsed is not None:
            record = {
                "request_hash": result.request_hash,
                "requested_model": result.requested_model,
                "actual_model": result.actual_model,
                "provider": result.provider,
                "created_at": result.created_at,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "estimated_cost": result.estimated_cost,
                "finish_reason": result.finish_reason,
                "raw_response": result.raw_response,
                "parsed_response": result.parsed_response,
                "validation_status": result.validation_status,
                "content_text": result.content_text,
                "label": label,
                "reasoning": used_reasoning,
            }
            atomic_write_json(cache_path, record)
        self.budget.add(estimated_cost)
        self._record_usage(result, label=label)
        return result

    def _record_usage(self, result: ChatResult, label: str = "") -> None:
        rec = UsageRecord(
            request_hash=result.request_hash,
            requested_model=result.requested_model,
            actual_model=result.actual_model,
            provider=result.provider,
            created_at=result.created_at,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost=0.0 if result.cached else result.estimated_cost,
            finish_reason=result.finish_reason,
            cached=result.cached,
            validation_status=result.validation_status,
            label=label,
        )
        with self._lock:
            self._usage.append(rec)
            line = stable_json(asdict(rec)) + "\n"
            self.usage_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.usage_log_path.open("a", encoding="utf-8") as f:
                f.write(line)

    def usage_summary(self) -> dict[str, Any]:
        with self._lock:
            rows = list(self._usage)
        total_in = sum(r.input_tokens for r in rows)
        total_out = sum(r.output_tokens for r in rows)
        total_cost = sum(r.estimated_cost for r in rows)
        cached_n = sum(1 for r in rows if r.cached)
        parse_ok = sum(
            1
            for r in rows
            if r.validation_status in {"ok", "healed_json_extract", "cached"}
        )
        return {
            "requests": len(rows),
            "cached_hits": cached_n,
            "uncached_requests": len(rows) - cached_n,
            "input_tokens": total_in,
            "output_tokens": total_out,
            "estimated_cost_usd": round(total_cost + self.budget.spent_usd * 0, 6),
            "budget_spent_usd": round(self.budget.spent_usd, 6),
            "budget_limit_usd": self.budget.budget_usd,
            "parse_ok": parse_ok,
            "parse_ok_rate": (parse_ok / len(rows)) if rows else 1.0,
        }

    def _request_with_retries(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                if method.upper() == "GET":
                    resp = self._client.get(path)
                else:
                    resp = self._client.post(path, json=json_body)
                if resp.status_code == 429 or resp.status_code >= 500:
                    # On rate limit, rotate fallback key before waiting
                    rotated = False
                    if resp.status_code == 429:
                        rotated = self._rotate_api_key()
                    wait = min(180.0, (2**attempt) * 3 + 2.0 * attempt)
                    if rotated:
                        wait = min(wait, 5.0)
                    # honor Retry-After when present
                    ra = resp.headers.get("Retry-After")
                    if ra:
                        try:
                            wait = max(wait, float(ra))
                        except ValueError:
                            pass
                    time.sleep(wait)
                    last_err = RuntimeError(
                        f"OpenRouter HTTP {resp.status_code}: "
                        f"{self._redact(resp.text[:500])}"
                        + (" (rotated API key)" if rotated else "")
                    )
                    continue
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"OpenRouter HTTP {resp.status_code}: "
                        f"{self._redact(resp.text[:800])}"
                    )
                return resp
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_err = RuntimeError(self._redact(str(exc)))
                wait = min(60.0, (2**attempt) + 0.25)
                time.sleep(wait)
        raise RuntimeError(
            f"OpenRouter request failed after retries: "
            f"{self._redact(str(last_err))}"
        )
