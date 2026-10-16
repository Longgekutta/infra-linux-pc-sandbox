from __future__ import annotations
"""
TLS Rewrite Module - Linux PC Sandbox (L3+ Full Wire-Fingerprint Layer)
CDP Fetch.enable-based full TLS rewriting for egress page requests.

Pattern (validated industry-wide, cf. blacktip v0.5.0 / bogdanfinn/tls-client):
  1. CDP `Fetch.enable` pauses every HTTP request the browser issues.
  2. Each paused request is handed to an external TLS daemon (a native binary
     built on a BoringSSL/uTLS stack — e.g. bogdanfinn/tls-client in Go, or
     curl-impersonate) which performs the upstream connection with a REAL
     browser ClientHello, HTTP/2 SETTINGS frame, and header order.
  3. The daemon's response is fulfilled back through CDP `Fetch.fulfillRequest`,
     so the browser never opens an upstream TCP connection.

First-principles boundary (why an external daemon is the CODE LIMIT for TLS):
  The ClientHello bytes are emitted by the TLS library that opens the raw TCP
  socket. A WASM/native-Python rewrite inside the browser process would still
  inherit that library's fingerprint. The only code-level way to change the
  wire bytes is to have a DIFFERENT native process open the socket — hence the
  daemon architecture. The daemon itself must be Go/Rust/C (raw-socket TLS
  control); Python cannot produce a byte-controlled ClientHello with stdlib ssl.
"""

import json
import logging
import shutil
import subprocess
from typing import Dict, Any, Optional, List

logger = logging.getLogger("TLSRewrite")

# Known native TLS-impersonation daemons (any one suffices; none are hard deps)
TLS_DAEMON_CANDIDATES = [
    "curl-impersonate-chrome",     # curl-impersonate chrome wrapper
    "curl_chrome133",              # curl-impersonate versioned wrapper
    "blacktip-tls",                # blacktip Go daemon (bogdanfinn/tls-client)
    "tls-client",                  # generic bogdanfinn/tls-client CLI
]

# Chrome owns these headers' lifecycle; a daemon must not forward caller values
CHROME_OWNED_REQUEST_HEADERS = [
    "host", "content-length", "connection", "keep-alive",
    "transfer-encoding", "upgrade", "sec-websocket-key",
]

# Chrome re-computes these on the response; the daemon's values must be stripped
CHROME_OWNED_RESPONSE_HEADERS = [
    "content-length", "content-encoding", "transfer-encoding",
    "connection", "keep-alive",
]


def find_tls_daemon() -> Optional[str]:
    """Locate a native TLS-impersonation daemon on PATH (optional enhancement)."""
    for cand in TLS_DAEMON_CANDIDATES:
        path = shutil.which(cand)
        if path:
            return path
    return None


def clean_request_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Strip headers whose values Chrome's lifecycle owns before daemon execution."""
    return {
        k: v for k, v in headers.items()
        if k.lower() not in CHROME_OWNED_REQUEST_HEADERS
    }


