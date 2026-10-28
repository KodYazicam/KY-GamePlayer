from __future__ import annotations

import json
import locale as locale_mod
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Iterable


_RATE_LIMIT_STATS = {"requests": 0, "rate_limited": 0, "retries": 0}

# A transient 429/5xx is common on Discord's edge. Retry idempotent requests by
# default; POST/PATCH need an explicit opt-in because the server may already
# have applied the write before returning a 5xx.
_DEFAULT_RETRY_STATUSES = (429, 500, 502, 503, 504)
_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})
_MAX_BACKOFF = 8.0
_BASE_BACKOFF = 0.5


def rate_limit_stats() -> dict[str, int]:
    """Cumulative HTTP counters since process start (rate-limit dashboard)."""
    return dict(_RATE_LIMIT_STATS)


def reset_rate_limit_stats() -> None:
    for key in _RATE_LIMIT_STATS:
        _RATE_LIMIT_STATS[key] = 0


def http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: Any | None = None,
    timeout: float = 20,
    retries: int = 3,
    retry_statuses: Iterable[int] | None = None,
    retry_non_idempotent: bool = False,
) -> tuple[int, Any, dict[str, str]]:
    """Perform an HTTP request with bounded, jittered retries.

    ``retries`` is the total number of attempts (not the number of retries).
    429 is retried for every method because Discord rejected the request
    before applying it. Other statuses from ``retry_statuses`` are retried for
    idempotent methods only unless ``retry_non_idempotent`` is set. Network
    exceptions follow the same rule: a POST is returned as status 0 instead of
    being sent twice by accident.

    ``Retry-After`` is honoured in seconds or HTTP-date form, capped at eight
    seconds. Exhausted retries return the last HTTP status/payload (or status
    0 with a message for transport failures) rather than raising.
    """
    attempts = max(1, retries)
    statuses = set(_DEFAULT_RETRY_STATUSES if retry_statuses is None else retry_statuses)
    upper_method = method.upper()
    idempotent = upper_method in _IDEMPOTENT_METHODS
    retry_transport = idempotent or retry_non_idempotent

    data = None
    if body is not None:
        data = body if isinstance(body, (bytes, bytearray)) else json.dumps(body).encode("utf-8")
    last_exc: Exception | None = None
    for attempt in range(attempts):
        req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
        _RATE_LIMIT_STATS["requests"] += 1
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                payload = _payload(raw)
                return int(response.status), payload, dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            hdrs = dict(exc.headers.items()) if exc.headers else {}
            status = int(exc.code)
            exc.close()
            if status == 429:
                _RATE_LIMIT_STATS["rate_limited"] += 1
            can_retry = status in statuses and (
                status == 429 or idempotent or retry_non_idempotent
            )
            if can_retry and attempt + 1 < attempts:
                _RATE_LIMIT_STATS["retries"] += 1
                _sleep(_retry_wait(hdrs, attempt))
                last_exc = exc
                continue
            return status, _payload(raw, fallback=str(exc)), hdrs
        except Exception as exc:
            last_exc = exc
            if retry_transport and attempt + 1 < attempts:
                _RATE_LIMIT_STATS["retries"] += 1
                _sleep(_retry_wait({}, attempt))
                continue
            return 0, {"message": str(exc)}, {}
    return 0, {"message": str(last_exc or "request failed")}, {}


def _payload(raw: bytes, *, fallback: str | None = None) -> Any:
    if not raw:
        return {"message": fallback} if fallback else None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw.decode("utf-8", "ignore")[:400]}


def _retry_wait(headers: dict[str, str], attempt: int) -> float:
    retry_after = _retry_after(headers)
    if retry_after is not None:
        return retry_after
    backoff = _BASE_BACKOFF * (2 ** attempt)
    return min(_MAX_BACKOFF, backoff + random.uniform(0, 0.35))


def _retry_after(headers: dict[str, str]) -> float | None:
    raw = ""
    for key, value in headers.items():
        if key.lower() == "retry-after":
            raw = value.strip()
            break
    if not raw:
        return None
    try:
        return max(0.2, min(_MAX_BACKOFF, float(raw)))
    except ValueError:
        pass
    try:
        moment = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    seconds = (moment - datetime.now(timezone.utc)).total_seconds()
    return max(0.2, min(_MAX_BACKOFF, seconds))


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def local_locale() -> str:
    raw = locale_mod.getlocale()[0] or _fallback_locale() or "tr_TR"
    text = raw.replace("_", "-")
    if "-" in text:
        lang, region = text.split("-", 1)
        return f"{lang.lower()}-{region.upper()}"
    return "tr-TR"


def _fallback_locale() -> str | None:
    try:
        return locale_mod.getdefaultlocale()[0]
    except AttributeError:
        return None


def local_timezone() -> str:
    try:
        import datetime as dt

        tz = dt.datetime.now().astimezone().tzinfo
        key = getattr(tz, "key", None)
        if key:
            return str(key)
    except Exception:
        pass
    try:
        offset = -time.altzone if time.daylight else -time.timezone
    except Exception:
        offset = 0
    if offset == 3 * 3600:
        return "Europe/Istanbul"
    return "UTC"
