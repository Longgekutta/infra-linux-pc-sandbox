from __future__ import annotations
"""Unit tests for the Camoufox driver (Gecko kernel, 4th fleet engine)."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from automation.camoufox_driver import (
    camoufox_available, binary_installed, CamoufoxDriver,
)


class TestCamoufoxDriver(unittest.TestCase):

    def test_kernel_lineage_is_gecko(self):
        d = CamoufoxDriver()
        self.assertEqual(d.KERNEL, "gecko",
                         "Camoufox must be declared as the Gecko kernel driver "
                         "(breaking out of Blink is the whole point)")

    def test_availability_reported_honestly(self):
        # In this environment camoufox package IS installed; binary may or may
        # not be fetched. The driver must report both dimensions separately.
        d = CamoufoxDriver()
        s = d.status()
        self.assertIn("package_available", s, "status must report package dimension")
        self.assertIn("binary_installed", s, "status must report binary dimension")
        self.assertIn("kernel", s, "status must report kernel lineage")
        # Coherence: if the package is absent, availability must be False
        if not camoufox_available():
            self.assertFalse(s["package_available"],
                             "Package absent must report package_available=False")

    def test_launch_without_binary_fails_loudly(self):
        d = CamoufoxDriver()
        if binary_installed():
            self.skipTest("binary fetched in this environment; loud-failure path untestable")
        with self.assertRaises(RuntimeError,
                               msg="Launch without binary must fail loudly, no silent Blink fallback"):
            d.launch()

    def test_binary_check_is_separate_dimension(self):
        # package_available and binary_installed must be independent signals:
        # a fresh pip install has the package but not the binary.
        s = CamoufoxDriver().status()
        if s["package_available"] and not s["binary_installed"]:
            self.assertFalse(s["launched"], "Package without binary must not report launched")

if __name__ == "__main__":
    unittest.main()