def clean_response_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Strip response headers Chrome re-computes when fulfilling via CDP."""
    return {
        k: v for k, v in headers.items()
        if k.lower() not in CHROME_OWNED_RESPONSE_HEADERS
    }


def is_websocket_upgrade(headers: Dict[str, str]) -> bool:
    """Detect WebSocket upgrades: their frames bypass CDP Fetch after the upgrade,
    presenting the browser's native TLS. Callers must fall through (documented
    industry limitation; only a framing-aware proxy fully covers these)."""
    upgrade = headers.get("Upgrade") or ""
    connection = headers.get("Connection") or ""
    return upgrade.lower() == "websocket" or "upgrade" in connection.lower()


class TLSRewriteDriver:
    """
    Installs a CDP Fetch.enable interception layer over an existing CDP driver,
    routing every page request through a native TLS daemon (when available).

    Degradation contract (fail loudly, never silently impersonate):
      - daemon available  -> requests are rewritten with real browser TLS
      - daemon missing    -> rewrite stays INACTIVE and status reports the gap;
                             callers decide whether that is acceptable.
    """

    def __init__(self, cdp_driver: Any, daemon_path: Optional[str] = None):
        self.cdp_driver = cdp_driver
        self.daemon_path = daemon_path or find_tls_daemon()
        self.active = False
        self.stats = {"intercepted": 0, "fulfilled": 0, "fell_through": 0, "websocket_leaks": 0}

    @property
    def available(self) -> bool:
        return self.daemon_path is not None

    def install(self, patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """Enable CDP Fetch interception. Returns the activation status."""
        if not self.available:
            return {
                "active": False,
                "reason": (
                    "No native TLS daemon on PATH (candidates: "
                    + ", ".join(TLS_DAEMON_CANDIDATES)
                    + "). Egress page requests keep the browser's native TLS. "
                      "Build/install a daemon (Go bogdanfinn/tls-client or "
                      "curl-impersonate) to activate full wire rewriting."
                ),
            }
        res = self.cdp_driver.call_cdp("Fetch.enable", {
            "patterns": patterns or [{"urlPattern": "*", "requestStage": "Request"}]
        })
        self.active = "result" in res or "error" not in res
        return {"active": self.active, "daemon": self.daemon_path}

    def handle_paused_request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle one Fetch.requestPaused event: route via daemon, fulfill via CDP."""
        self.stats["intercepted"] += 1
        req = event.get("request", {})
        request_id = event.get("requestId")
        headers = req.get("headers", {})

        if is_websocket_upgrade(headers):
            # Documented industry limitation: WS frames bypass CDP Fetch after
            # the upgrade; fall through so the upgrade succeeds, count the leak.
            self.stats["websocket_leaks"] += 1
            self.stats["fell_through"] += 1
            self.cdp_driver.call_cdp("Fetch.continueRequest", {"requestId": request_id})
            return {"action": "continue", "reason": "websocket_upgrade"}

        if not self.available:
            self.stats["fell_through"] += 1
            self.cdp_driver.call_cdp("Fetch.continueRequest", {"requestId": request_id})
            return {"action": "continue", "reason": "no_daemon"}

        try:
            upstream = self._daemon_fetch(
                url=req.get("url", ""),
                method=req.get("method", "GET"),
                headers=clean_request_headers(headers),
                body=req.get("postData"),
            )
        except Exception as e:
            logger.debug("TLS daemon fetch failed for %s: %s", req.get("url"), e)
            self.stats["fell_through"] += 1
            self.cdp_driver.call_cdp("Fetch.continueRequest", {"requestId": request_id})
            return {"action": "continue", "reason": f"daemon_error: {str(e)[:60]}"}

        fulfill_params: Dict[str, Any] = {
            "requestId": request_id,
            "responseCode": upstream.get("status", 200),
            "responseHeaders": [
                {"name": k, "value": v}
                for k, v in clean_response_headers(upstream.get("headers", {})).items()
            ],
        }
        body_b64 = upstream.get("body_b64")
        if body_b64:
            fulfill_params["body"] = body_b64
        res = self.cdp_driver.call_cdp("Fetch.fulfillRequest", fulfill_params)
        if "error" in res:
            self.stats["fell_through"] += 1
            return {"action": "fulfill_failed", "error": res["error"]}
        self.stats["fulfilled"] += 1
        return {"action": "fulfilled"}

    def _daemon_fetch(self, url: str, method: str,
                      headers: Dict[str, str], body: Optional[str]) -> Dict[str, Any]:
        """Execute one upstream request via the native TLS daemon (NDJSON stdio
        or CLI form, per the daemon's interface)."""
        job = {"method": method, "url": url, "headers": headers}
        if body:
            job["body"] = body
        proc = subprocess.run(
            [self.daemon_path],
            input=json.dumps(job).encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"daemon exit {proc.returncode}: {proc.stderr[:80]}")
        return json.loads(proc.stdout.decode("utf-8", errors="replace"))

    def status(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "active": self.active,
            "daemon": self.daemon_path,
            "stats": dict(self.stats),
        }
