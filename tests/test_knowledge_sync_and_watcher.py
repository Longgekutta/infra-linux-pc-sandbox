from __future__ import annotations
"""Unit tests for knowledge sync (three-sandbox coordination) and upstream watcher."""
import unittest
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.knowledge_sync import (
    load_shared, automation_switches_to_remove, cdp_runtime_fix_mode,
    sourceURL_name, utility_world_name, tls_default_profile,
    tls_profiles_available, mobile_pif_insights, status,
)
from core.upstream_watcher import DEFAULT_WATCH_TARGETS, load_state


class TestKnowledgeSync(unittest.TestCase):

    def test_shared_knowledge_loads_with_patchright_switches(self):
        d = load_shared()
        switches = automation_switches_to_remove()
        self.assertGreaterEqual(len(switches), 10,
                                f"Shared knowledge must carry patchright's switch list, got {len(switches)}")
        # Key automation tells from patchright's chromiumSwitchesPatch
        self.assertIn("--enable-automation", switches, "The #1 automation tell must be in the list")
        self.assertIn("--disable-ipc-flooding-protection", switches,
                      "IPC flooding protection removal must be tracked")

    def test_runtime_fix_mode_is_valid_rebrowser_mode(self):
        mode = cdp_runtime_fix_mode()
        valid = {"addBinding", "alwaysIsolated", "enableDisable"}
        self.assertIn(mode, valid, f"Fix mode '{mode}' must be a valid rebrowser taxonomy mode")

    def test_sourceurl_and_world_names_are_generic(self):
        self.assertEqual(sourceURL_name(), "app.js",
                         "sourceURL must be generic (not pptr:-style fingerprint)")
        self.assertNotIn("playwright", utility_world_name().lower(),
                         "World name must not fingerprint the automation library")

    def test_tls_profiles_include_pinned_default(self):
        self.assertIn(tls_default_profile(), tls_profiles_available(),
                      "The pinned default profile must be in the available list")
        self.assertGreaterEqual(len(tls_profiles_available()), 5,
                                "tls-client ships multiple Chrome profiles")

    def test_mobile_pif_insights_present(self):
        insights = mobile_pif_insights()
        self.assertIn("deepest_project", insights, "PIF insights must name the deepest project")
        self.assertIn("private", insights.get("key_insight", ""),
                      "PIF key insight must mention private fingerprints")

    def test_status_shape(self):
        s = status()
        self.assertIn("version", s)
        self.assertIn("switches", s)
        self.assertIn("fix_mode", s)
        self.assertIn("tls_profiles", s)
        self.assertGreaterEqual(s["version"], 1, "Shared knowledge must be versioned >= 1")
        self.assertEqual(s["switches"], len(automation_switches_to_remove()),
                         "Status switch count must match the actual list")
        self.assertGreaterEqual(s["tls_profiles"], 5, "Status must count available TLS profiles")


class TestUpstreamWatcher(unittest.TestCase):

    def test_watch_targets_cover_all_four_upstreams(self):
        repos = {t["repo"] for t in DEFAULT_WATCH_TARGETS}
        for expected in ["Kaliiiiiiiiii-Vinyzu/patchright", "rebrowser/rebrowser-patches",
                         "osm0sis/PlayIntegrityFork", "bogdanfinn/tls-client"]:
            self.assertIn(expected, repos, f"Must watch {expected}")

    def test_auto_absorb_flags_are_correct(self):
        # tls-client and PIFork are auto-absorbable (pure parameter lists);
        # patchright/rebrowser need human judgment (patch library source).
        by_repo = {t["repo"]: t for t in DEFAULT_WATCH_TARGETS}
        self.assertTrue(by_repo["bogdanfinn/tls-client"].get("auto_absorb"),
                        "tls-client profiles are parameter lists: auto-absorbable")
        self.assertFalse(by_repo["Kaliiiiiiiiii-Vinyzu/patchright"].get("auto_absorb"),
                         "patchright TS patches need human judgment")

    def test_watcher_state_persists(self):
        from core.upstream_watcher import WATCHER_STATE
        # If a real watch cycle has run, the state must persist per-repo entries
        state = load_state()
        self.assertIsInstance(state, dict, "Watcher state must be a dict")
        if state:
            for repo, entry in state.items():
                self.assertIn(repo, {t["repo"] for t in DEFAULT_WATCH_TARGETS},
                              f"State key '{repo}' must be a watched repo")
                self.assertIn("last_commit_date", entry,
                              f"State entry for {repo} must carry last_commit_date")
        # State file path must live inside the project (not CWD-dependent)
        self.assertTrue(WATCHER_STATE.endswith("watcher_state.json"),
                        f"State path must be watcher_state.json, got {WATCHER_STATE}")

if __name__ == "__main__":
    unittest.main()
