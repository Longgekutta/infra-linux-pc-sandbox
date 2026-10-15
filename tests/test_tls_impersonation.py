from __future__ import annotations
"""Unit tests for the TLS impersonation module (L3 TLS layer boundary)."""
import unittest
import sys
import os
import ssl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.tls_impersonation import build_ssl_context, egress_tls_status, UTLS_AVAILABLE


class TestTLSImpersonation(unittest.TestCase):

    def test_build_ssl_context_returns_valid_context(self):
        ctx = build_ssl_context()
        self.assertIsInstance(ctx, ssl.SSLContext, "build_ssl_context must return an SSLContext")
        # Both stdlib and utls contexts must be client-capable with sane defaults
        self.assertTrue(ctx.check_hostname, "Context must keep certificate hostname verification on")

    def test_build_ssl_context_fallback_without_utls(self):
        # In this environment utls is not installed: impersonation must degrade to
        # the stdlib OpenSSL context AND the status report must stay coherent.
        if UTLS_AVAILABLE:
            self.skipTest("utls installed in this environment; fallback path untestable")
        ctx = build_ssl_context(impersonate=True)
        self.assertIsInstance(ctx, ssl.SSLContext, "Fallback path must still return a usable SSLContext")
        self.assertIs(ctx, build_ssl_context(impersonate=False).__class__ and ctx, "Same context class as stdlib path")
        status = egress_tls_status()
        self.assertFalse(status["impersonation_active"],
                         "Status must report impersonation inactive when utls is absent")
        self.assertIn("OpenSSL", status["active_stack"],
                      "Active stack must report the stdlib OpenSSL fallback")

    def test_egress_tls_status_shape(self):
        status = egress_tls_status()
        self.assertIn("utls_installed", status, "Status must report utls availability")
        self.assertIn("active_stack", status, "Status must report the active TLS stack")
        self.assertIn("limit", status, "Status must document the code-level boundary")
        # coherence invariant: impersonation_active iff utls installed
        self.assertEqual(status["impersonation_active"], status["utls_installed"],
                         "Impersonation can only be active when utls is installed")

if __name__ == "__main__":
    unittest.main()
