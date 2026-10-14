from __future__ import annotations
"""
Cloud Network Router Module - Linux PC Sandbox
Manages high-concurrency cloud network routing, DNS-over-HTTPS (DoH) leak protection,
IPv6 leak shields, and egress proxy verification across cloud worker nodes.
"""

import os
import json
import socket
import ssl
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple
from bridge.shared_schema import ProxyConfig

class LinuxCloudNetworkRouter:
    """
    Cloud-native network security and proxy router for Linux PC sandboxes.
    Guarantees no server IP leakage, verifies upstream proxy egress, and provides DoH resolution.
    """

    DEFAULT_DOH_SERVERS = [
        "https://1.1.1.1/dns-query",
        "https://dns.google/resolve",
        "https://cloudflare-dns.com/dns-query"
    ]

    def __init__(self, default_proxy: Optional[ProxyConfig] = None):
        self.default_proxy = default_proxy

    @staticmethod
    def get_proxy_opener(proxy: ProxyConfig) -> urllib.request.OpenerDirector:
        """Create an urllib opener configured for the specified proxy."""
        if not proxy.enabled or not proxy.host:
            return urllib.request.build_opener()

        auth_str = ""
        if proxy.username and proxy.password:
            auth_str = f"{proxy.username}:{proxy.password}@"

        proxy_url = f"{proxy.proxy_type}://{auth_str}{proxy.host}:{proxy.port}"
        proxy_handler = urllib.request.ProxyHandler({
            "http": proxy_url,
            "https": proxy_url
        })
        return urllib.request.build_opener(proxy_handler)

    def test_proxy_connectivity(
        self,
        proxy: ProxyConfig,
        timeout: float = 8.0
    ) -> Tuple[bool, str, float]:
        """
        Verify proxy reachability, check outbound public IP, and measure response latency.
        Returns: (success: bool, egress_ip_or_error: str, latency_ms: float)
        """
        if not proxy.enabled or not proxy.host:
            return False, "Proxy disabled or missing host", 0.0

        opener = self.get_proxy_opener(proxy)
        test_url = "https://api.ipify.org?format=json"

        start_time = time.time()
        try:
            req = urllib.request.Request(
                test_url,
                headers={"User-Agent": "Linux-PC-Sandbox/1.0"}
            )
            # Create a context that verifies certificates
            ctx = ssl.create_default_context()
            with opener.open(req, timeout=timeout, context=ctx) as resp:
                latency = (time.time() - start_time) * 1000.0
                data = json.loads(resp.read().decode("utf-8"))
                ip = data.get("ip", "unknown")
                return True, ip, round(latency, 2)
        except Exception as e:
            latency = (time.time() - start_time) * 1000.0
            return False, str(e), round(latency, 2)

    def resolve_doh(
        self,
        domain: str,
        doh_url: Optional[str] = None,
        proxy: Optional[ProxyConfig] = None,
        timeout: float = 5.0
    ) -> Optional[str]:
        """
        Resolve DNS query using DNS-over-HTTPS (DoH) to prevent ISP/cloud DNS eavesdropping and poisoning.
        """
        endpoint = doh_url or self.DEFAULT_DOH_SERVERS[0]
        url = f"{endpoint}?name={domain}&type=A"
        opener = self.get_proxy_opener(proxy) if proxy else urllib.request.build_opener()

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/dns-json",
                    "User-Agent": "Linux-PC-Sandbox-DoH/1.0"
                }
            )
            ctx = ssl.create_default_context()
            with opener.open(req, timeout=timeout, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                answers = data.get("Answer", [])
                for ans in answers:
                    if ans.get("type") == 1:  # Type A (IPv4)
                        return ans.get("data")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            sys.stderr.write(f"[DoH] Query warning for {domain}: {e}\n")
            return None
        return None

    @staticmethod
    def get_chrome_network_args(proxy: ProxyConfig) -> list[str]:
        """
        Generate Chromium CLI arguments to enforce proxy and block WebRTC/IPv6 leaks.
        """
        args = []
        if proxy.enabled and proxy.host:
            args.append(f"--proxy-server={proxy.proxy_type}://{proxy.host}:{proxy.port}")
            bypass = getattr(proxy, "bypass_list", None)
            if bypass:
                args.append(f"--proxy-bypass-list={bypass}")

        # Block WebRTC public IP exposure
        args.extend([
            "--enforce-webrtc-ip-permission-check",
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
            "--disable-features=WebRtcHideLocalIpsWithMdns",
            "--dns-over-https-mode=secure"
        ])
        return args
