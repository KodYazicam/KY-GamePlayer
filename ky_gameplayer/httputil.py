from __future__ import annotations

import json
import locale as locale_mod
import random
import time
import urllib.error
import urllib.request
from typing import Any


def http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: Any | None = None,
    timeout: float = 20,
    retries: int = 3,
) -> tuple[int, Any, dict[str, str]]:
    data = None
    if body is not None:
        data = body if isinstance(body, (bytes, bytearray)) else json.dumps(body).encode("utf-8")
    last_exc: Exception | None = None
    for attempt in range(max(1, retries)):
        req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                payload = None
                if raw:
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        payload = {"raw": raw.decode("utf-8", "ignore")[:400]}
                return int(response.status), payload, dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            hdrs = dict(exc.headers.items()) if exc.headers else {}
            if exc.code == 429 and attempt + 1 < retries:
                wait = _retry_after(hdrs, attempt)
                time.sleep(wait)
                last_exc = exc
                continue
            try:
                payload = json.loads(raw) if raw else {"message": str(exc)}
            except Exception:
                payload = {"message": raw.decode("utf-8", "ignore")[:400]}
            return int(exc.code), payload, hdrs
        except Exception as exc:
            last_exc = exc
            if attempt + 1 < retries:
                time.sleep(0.4 * (attempt + 1) + random.uniform(0, 0.3))
                continue
            return 0, {"message": str(exc)}, {}
    return 0, {"message": str(last_exc or "request failed")}, {}


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


def _retry_after(headers: dict[str, str], attempt: int) -> float:
    raw = headers.get("Retry-After") or headers.get("retry-after") or ""
    try:
        return min(30.0, max(0.4, float(raw)))
    except ValueError:
        return min(8.0, 0.6 * (2 ** attempt) + random.uniform(0, 0.4))
