from __future__ import annotations
"""
State Bridge Module - Universal Cross-Platform PC Sandbox State Portability
Provides seamless export/import of profile metadata, session tokens, and cookie storage
between Windows PC Sandbox (Master High-Trust Node) and Linux PC Sandbox (Cloud Worker Fleet).
"""

import os
import sys
import json
import shutil
import logging
from typing import Dict, Any, List, Optional
from bridge.shared_schema import PCBrowserProfile

logger = logging.getLogger("StateBridge")

class _HybridBridgeMethod:
    """Descriptor that enables methods to be called both as instance and class methods."""
    def __init__(self, fn):
        self.fn = fn

    def __get__(self, instance, owner):
        def wrapper(*args, **kwargs):
            if instance is not None:
                return self.fn(instance, *args, **kwargs)
            return self.fn(owner(), *args, **kwargs)
        return wrapper

class StateBridge:
    """
    Manages session state serialization, cookie extraction, and cross-platform profile transfer.
    Methods can be called on an instance (using base_profile_dir) or directly on the StateBridge class.
    """

    def __init__(self, base_profile_dir: Optional[str] = None):
        self.base_profile_dir = base_profile_dir

    def get_profile_dir(self, profile_id: str) -> str:
        if self.base_profile_dir:
            return os.path.join(self.base_profile_dir, profile_id)
        return profile_id

    @_HybridBridgeMethod
    def export_profile_bundle(
        self,
        profile_id_or_dir: str,
        target_path: str,
        include_cookies_db: bool = True
    ) -> str:
        """
        Export a profile's metadata and state into a portable JSON package or ZIP archive.
        """
        if self.base_profile_dir and not os.path.isdir(profile_id_or_dir):
            p_dir = os.path.join(self.base_profile_dir, profile_id_or_dir)
        else:
            p_dir = profile_id_or_dir

        if not os.path.isdir(p_dir):
            raise FileNotFoundError(f"Source profile directory does not exist: {p_dir}")

        cfg_path = os.path.join(p_dir, "profile.json")
        profile_data = {}
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                profile_data = json.load(f)
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning("Failed to parse %s: %s", cfg_path, e)

        session_state_path = os.path.join(p_dir, "session_state.json")
        session_data = {}
        try:
            with open(session_state_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning("Failed to parse %s: %s", session_state_path, e)

        default_dir = os.path.join(p_dir, "Default")
        cookies_db = os.path.join(default_dir, "Network", "Cookies") if os.path.exists(os.path.join(default_dir, "Network", "Cookies")) else os.path.join(default_dir, "Cookies")
        has_cookies = os.path.exists(cookies_db)

        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

        if target_path.endswith(".json"):
            bundle = {
                "version": "1.0",
                "profile": profile_data,
                "session": session_data,
                "has_cookies_db": has_cookies,
                "profile_id": profile_data.get("profile_id", os.path.basename(p_dir))
            }
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(bundle, f, ensure_ascii=False, indent=2)
            return target_path

        elif target_path.endswith(".zip"):
            base_name = target_path[:-4]
            shutil.make_archive(base_name, "zip", p_dir)
            return target_path

        raise ValueError(f"Unsupported target format (must end in .json or .zip): {target_path}")

    @_HybridBridgeMethod
    def import_profile_bundle(
        self,
        bundle_path: str,
        target_profile_id: Optional[str] = None
    ) -> PCBrowserProfile:
        """
        Import a portable state bundle into target profile directory and return parsed profile.
        """
        if not os.path.isfile(bundle_path):
            raise FileNotFoundError(f"Bundle file not found: {bundle_path}")

        if bundle_path.endswith(".json"):
            with open(bundle_path, "r", encoding="utf-8") as f:
                bundle = json.load(f)

            p_dict = bundle.get("profile", {})
            profile = PCBrowserProfile.from_dict(p_dict)
            target_id = target_profile_id or profile.profile_id or "imported_profile"
            profile.profile_id = target_id

            dest_dir = self.get_profile_dir(target_id)
            os.makedirs(dest_dir, exist_ok=True)

            with open(os.path.join(dest_dir, "profile.json"), "w", encoding="utf-8") as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

            if "session" in bundle:
                with open(os.path.join(dest_dir, "session_state.json"), "w", encoding="utf-8") as f:
                    json.dump(bundle["session"], f, indent=2, ensure_ascii=False)

            return profile

        elif bundle_path.endswith(".zip"):
            target_id = target_profile_id or os.path.splitext(os.path.basename(bundle_path))[0]
            dest_dir = self.get_profile_dir(target_id)
            os.makedirs(dest_dir, exist_ok=True)
            shutil.unpack_archive(bundle_path, dest_dir, "zip")

            cfg_path = os.path.join(dest_dir, "profile.json")
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    profile = PCBrowserProfile.from_dict(json.load(f))
                    profile.profile_id = target_id
                    return profile
            except FileNotFoundError:
                raise ValueError("ZIP archive did not contain a valid profile.json")
            except Exception as e:
                logger.warning("Failed to parse %s: %s", cfg_path, e)
                raise ValueError(f"Corrupt profile.json in archive: {e}")

        raise ValueError("Invalid bundle format (must be .json or .zip)")

    @_HybridBridgeMethod
    def export_session_via_cdp(self, cdp_client: Any) -> Dict[str, Any]:
        """
        Extract cookies and storage state directly from active Chromium process via CDP.
        Immune to Chrome 127+ Windows App-Bound Encryption (ABE) because cookies are retrieved
        from decrypted memory structures.
        """
        result = {"cookies": [], "origins": []}
        try:
            if hasattr(cdp_client, "get_cookies"):
                result["cookies"] = cdp_client.get_cookies()
            else:
                res = cdp_client.call_cdp("Network.getCookies")
                if "result" in res and "cookies" in res["result"]:
                    result["cookies"] = res["result"]["cookies"]
                elif "cookies" in res:
                    result["cookies"] = res["cookies"]
        except Exception as e:
            logger.debug("Failed to export cookies via CDP: %s", e)
        return result

    @_HybridBridgeMethod
    def import_session_via_cdp(self, cdp_client: Any, session_data: Dict[str, Any]) -> int:
        """
        Inject cookies directly into active Chromium instance via CDP Network.setCookies.
        """
        cookies = session_data.get("cookies", [])
        if not cookies:
            return 0
        try:
            if hasattr(cdp_client, "set_cookies"):
                success = cdp_client.set_cookies(cookies)
                return len(cookies) if success else 0
            else:
                res = cdp_client.call_cdp("Network.setCookies", {"cookies": cookies})
                if "result" in res or "error" not in res:
                    return len(cookies)
        except Exception as e:
            logger.debug("Failed to import cookies via CDP: %s", e)
        return 0

