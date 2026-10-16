from __future__ import annotations
"""Unit tests for the cross-layer fingerprint coherence auditor (A1)."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.consistency_audit import audit_profile_coherence, audit_egress_payload
from core.stealth_profile import LinuxStealthProfileGenerator


class TestConsistencyAudit(unittest.TestCase):

    def test_coherent_profile_scores_full(self):
        p = LinuxStealthProfileGenerator.create_profile("audit_ok")
        r = audit_profile_coherence(p, egress_country="US")
        self.assertEqual(r["score"], 100, f"Coherent profile must score 100, got {r['score']} with issues {r['issues']}")
        self.assertTrue(r["coherent"], "Coherent profile must pass")

    def test_timezone_contradiction_detected(self):
        p = LinuxStealthProfileGenerator.create_profile("audit_tz")
        p.timezone = "Asia/Shanghai"  # contradicts US egress
        r = audit_profile_coherence(p, egress_country="US")
        self.assertFalse(r["coherent"], "US egress + Asia/Shanghai tz must fail")
        self.assertTrue(any("Egress/timezone" in i for i in r["issues"]),
                        f"Issues must name the timezone contradiction: {r['issues']}")

    def test_language_contradiction_detected(self):
        p = LinuxStealthProfileGenerator.create_profile("audit_lang")
        p.languages = ["zh-CN", "zh"]
        p.timezone = "Asia/Shanghai"
        r = audit_profile_coherence(p, egress_country="US")
        self.assertTrue(any("Egress/language" in i for i in r["issues"]),
                        f"Issues must name the language contradiction: {r['issues']}")
        self.assertLess(r["score"], 60, "Multiple contradictions must score below 60")

    def test_proxy_webrtc_contradiction_detected(self):
        p = LinuxStealthProfileGenerator.create_profile("audit_webrtc")
        p.webrtc_mode = "default"  # allows non-proxied UDP with proxy on
        r = audit_profile_coherence(p)
        self.assertTrue(any("WebRTC" in i for i in r["issues"]),
                        f"Proxy on + permissive WebRTC must be flagged: {r['issues']}")

    def test_egress_payload_wrapper(self):
        p = LinuxStealthProfileGenerator.create_profile("audit_wrap")
        payload = {"country_code": "US", "ip": "1.2.3.4"}
        r = audit_egress_payload(payload, p)
        self.assertEqual(r["score"], 100, "Coherent payload+profile must score 100")
        payload_bad = {"countryCode": "JP"}
        r2 = audit_egress_payload(payload_bad, p)
        self.assertFalse(r2["coherent"], "JP egress + America/New_York tz must fail")

    def test_mobile_ua_with_desktop_gpu_detected(self):
        p = LinuxStealthProfileGenerator.create_profile("audit_mobile_gpu")
        p.user_agent = "Mozilla/5.0 (Linux; Android 14; Pixel 8) Mobile Safari/537.36"
        r = audit_profile_coherence(p)
        self.assertTrue(any("Mobile UA with desktop GPU" in i for i in r["issues"]),
                        f"Mobile UA + desktop GPU must be a hard contradiction: {r['issues']}")

if __name__ == "__main__":
    unittest.main()
