from __future__ import annotations
"""
Knowledge Sync Module - Linux PC Sandbox (Three-Sandbox Adversarial Knowledge Sharing)
Single source of truth for cross-sandbox adversarial knowledge: fingerprint
presets, leak probes, TLS parameters, and upstream-patched automation switches.

Why this exists (the three-sandbox coordination problem):
  Each sandbox tier (Windows master / Linux cloud workers / mobile fleet) faces
  the same anti-bot engines. A new leak vector discovered on ONE tier must
  reach the other two tiers' selftests and profiles without manual copying.
  This module distributes one shared JSON (shared_knowledge.json) to all three
  tiers and exposes typed accessors so no tier hardcodes stale parameters.

Data flow:
  upstream (patchright/rebrowser/PIFork/tls-client) 
    -> upstream_watcher.py diffs releases/commits
    -> shared_knowledge.json updated
    -> knowledge_sync.distribute() copies to all three tiers
    -> each tier's selftest/profiles read the shared values
"""

import json
import os
import shutil
from typing import Dict, Any, Optional, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED_KNOWLEDGE = os.path.join(ROOT, "shared_knowledge.json")
# sibling tiers (same repo checkout layout)
SIBLING_TIERS = [
    ("windows", os.path.join(os.path.dirname(ROOT), "infra-windows-pc-sandbox")),
    ("mobile", os.path.join(os.path.dirname(ROOT), "infra-universal-mobile-sandbox")),
]


def load_shared() -> Dict[str, Any]:
    """Load the shared knowledge base. Missing file -> minimal defaults."""
    try:
        with open(SHARED_KNOWLEDGE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"_version": 0, "chromium_automation_switches_to_remove": []}


def automation_switches_to_remove() -> List[str]:
    """Chromium switches that patchright removes (automation tells)."""
    return load_shared().get("chromium_automation_switches_to_remove", [])


def cdp_runtime_fix_mode() -> str:
    """The active Runtime.enable leak fix mode (rebrowser taxonomy)."""
    return load_shared().get("_runtime_fix_mode", "alwaysIsolated")


def sourceURL_name() -> str:
    """Generic script name replacing pptr:-style sourceURL fingerprints."""
    return load_shared().get("sourceURL_spoof_name", "app.js")


def utility_world_name() -> str:
    """Generic isolated world name (avoids Playwright default world fingerprint)."""
    return load_shared().get("utility_world_name", "isolated_world")


def tls_default_profile() -> str:
    """The pinned Chrome profile for the TLS daemon / utls context."""
    return load_shared().get("tls_default_profile", "Chrome_133")


def tls_profiles_available() -> List[str]:
    return load_shared().get("tls_chrome_profiles_available", [])


def mobile_pif_insights() -> Dict[str, Any]:
    return load_shared().get("mobile_pif_ecosystem", {})


def distribute(include_siblings: bool = True) -> Dict[str, Any]:
    """Copy the shared knowledge JSON to the sibling tier repos so all three
    tiers read one source of truth. Returns the distribution report."""
    report = {"distributed": [], "errors": []}
    if not include_siblings:
        report["distributed"].append(SHARED_KNOWLEDGE)
        return report
    for tier_name, tier_root in SIBLING_TIERS:
        dest = os.path.join(tier_root, "shared_knowledge.json")
        try:
            if os.path.isdir(tier_root):
                shutil.copyfile(SHARED_KNOWLEDGE, dest)
                report["distributed"].append(dest)
        except OSError as e:
            report["errors"].append(f"{tier_name}: {e}")
    return report


def status() -> Dict[str, Any]:
    d = load_shared()
    return {
        "version": d.get("_version", 0),
        "updated": d.get("_updated"),
        "switches": len(automation_switches_to_remove()),
        "tls_profiles": len(tls_profiles_available()),
        "fix_mode": cdp_runtime_fix_mode(),
    }
