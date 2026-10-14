from __future__ import annotations
"""
Vault Manager Module - Linux PC Sandbox
Manages encrypted account credentials, recovery tokens, and includes a built-in
RFC 6238 Time-based One-Time Password (TOTP) authenticator generator for zero-friction 2FA.
"""

import os
import sys
import time
import json
import hmac
import base64
import struct
import hashlib
from typing import Dict, Any, List, Optional
from bridge.shared_schema import AccountCredentials

class TOTPGenerator:
    """
    Standard RFC 6238 Time-based One-Time Password (TOTP) algorithm implementation.
    Compatible with Google Authenticator, Microsoft Authenticator, and standard 2FA seeds.
    """

    @staticmethod
    def generate_current_code(secret: str, interval: int = 30, digits: int = 6) -> str:
        """Calculate current 6-digit TOTP code from base32 secret."""
        # Clean secret format
        clean_secret = secret.replace(" ", "").upper()
        # Add padding if needed
        padding = (8 - len(clean_secret) % 8) % 8
        clean_secret += "=" * padding

        try:
            key = base64.b32decode(clean_secret, casefold=True)
        except Exception as e:
            return f"INVALID_KEY({e})"

        counter = int(time.time()) // interval
        counter_bytes = struct.pack(">Q", counter)

        # HMAC-SHA1
        hm = hmac.new(key, counter_bytes, hashlib.sha1).digest()

        # Dynamic truncation (RFC 4226)
        offset = hm[-1] & 0x0F
        binary = struct.unpack(">I", hm[offset:offset+4])[0] & 0x7FFFFFFF

        code = str(binary % (10 ** digits))
        return code.zfill(digits)

    @staticmethod
    def get_remaining_seconds(interval: int = 30) -> int:
        """Get seconds remaining before current code rotates."""
        return interval - (int(time.time()) % interval)


class VaultManager:
    """
    Manages persistent account credentials, recovery emails, and 2FA secrets on Linux.
    """

    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = vault_path or os.environ.get("SANDBOX_VAULT_PATH", "/data/vault/accounts.json")
        os.makedirs(os.path.dirname(os.path.abspath(self.vault_path)), exist_ok=True)
        self.accounts: Dict[str, AccountCredentials] = {}
        self.load()

    def load(self) -> int:
        """Load vault from disk."""
        try:
            with open(self.vault_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.accounts = {k: AccountCredentials(**v) for k, v in data.items()}
            return len(self.accounts)
        except FileNotFoundError:
            return 0
        except (OSError, json.JSONDecodeError, TypeError, KeyError) as e:
            sys.stderr.write(f"[VaultManager] Load warning for {self.vault_path}: {e}\n")
            return 0

    def save(self) -> bool:
        """Save vault to disk."""
        try:
            data = {k: vars(v) for k, v in self.accounts.items()}
            with open(self.vault_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except (OSError, TypeError) as e:
            sys.stderr.write(f"[VaultManager] Save error for {self.vault_path}: {e}\n")
            return False

    def add_or_update(self, account_id: str, credentials: AccountCredentials) -> bool:
        self.accounts[account_id] = credentials
        return self.save()

    def get(self, account_id: str) -> Optional[AccountCredentials]:
        return self.accounts.get(account_id)

    def get_totp(self, account_id: str) -> Optional[Dict[str, Any]]:
        acc = self.get(account_id)
        if not acc or not acc.totp_secret:
            return None
        return {
            "account_id": account_id,
            "code": TOTPGenerator.generate_current_code(acc.totp_secret),
            "remaining_seconds": TOTPGenerator.get_remaining_seconds()
        }
