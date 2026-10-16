from __future__ import annotations
"""Unit tests for session pacing in LinuxTaskWorker (A3)."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from automation.task_worker import LinuxTaskWorker


class _MockDriver:
    def __init__(self):
        self.navigated = []
        self.stealth_injected = False
        self.profile = type("P", (), {"profile_id": "pacing_test"})()
    def inject_stealth(self):
        self.stealth_injected = True
    def navigate(self, url, wait_seconds=2.0):
        self.navigated.append(url)
        return True
    def evaluate(self, script):
        return {}


class TestSessionPacing(unittest.TestCase):

    def test_warmup_visits_all_targets_in_order(self):
        driver = _MockDriver()
        worker = LinuxTaskWorker(driver)
        results = worker.warm_up_session(urls=["https://a.com", "https://b.com"],
                                         duration_per_url=0.1, session_pacing=False)
        self.assertEqual(driver.navigated, ["https://a.com", "https://b.com"],
                         "Targets must be visited in order")
        self.assertTrue(all(r["success"] for r in results), "All navigations must report success")
        self.assertTrue(driver.stealth_injected, "Stealth must be injected before warm-up")

    def test_pacing_flag_respected(self):
        driver = _MockDriver()
        worker = LinuxTaskWorker(driver)
        # session_pacing=False must complete without error (no inter-page pause)
        results = worker.warm_up_session(urls=["https://a.com"], session_pacing=False)
        self.assertEqual(len(results), 1, "One URL must produce one result")
        # session_pacing=True must also complete (pause path exercised)
        results2 = worker.warm_up_session(urls=["https://b.com", "https://c.com"],
                                          duration_per_url=0.1, session_pacing=True)
        self.assertEqual(len(results2), 2, "Paced session must visit all URLs")

    def test_results_carry_elapsed_seconds(self):
        driver = _MockDriver()
        worker = LinuxTaskWorker(driver)
        results = worker.warm_up_session(urls=["https://a.com"], duration_per_url=0.1,
                                         session_pacing=False)
        self.assertIn("elapsed_seconds", results[0], "Results must carry elapsed timing")
        self.assertIsInstance(results[0]["elapsed_seconds"], float, "Elapsed must be float seconds")

if __name__ == "__main__":
    unittest.main()
