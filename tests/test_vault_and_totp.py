from __future__ import annotations
"""
Unit Tests for Linux Vault Manager and RFC 6238 TOTP Generator
"""

import unittest
import sys
import os
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.vault_manager import VaultManager, TOTPGenerator
from bridge.shared_schema import AccountCredentials

class TestLinuxVaultAndTOTP(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.vault_file = os.path.join(self.test_dir, "vault.json")
        self.vault = VaultManager(vault_path=self.vault_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_totp_code_generation(self):
        # Standard RFC 6238 test secret
        secret = "JBSWY3DPEHPK3PXP"
        code = TOTPGenerator.generate_current_code(secret)
        self.assertEqual(len(code), 6, f"TOTP code '{code}' must be exactly 6 characters long")
        self.assertTrue(code.isdigit(), f"TOTP code '{code}' must consist only of decimal digits")

        rem = TOTPGenerator.get_remaining_seconds()
        self.assertTrue(0 <= rem <= 30, f"Remaining period {rem}s must be within [0, 30]")

    def test_vault_persistence(self):
        creds = AccountCredentials(
            email="linux_worker@gmail.com",
            password="cloudPassword789!",
            totp_secret="JBSWY3DPEHPK3PXP"
        )
        self.vault.add_or_update("worker_acc_01", creds)

        loaded = self.vault.get("worker_acc_01")
        self.assertIsNotNone(loaded, "Retrieved account credentials must not be None")
        self.assertEqual(loaded.email, "linux_worker@gmail.com", "Retrieved account email must match stored value")

        totp_data = self.vault.get_totp("worker_acc_01")
        self.assertIsNotNone(totp_data, "Generated TOTP dictionary must not be None")
        self.assertEqual(len(totp_data["code"]), 6, f"Generated TOTP code '{totp_data['code']}' must be 6 digits")

if __name__ == "__main__":
    unittest.main()
