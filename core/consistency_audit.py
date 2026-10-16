from __future__ import annotations
"""
Consistency Audit Module - Linux PC Sandbox (Cross-Layer Fingerprint Coherence Auditor)
Cross-validates every profile dimension against every other before task launch.
Catches configuration contradictions that single-layer checks miss — e.g. an
egress IP in the US with an Asia/Shanghai timezone, a de-DE language list with
an en-US UA, or a GPU whose client-hint vendor contradicts the UA platform.

First principles: detection engines do not score signals in isolation; they
score contradictions BETWEEN signals. A profile with a perfect per-layer
fingerprint can still be flagged in one query if two layers disagree.
This module makes cross-layer coherence a pre-flight invariant.
"""

import re
from typing import Dict, Any, List, Optional
from bridge.shared_schema import PCBrowserProfile

# Country -> expected default timezone + locale prefix (coherence pairs)
COUNTRY_TIMEZONE = {
    "US": {"tz_prefixes": ("America/",), "locale": "en-US"},
    "GB": {"tz_prefixes": ("Europe/London",), "locale": "en-GB"},
    "DE": {"tz_prefixes": ("Europe/Berlin", "Europe/Paris"), "locale": "de-DE"},
    "FR": {"tz_prefixes": ("Europe/Paris",), "locale": "fr-FR"},
    "JP": {"tz_prefixes": ("Asia/Tokyo",), "locale": "ja-JP"},
    "CN": {"tz_prefixes": ("Asia/Shanghai",), "locale": "zh-CN"},
    "SG": {"tz_prefixes": ("Asia/Singapore",), "locale": "en-SG"},
}

# Platform token each UA family must contain
PLATFORM_TOKENS = {
    "windows": "Windows NT 10.0",
    "linux": "X11; Linux x86_64",
}

# GPU vendors that contradict a mobile/ARM UA
DESKTOP_GPU_VENDORS = ("NVIDIA", "AMD Radeon", "Intel", "ANGLE")


def audit_profile_coherence(
    profile: PCBrowserProfile,
    egress_country: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Cross-validate a profile's layers for contradictions.
    Returns {"score": 0-100, "issues": [..], "coherent": bool}.
    """
    score = 100
    issues: List[str] = []

    ua = profile.user_agent or ""
    platform = (profile.platform or "").lower()

    # 1. UA <-> platform coherence
    expected_token = PLATFORM_TOKENS.get(platform)
    if expected_token and expected_token not in ua:
        score -= 30
        issues.append(
            f"UA/platform mismatch: UA lacks '{expected_token}' for platform '{platform}'")

    # 2. Timezone <-> language coherence (locale prefix must match tz region)
    tz = profile.timezone or ""
    langs = profile.languages or []
    primary_lang = langs[0] if langs else ""
    tz_region = tz.split("/")[0] if "/" in tz else ""
    if primary_lang.startswith(("zh", "ja", "de", "fr")) and tz_region == "America":
        score -= 25
        issues.append(
            f"Locale/timezone contradiction: language '{primary_lang}' with timezone '{tz}'")

    # 3. Egress country <-> timezone coherence
    if egress_country:
        expected = COUNTRY_TIMEZONE.get(egress_country.upper())
        if expected and not tz.startswith(expected["tz_prefixes"]):
            score -= 35
            issues.append(
                f"Egress/timezone contradiction: egress '{egress_country}' expects tz "
                f"prefix {expected['tz_prefixes']}, got '{tz}'")

    # 4. Egress country <-> language coherence
    if egress_country:
        expected = COUNTRY_TIMEZONE.get(egress_country.upper())
        if expected and primary_lang and not primary_lang.startswith(expected["locale"][:2]):
            score -= 20
            issues.append(
                f"Egress/language contradiction: egress '{egress_country}' expects locale "
                f"'{expected['locale']}', got '{primary_lang}'")

    # 5. Proxy on/off vs webrtc mode coherence
    if profile.proxy.enabled and profile.webrtc_mode != "disable_non_proxied_udp":
        score -= 15
        issues.append(
            "Proxy enabled but WebRTC mode allows non-proxied UDP — IP leak risk")

    # 6. GPU coherence: desktop GPU with mobile UA is a contradiction
    if "Mobile" in ua and any(v in (profile.gpu.gl_vendor + profile.gpu.gl_renderer) for v in DESKTOP_GPU_VENDORS):
        score -= 30
        issues.append("Mobile UA with desktop GPU renderer — hard contradiction")

    # 7. Screen sanity: width/height/scale positive & landscape typical
    scr = profile.screen
    if scr.width <= 0 or scr.height <= 0 or scr.scale_factor <= 0:
        score -= 25
        issues.append(f"Invalid screen geometry: {scr.width}x{scr.height} @ {scr.scale_factor}x")
    if scr.height > scr.width and platform in ("windows", "linux"):
        score -= 10
        issues.append("Portrait screen on desktop platform — atypical, raises entropy")

    return {"score": max(0, score), "issues": issues, "coherent": score >= 80}


def audit_egress_payload(payload: Dict[str, Any], profile: PCBrowserProfile) -> Dict[str, Any]:
    """
    Convenience wrapper: feed an egress verification payload (from
    WindowsNetworkProxy.verify_proxy_egress / LinuxCloudNetworkRouter) plus the
    profile to get the full cross-layer verdict.
    """
    country = payload.get("country_code") or payload.get("countryCode") or payload.get("country")
    return audit_profile_coherence(profile, egress_country=country)
