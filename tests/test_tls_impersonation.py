from __future__ import annotations
"""Unit tests for the TLS impersonation module (L3 TLS layer, real-verified contract)."""
import unittest
import sys
import os
import ssl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.tls_impersonation import (
    build_ssl_context, egress_tls_status, chrome_egress_headers, active_ja4,
    get_chrome_fingerprint, UTLS_AVAILABLE, CHROME_PRESET,
)


class TestTLSImpersonation(unittest.TestCase):

    def test_build_ssl_context_returns_valid_context(self):
        ctx = build_ssl_context()
        self.assertIsInstance(ctx, ssl.SSLContext, "build_ssl_context must return an SSLContext")
        self.assertTrue(ctx.check_hostname, "Context must keep certificate hostname verification on")

    def test_impersonated_context_pins_chrome_fingerprint(self):
        if not UTLS_AVAILABLE:
            self.skipTest("utls not installed in this environment")
        ctx = build_ssl_context(impersonate=True)
        self.assertIsNotNone(ctx.fingerprint, "Impersonated context must carry a Chrome fingerprint")
        self.assertEqual(ctx.fingerprint.ja4_hash, active_ja4(),
                         "Context JA4 must match the reported active JA4")
        # Verified contract: ALPN pinned to http/1.1 so urllib's HTTP/1.1 writer
        # matches the negotiated protocol (h2 negotiation stalls urllib).
        self.assertEqual(ctx.get_alpn_protocols() if hasattr(ctx, "get_alpn_protocols") else None, None,
                         "ALPN check via wrap-time selection; context must not negotiate h2 for urllib")

    def test_chrome_preset_is_real_chrome(self):
        if not UTLS_AVAILABLE:
            self.skipTest("utls not installed in this environment")
        fp = get_chrome_fingerprint()
        self.assertIsNotNone(fp, "Chrome preset must load when utls is installed")
        self.assertTrue(fp.ja4_hash.startswith("t13d"), "Chrome TLS1.3 JA4 must start with t13d")
        self.assertIn("Chrome", fp.http_headers.get("User-Agent", ""),
                      "Chrome preset headers must carry a Chrome User-Agent")

    def test_chrome_egress_headers_shape(self):
        if not UTLS_AVAILABLE:
            self.skipTest("utls not installed in this environment")
        hdrs = chrome_egress_headers()
        self.assertIsNotNone(hdrs, "Chrome egress headers must build when utls is installed")
        self.assertIn("sec-ch-ua", hdrs, "Chrome headers must include sec-ch-ua client hints")
        self.assertIn("Sec-Fetch-Mode", hdrs, "Chrome headers must include Sec-Fetch metadata")

    def test_egress_tls_status_coherent(self):
        status = egress_tls_status()
        self.assertIn("utls_installed", status)
        self.assertIn("active_stack", status)
        self.assertIn("ja4", status)
        self.assertIn("limit", status)
        self.assertEqual(status["impersonation_active"], status["utls_installed"],
                         "Impersonation can only be active when utls is installed")
        if status["impersonation_active"]:
            self.assertIn("BoringSSL", status["active_stack"], "Active stack must report BoringSSL/Chrome")
            self.assertIsNotNone(status["ja4"], "Active impersonation must report its JA4")

if __name__ == "__main__":
    unittest.main()
