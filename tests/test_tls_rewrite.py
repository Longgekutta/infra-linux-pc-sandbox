from __future__ import annotations
"""Unit tests for the CDP Fetch TLS rewrite layer (L3+ full wire fingerprint)."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.tls_rewrite import (
    find_tls_daemon, clean_request_headers, clean_response_headers,
    is_websocket_upgrade, TLSRewriteDriver, TLS_DAEMON_CANDIDATES,
)


class _MockCDP:
    def __init__(self):
        self.calls = []
    def call_cdp(self, method, params=None):
        self.calls.append((method, params))
        return {"result": {}}


class TestTLSRewrite(unittest.TestCase):

    def test_clean_request_headers_strips_chrome_owned(self):
        cleaned = clean_request_headers({
            "Host": "target.com", "Content-Length": "5",
            "Connection": "keep-alive", "User-Agent": "UA/1.0",
            "sec-websocket-key": "abc",
        })
        self.assertNotIn("Host", cleaned, "Chrome-owned Host must be stripped before daemon execution")
        self.assertNotIn("Content-Length", cleaned, "Chrome-owned Content-Length must be stripped")
        self.assertNotIn("Connection", cleaned, "Chrome-owned Connection must be stripped")
        self.assertNotIn("sec-websocket-key", cleaned, "WS handshake headers must be stripped")
        self.assertIn("User-Agent", cleaned, "Caller headers Chrome does not own must survive")

    def test_clean_response_headers_strips_recomputed(self):
        cleaned = clean_response_headers({
            "Content-Length": "100", "Content-Encoding": "gzip",
            "Set-Cookie": "a=1", "Content-Type": "text/html",
        })
        self.assertNotIn("Content-Length", cleaned, "Chrome recomputes Content-Length on fulfill")
        self.assertNotIn("Content-Encoding", cleaned, "Chrome recomputes Content-Encoding on fulfill")
        self.assertIn("Set-Cookie", cleaned, "Set-Cookie must survive")
        self.assertIn("Content-Type", cleaned, "Content-Type must survive")

    def test_websocket_upgrade_detection(self):
        self.assertTrue(is_websocket_upgrade({"Upgrade": "websocket"}), "WS upgrade must be detected")
        self.assertTrue(is_websocket_upgrade({"Connection": "Upgrade"}), "Connection upgrade must be detected")
        self.assertFalse(is_websocket_upgrade({"Connection": "keep-alive"}), "Plain HTTP must not be flagged")

    def test_no_daemon_degrades_loudly(self):
        driver = TLSRewriteDriver(cdp_driver=_MockCDP(), daemon_path=None)
        self.assertFalse(driver.available, "Missing daemon must report unavailable")
        res = driver.install()
        self.assertFalse(res["active"], "Install without daemon must stay inactive")
        self.assertIn("reason", res, "Inactive install must report a reason, not fail silently")

    def test_handle_paused_request_without_daemon_falls_through(self):
        mock_cdp = _MockCDP()
        driver = TLSRewriteDriver(cdp_driver=mock_cdp, daemon_path=None)
        res = driver.handle_paused_request({
            "requestId": "r1",
            "request": {"url": "https://x.com/", "method": "GET", "headers": {}},
        })
        self.assertEqual(res["action"], "continue", "No-daemon path must fall through via continueRequest")
        self.assertEqual(driver.stats["fell_through"], 1, "Fall-through must be counted")
        methods = [c[0] for c in mock_cdp.calls]
        self.assertIn("Fetch.continueRequest", methods, "Fall-through must call Fetch.continueRequest")

    def test_websocket_upgrade_counts_leak_and_continues(self):
        mock_cdp = _MockCDP()
        driver = TLSRewriteDriver(cdp_driver=mock_cdp,
                                  daemon_path="/nonexistent/daemon")  # available=True shape
        res = driver.handle_paused_request({
            "requestId": "r2",
            "request": {"url": "wss://x.com/", "method": "GET",
                        "headers": {"Upgrade": "websocket", "Connection": "Upgrade"}},
        })
        self.assertEqual(res["action"], "continue", "WS upgrade must continue (documented limitation)")
        self.assertEqual(driver.stats["websocket_leaks"], 1, "WS leak must be counted")

    def test_daemon_candidates_are_declared(self):
        self.assertGreaterEqual(len(TLS_DAEMON_CANDIDATES), 3, "Must declare known native daemon candidates")

if __name__ == "__main__":
    unittest.main()
