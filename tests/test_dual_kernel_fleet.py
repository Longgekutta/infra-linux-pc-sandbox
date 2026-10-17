from __future__ import annotations
"""Unit tests for the dual-kernel fleet formation (Blink + Gecko drivers)."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from automation.headless_driver import LinuxHeadlessDriver
from automation.camoufox_driver import CamoufoxDriver, camoufox_available


class TestDualKernelFleet(unittest.TestCase):

    def test_fleet_has_two_distinct_kernels(self):
        blink = LinuxHeadlessDriver(cdp_port=9333,
                                    profile=__import__("core.stealth_profile", fromlist=["LinuxStealthProfileGenerator"]).LinuxStealthProfileGenerator.create_profile("fleet_t"))
        gecko = CamoufoxDriver()
        kernels = {blink.__class__.__module__, gecko.KERNEL}
        self.assertEqual(gecko.KERNEL, "gecko", "Gecko driver must declare its kernel")
        # Blink drivers are CDP-based; Gecko driver is Juggler-based
        self.assertNotEqual(gecko.KERNEL, "blink",
                            "Camoufox must NOT be a Blink driver (kernel diversity is the point)")

    def test_gecko_driver_has_no_cdp_runtime_leak_by_construction(self):
        # Juggler protocol (Gecko) structurally lacks CDP Runtime.enable —
        # the leak the Blink drivers mitigate cannot exist here.
        d = CamoufoxDriver()
        self.assertFalse(hasattr(d, "call_cdp"),
                         "Gecko driver must not expose CDP call_cdp (Juggler protocol)")

    def test_fleet_strategy_documented_in_code(self):
        from automation import camoufox_driver
        self.assertIn("dual-kernel", camoufox_driver.__doc__.lower(),
                      "Dual-kernel formation strategy must be documented in the driver")

if __name__ == "__main__":
    unittest.main()
