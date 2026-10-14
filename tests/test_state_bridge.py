from __future__ import annotations
import unittest
import tempfile
import os
import json
import shutil
from bridge.state_bridge import StateBridge
from bridge.shared_schema import PCBrowserProfile
from core.stealth_profile import LinuxStealthProfileGenerator

class TestLinuxStateBridge(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.bridge = StateBridge(base_profile_dir=self.temp_dir)
        self.profile = LinuxStealthProfileGenerator.create_profile("sync_test_01")

        # Save profile
        p_dir = self.bridge.get_profile_dir(self.profile.profile_id)
        os.makedirs(p_dir, exist_ok=True)
        with open(os.path.join(p_dir, "profile.json"), "w", encoding="utf-8") as f:
            json.dump(self.profile.to_dict(), f, indent=2)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_and_import_json(self):
        bundle_file = os.path.join(self.temp_dir, "test_bundle.json")
        out_path = self.bridge.export_profile_bundle(self.profile.profile_id, bundle_file)
        self.assertTrue(os.path.isfile(out_path), f"JSON bundle file '{out_path}' must exist after export")

        imported = self.bridge.import_profile_bundle(out_path, target_profile_id="restored_worker")
        self.assertEqual(imported.profile_id, "restored_worker", "Restored profile ID must match target ID")
        self.assertEqual(imported.platform, "linux", "Restored profile platform must be linux")
        self.assertEqual(imported.gpu.gl_renderer, self.profile.gpu.gl_renderer, "Restored GPU renderer must match original")
        self.assertEqual(imported.hardware_concurrency, self.profile.hardware_concurrency, "Restored concurrency must match original")

    def test_export_and_import_zip(self):
        zip_file = os.path.join(self.temp_dir, "test_bundle.zip")
        out_path = self.bridge.export_profile_bundle(self.profile.profile_id, zip_file)
        self.assertTrue(os.path.isfile(out_path), f"ZIP bundle file '{out_path}' must exist after export")

        imported = self.bridge.import_profile_bundle(out_path, target_profile_id="restored_zip_worker")
        self.assertEqual(imported.profile_id, "restored_zip_worker", "Restored profile ID must match target ID")
        self.assertEqual(imported.platform, "linux", "Restored profile platform must be linux")

    def test_cdp_session_sync_roundtrip(self):
        class MockLinuxCDP:
            def __init__(self):
                self._cookies = [{"name": "cf_clearance", "value": "token_abc123", "domain": ".google.com"}]
            def get_cookies(self):
                return self._cookies
            def set_cookies(self, cookies):
                self._cookies = cookies
                return True

        mock_cdp = MockLinuxCDP()
        exported = StateBridge.export_session_via_cdp(mock_cdp)
        self.assertEqual(len(exported["cookies"]), 1, "Exported session must contain exactly 1 cookie")
        self.assertEqual(exported["cookies"][0]["name"], "cf_clearance", "Cookie name must match original")

        imported_count = StateBridge.import_session_via_cdp(mock_cdp, exported)
        self.assertEqual(imported_count, 1, "Imported count must match cookie count")

if __name__ == "__main__":
    unittest.main()
