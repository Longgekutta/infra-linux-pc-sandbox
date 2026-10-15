from __future__ import annotations
"""
TLS Impersonation Module - Linux PC Sandbox (L3 TLS Fingerprint Layer)
Documents and optionally enables browser-grade TLS ClientHello impersonation for
egress HTTP requests. Pure-stdlib fallback uses OpenSSL (python ssl), whose JA3/JA4
fingerprint is a known non-browser tell; when the optional `utls` package
(BoringSSL drop-in `import ssl` replacement, MIT, jawah/utls) is installed,
`build_ssl_context()` returns a Chrome-impersonating context instead.

First-principles boundary (why this module is the CODE LIMIT):
  The ClientHello is emitted by the TLS library before any application code runs —
  no page script, no header trick, and no post-hoc patch can change it
  (cf. JA3/JA4 analysis: "a TLS fingerprint cannot be patched"). The only two
  code-level remedies are (1) impersonate the handshake via a BoringSSL-backed
  library, or (2) let a real browser open the connection. This module implements
  (1) with a stdlib fallback; (2) is the domain of the browser drivers.
"""

import ssl
import importlib.util
from typing import Optional

UTLS_AVAILABLE = importlib.util.find_spec("utls") is not None


def build_ssl_context(impersonate: bool = True) -> ssl.SSLContext:
    """
    Build an SSLContext for egress requests.

    - impersonate=True and `utls` installed: Chrome-impersonating BoringSSL context
      (JA3/JA4 indistinguishable from Chrome of the pinned version).
    - otherwise: default stdlib context (OpenSSL ClientHello — detectable as
      non-browser at the TLS layer; documented limitation, not a bug).
    """
    if impersonate and UTLS_AVAILABLE:
        try:
            import importlib
            utls = importlib.import_module("utls")  # optional BoringSSL-backed ssl replacement
            if hasattr(utls, "create_default_context"):
                ctx = utls.create_default_context(impersonate="chrome")
                if ctx is not None:
                    return ctx
            import sys
            sys.stderr.write(
                "[tls_impersonation] utls installed but has no create_default_context; "
                "falling back to stdlib OpenSSL context\n")
        except Exception as e:
            # Optional-enhancement failure must degrade loudly, not silently:
            # log and fall back to the stdlib context.
            import sys
            sys.stderr.write(f"[tls_impersonation] utls context build failed: {e}\n")
    return ssl.create_default_context()


def egress_tls_status() -> dict:
    """Report the active TLS layer status for the preflight audit."""
    return {
        "utls_installed": UTLS_AVAILABLE,
        "impersonation_active": UTLS_AVAILABLE,
        "active_stack": "BoringSSL (Chrome-impersonating)" if UTLS_AVAILABLE else "OpenSSL (stdlib default)",
        "limit": (
            "Without utls, egress TLS ClientHello is OpenSSL's — JA3/JA4 distinguishable "
            "from a browser at the TLS layer. Install utls (optional) or route egress "
            "through the browser drivers to eliminate this layer."
        ),
    }
