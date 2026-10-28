from __future__ import annotations

import threading
import unittest
import urllib.error
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from ky_gameplayer import httputil
from ky_gameplayer.httputil import http_request, rate_limit_stats, reset_rate_limit_stats


class _ScriptedHandler(BaseHTTPRequestHandler):
    responses: list[tuple[int, dict[str, str], bytes]] = []
    calls: list[tuple[str, str]] = []
    lock = threading.Lock()

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        self._handle()

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        self._handle()

    def _handle(self) -> None:
        with self.lock:
            self.calls.append((self.command, self.path))
            if self.responses:
                status, headers, body = self.responses.pop(0)
            else:
                status, headers, body = 500, {}, b'{"message": "script exhausted"}'
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        return


@contextmanager
def scripted_server(responses: list[tuple[int, dict[str, str], bytes]]):
    handler = type(
        "Handler",
        (_ScriptedHandler,),
        {"responses": list(responses), "calls": [], "lock": threading.Lock()},
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/endpoint", handler.calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class _FakeResponse:
    status = 200
    headers = {"Content-Type": "application/json"}

    def __init__(self, body: bytes = b'{"ok": true}') -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        return None


class RetryTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_rate_limit_stats()

    def test_get_retries_transient_5xx(self) -> None:
        responses = [
            (503, {}, b'{"message": "temporary"}'),
            (200, {"Content-Type": "application/json"}, b'{"ok": true}'),
        ]
        with scripted_server(responses) as (url, calls), mock.patch.object(httputil, "_sleep") as sleep:
            status, payload, headers = http_request("GET", url, retries=2, timeout=5)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"ok": True})
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(len(calls), 2)
        sleep.assert_called_once()
        self.assertEqual(rate_limit_stats()["requests"], 2)
        self.assertEqual(rate_limit_stats()["retries"], 1)

    def test_get_returns_last_status_when_retries_are_exhausted(self) -> None:
        responses = [(503, {}, b"busy")] * 3
        with scripted_server(responses) as (url, calls), mock.patch.object(httputil, "_sleep"):
            status, payload, _headers = http_request("GET", url, retries=3, timeout=5)
        self.assertEqual(status, 503)
        self.assertEqual(payload, {"raw": "busy"})
        self.assertEqual(len(calls), 3)
        self.assertEqual(rate_limit_stats()["retries"], 2)

    def test_post_is_not_retried_on_5xx_by_default(self) -> None:
        responses = [(503, {}, b"busy"), (200, {}, b'{"ok": true}')]
        with scripted_server(responses) as (url, calls), mock.patch.object(httputil, "_sleep") as sleep:
            status, _payload, _headers = http_request("POST", url, body={"event": 1}, retries=3, timeout=5)
        self.assertEqual(status, 503)
        self.assertEqual(len(calls), 1)
        sleep.assert_not_called()

    def test_post_can_opt_in_to_5xx_retries(self) -> None:
        responses = [
            (502, {}, b"bad gateway"),
            (200, {"Content-Type": "application/json"}, b'{"ok": true}'),
        ]
        with scripted_server(responses) as (url, calls), mock.patch.object(httputil, "_sleep"):
            status, payload, _headers = http_request(
                "POST",
                url,
                body={"event": 1},
                retries=2,
                retry_non_idempotent=True,
                timeout=5,
            )
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"ok": True})
        self.assertEqual(len(calls), 2)

    def test_post_retries_429_without_opt_in(self) -> None:
        responses = [
            (429, {"Retry-After": "0"}, b'{"message": "rate limited"}'),
            (200, {}, b'{"ok": true}'),
        ]
        with scripted_server(responses) as (url, calls), mock.patch.object(httputil, "_sleep") as sleep:
            status, _payload, _headers = http_request("POST", url, body={"event": 1}, retries=2, timeout=5)
        self.assertEqual(status, 200)
        self.assertEqual(len(calls), 2)
        self.assertGreaterEqual(sleep.call_args.args[0], 0.2)
        self.assertEqual(rate_limit_stats()["rate_limited"], 1)

    def test_custom_retry_statuses_are_respected(self) -> None:
        responses = [(500, {}, b"server error"), (200, {}, b'{"ok": true}')]
        with scripted_server(responses) as (url, calls), mock.patch.object(httputil, "_sleep") as sleep:
            status, _payload, _headers = http_request(
                "GET",
                url,
                retries=3,
                retry_statuses=(503,),
                timeout=5,
            )
        self.assertEqual(status, 500)
        self.assertEqual(len(calls), 1)
        sleep.assert_not_called()

    def test_transport_errors_retry_idempotent_requests(self) -> None:
        responses = [urllib.error.URLError("temporary"), _FakeResponse()]
        with mock.patch.object(httputil.urllib.request, "urlopen", side_effect=responses) as urlopen:
            with mock.patch.object(httputil, "_sleep"):
                status, payload, _headers = http_request("GET", "https://example.invalid/", retries=2)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"ok": True})
        self.assertEqual(urlopen.call_count, 2)

    def test_transport_errors_do_not_retry_post_by_default(self) -> None:
        with mock.patch.object(
            httputil.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("temporary"),
        ) as urlopen:
            with mock.patch.object(httputil, "_sleep") as sleep:
                status, payload, _headers = http_request("POST", "https://example.invalid/", retries=3)
        self.assertEqual(status, 0)
        self.assertEqual(payload, {"message": "<urlopen error temporary>"})
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()


class RetryAfterTests(unittest.TestCase):
    def test_seconds_are_capped(self) -> None:
        self.assertEqual(httputil._retry_after({"Retry-After": "120"}), 8.0)
        self.assertEqual(httputil._retry_after({"retry-after": "0"}), 0.2)

    def test_http_date_is_accepted(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(seconds=3)
        wait = httputil._retry_after({"Retry-After": format_datetime(future, usegmt=True)})
        self.assertIsNotNone(wait)
        self.assertGreaterEqual(wait or 0, 0.2)
        self.assertLessEqual(wait or 0, 8.0)

    def test_invalid_header_returns_none(self) -> None:
        self.assertIsNone(httputil._retry_after({"Retry-After": "not a date"}))


class StatsTests(unittest.TestCase):
    def test_stats_are_copied_and_reset(self) -> None:
        reset_rate_limit_stats()
        stats = rate_limit_stats()
        self.assertEqual(stats, {"requests": 0, "rate_limited": 0, "retries": 0})
        stats["requests"] = 99
        self.assertEqual(rate_limit_stats()["requests"], 0)


if __name__ == "__main__":
    unittest.main()
