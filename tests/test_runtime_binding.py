from __future__ import annotations
"""Unit tests for the rebrowser addBinding port (deepest Runtime.enable fix)."""
import unittest
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.runtime_binding import random_binding_name, RuntimeBindingSession


class _MockCDP:
    def __init__(self):
        self.calls = []
        self.fail_add_binding = False
    def call_cdp(self, method, params=None):
        self.calls.append((method, params))
        if method == "Runtime.addBinding" and self.fail_add_binding:
            return {"error": "binding failed"}
        return {"result": {}}


class TestRuntimeBinding(unittest.TestCase):

    def test_binding_name_is_random_and_namespaced(self):
        n1, n2 = random_binding_name(), random_binding_name()
        self.assertNotEqual(n1, n2, "Two binding names must differ (random per session)")
        self.assertTrue(n1.startswith("rb_"), "Binding name must be namespaced rb_")
        self.assertTrue(re.fullmatch(r"rb_[a-z0-9]{12}", n1), "Name must be rb_ + 12 alphanumerics")

    def test_arm_sends_add_binding_without_runtime_enable(self):
        mock = _MockCDP()
        session = RuntimeBindingSession(mock, fix_mode="addBinding")
        ok = session.arm()
        self.assertTrue(ok, "arm must succeed against a cooperative CDP endpoint")
        methods = [c[0] for c in mock.calls]
        self.assertIn("Runtime.addBinding", methods, "arm must send Runtime.addBinding")
        self.assertNotIn("Runtime.enable", methods,
                         "addBinding mode must NEVER send Runtime.enable (the whole point)")

    def test_arm_failure_reported_not_swallowed(self):
        mock = _MockCDP()
        mock.fail_add_binding = True
        session = RuntimeBindingSession(mock, fix_mode="addBinding")
        ok = session.arm()
        self.assertFalse(ok, "arm failure must be reported (not silently swallowed)")
        self.assertFalse(session._binding_ready, "Failed arm must not mark binding ready")

    def test_probe_returns_none_when_not_armed(self):
        mock = _MockCDP()
        session = RuntimeBindingSession(mock, fix_mode="addBinding")
        self.assertIsNone(session.probe_main_context({}),
                          "Unarmed session must return None (caller falls back to isolated)")

    def test_status_shape(self):
        mock = _MockCDP()
        session = RuntimeBindingSession(mock, fix_mode="alwaysIsolated")
        s = session.status()
        self.assertEqual(s["fix_mode"], "alwaysIsolated")
        self.assertFalse(s["armed"], "Unarmed session must report armed=False")

if __name__ == "__main__":
    unittest.main()
