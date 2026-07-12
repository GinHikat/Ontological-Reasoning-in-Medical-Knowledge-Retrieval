"""Token-bucket / interval rate limiter for OpenRouter reduced pipeline.

Defaults are deliberately conservative for free-tier models:
global concurrency 1, per-model concurrency 1, min interval + jitter.
"""

from __future__ import annotations

import os
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RateLimitConfig:
    global_concurrency: int = 1
    per_model_concurrency: int = 1
    max_requests_per_minute: float | None = None
    min_request_interval_seconds: float = 3.0
    jitter_seconds: float = 2.0
    max_retries: int = 8

    @classmethod
    def from_env(cls, prefix: str = "OPENROUTER_REDUCED_") -> "RateLimitConfig":
        def _int(name: str, default: int) -> int:
            raw = os.environ.get(prefix + name, "").strip()
            return int(raw) if raw else default

        def _float(name: str, default: float) -> float:
            raw = os.environ.get(prefix + name, "").strip()
            return float(raw) if raw else default

        rpm = os.environ.get(prefix + "MAX_REQUESTS_PER_MINUTE", "").strip()
        return cls(
            global_concurrency=_int("GLOBAL_CONCURRENCY", 1),
            per_model_concurrency=_int("PER_MODEL_CONCURRENCY", 1),
            max_requests_per_minute=float(rpm) if rpm else None,
            min_request_interval_seconds=_float("MIN_REQUEST_INTERVAL_SECONDS", 3.0),
            jitter_seconds=_float("JITTER_SECONDS", 2.0),
            max_retries=_int("MAX_RETRIES", 8)
            if os.environ.get(prefix + "MAX_RETRIES", "").strip()
            else int(os.environ.get("OPENROUTER_MAX_RETRIES", "8")),
        )


@dataclass
class RateLimitStats:
    waits: int = 0
    rate_limit_hits: int = 0
    retries: int = 0
    total_wait_seconds: float = 0.0


class RateLimitScheduler:
    """Serialize OpenRouter calls with interval + optional RPM + Retry-After."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig.from_env()
        self.stats = RateLimitStats()
        self._global_sem = threading.Semaphore(max(1, self.config.global_concurrency))
        self._model_sems: dict[str, threading.Semaphore] = {}
        self._model_lock = threading.Lock()
        self._last_request_ts = 0.0
        self._rpm_timestamps: list[float] = []
        self._schedule_lock = threading.Lock()

    def _model_sem(self, model: str) -> threading.Semaphore:
        with self._model_lock:
            if model not in self._model_sems:
                self._model_sems[model] = threading.Semaphore(
                    max(1, self.config.per_model_concurrency)
                )
            return self._model_sems[model]

    def _sleep(self, seconds: float) -> None:
        if seconds <= 0:
            return
        self.stats.waits += 1
        self.stats.total_wait_seconds += seconds
        time.sleep(seconds)

    def acquire(self, model: str) -> None:
        """Block until a request slot is available; enforce spacing and RPM."""
        self._global_sem.acquire()
        self._model_sem(model).acquire()
        try:
            with self._schedule_lock:
                now = time.monotonic()
                # minimum interval + jitter (no bursts)
                interval = float(self.config.min_request_interval_seconds)
                jitter = random.uniform(0.0, max(0.0, float(self.config.jitter_seconds)))
                earliest = self._last_request_ts + interval + jitter
                wait = max(0.0, earliest - now)

                # RPM window
                if self.config.max_requests_per_minute and self.config.max_requests_per_minute > 0:
                    window = 60.0
                    cutoff = now - window
                    self._rpm_timestamps = [t for t in self._rpm_timestamps if t >= cutoff]
                    limit = float(self.config.max_requests_per_minute)
                    if len(self._rpm_timestamps) >= limit:
                        oldest = self._rpm_timestamps[0]
                        rpm_wait = max(0.0, oldest + window - now)
                        wait = max(wait, rpm_wait)

                if wait > 0:
                    # release schedule lock while sleeping
                    pass
                planned_wait = wait
            if planned_wait > 0:
                self._sleep(planned_wait)
            with self._schedule_lock:
                ts = time.monotonic()
                self._last_request_ts = ts
                self._rpm_timestamps.append(ts)
                cutoff = ts - 60.0
                self._rpm_timestamps = [t for t in self._rpm_timestamps if t >= cutoff]
        except Exception:
            self._model_sem(model).release()
            self._global_sem.release()
            raise

    def release(self, model: str) -> None:
        self._model_sem(model).release()
        self._global_sem.release()

    def backoff_sleep(
        self,
        attempt: int,
        *,
        retry_after: float | None = None,
        rate_limited: bool = False,
    ) -> None:
        if rate_limited:
            self.stats.rate_limit_hits += 1
        self.stats.retries += 1
        exp = min(180.0, (2**attempt) * 3.0 + 2.0 * attempt)
        jitter = random.uniform(0.0, max(0.0, float(self.config.jitter_seconds)))
        wait = exp + jitter
        if retry_after is not None:
            wait = max(wait, float(retry_after))
        self._sleep(wait)

    def as_dict(self) -> dict[str, Any]:
        return {
            "config": {
                "global_concurrency": self.config.global_concurrency,
                "per_model_concurrency": self.config.per_model_concurrency,
                "max_requests_per_minute": self.config.max_requests_per_minute,
                "min_request_interval_seconds": self.config.min_request_interval_seconds,
                "jitter_seconds": self.config.jitter_seconds,
                "max_retries": self.config.max_retries,
            },
            "stats": {
                "waits": self.stats.waits,
                "rate_limit_hits": self.stats.rate_limit_hits,
                "retries": self.stats.retries,
                "total_wait_seconds": round(self.stats.total_wait_seconds, 3),
            },
        }
