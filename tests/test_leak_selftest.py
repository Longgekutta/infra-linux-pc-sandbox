from __future__ import annotations
"""Unit tests for the CDP leak self-verifier (A2)."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.leak_selftest import run_leak_selftest, ALL_PROBES


class _MockDriver:
    """Mock CDP driver returning scripted page-side probe verdicts."""
    def __init__(self, verdicts=None):
        self.verdicts = verdicts or []  # list of dicts per call
        self.calls = []
        self._i = 0
    def evaluate(self, expr):
        self.calls.append(expr)
        if self._i < len(self.verdicts):
            v = self.verdicts[self._i]
        else:
            v = {"probe": f"p{self._i}", "leak": False}
        self._i += 1
        return v


class TestLeakSelftest(unittest.TestCase):

    def test_clean_session_reports_clean(self):
        driver = _MockDriver()  # defaults all clean
        r = run_leak_selftest(driver)
        self.assertTrue(r["clean"], "All-clean verdicts must report clean")
        self.assertEqual(r["leaks"], [], "No leaks must be listed")
        self.assertEqual(len(driver.calls), len(ALL_PROBES), "Every probe must be evaluated")

    def test_webdriver_regression_detected(self):
        verdicts = [{"probe": "console_stack", "leak": False}] * 2 + \
                   [{"probe": "webdriver", "leak": True}] + \
                   [{"probe": "plugins", "leak": False}]
        r = run_leak_selftest(_MockDriver(verdicts))
        self.assertFalse(r["clean"], "webdriver=true must fail the selftest")
        self.assertIn("webdriver", r["leaks"], "Leaks must name the webdriver probe")

    def test_probe_evaluation_failure_counts_as_leak(self):
        verdicts = [{"probe": "console_stack", "leak": False}, None, None, None]
        r = run_leak_selftest(_MockDriver(verdicts))
        self.assertFalse(r["clean"], "Probe evaluation failure must count as a leak (fail-closed)")
        self.assertTrue(any("unknown" in l for l in r["leaks"]), "Failed probes must be listed")

    def test_console_stack_probe_source_is_complete(self):
        # The probe source must compute the verdict page-side (no host shortcuts)
        for src in ALL_PROBES:
            self.assertIn("leak:", src, f"Every probe must return a leak field: {src[:40]}")
        self.assertIn("console.debug", ALL_PROBES[0], "console_stack probe must exercise console.debug")
        self.assertIn("ownKeys", ALL_PROBES[1], "proxy_ownkeys probe must exercise ownKeys trap")

if __name__ == "__main__":
    unittest.main()
