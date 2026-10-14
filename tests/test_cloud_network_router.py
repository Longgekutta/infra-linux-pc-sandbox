from __future__ import annotations
import unittest
import urllib.request
from core.cloud_network_router import LinuxCloudNetworkRouter
from bridge.shared_schema import ProxyConfig

class TestLinuxCloudNetworkRouter(unittest.TestCase):

    def test_chrome_network_args(self):
        proxy = ProxyConfig(
            enabled=True,
            proxy_type="socks5",
            host="127.0.0.1",
            port=10808,
            bypass_list="<-loopback>"
        )
        args = LinuxCloudNetworkRouter.get_chrome_network_args(proxy)
        self.assertIn("--proxy-server=socks5://127.0.0.1:10808", args, "Args must contain configured proxy server")
        self.assertIn("--proxy-bypass-list=<-loopback>", args, "Args must configure proxy bypass list")
        self.assertIn("--enforce-webrtc-ip-permission-check", args, "Args must enforce WebRTC IP permission check")
        self.assertIn("--dns-over-https-mode=secure", args, "Args must configure secure DNS-over-HTTPS mode")

    def test_chrome_network_args_direct(self):
        proxy = ProxyConfig(enabled=False)
        args = LinuxCloudNetworkRouter.get_chrome_network_args(proxy)
        for arg in args:
            self.assertFalse(arg.startswith("--proxy-server="), f"Direct connection arg list should not contain proxy-server, found {arg}")

    def test_proxy_opener(self):
        proxy = ProxyConfig(
            enabled=True,
            proxy_type="http",
            host="127.0.0.1",
            port=7890
        )
        opener = LinuxCloudNetworkRouter.get_proxy_opener(proxy)
        handler_types = [type(h) for h in opener.handlers]
        self.assertIn(urllib.request.ProxyHandler, handler_types, "Opener handlers must contain ProxyHandler")
        proxy_handler = next(h for h in opener.handlers if isinstance(h, urllib.request.ProxyHandler))
        self.assertEqual(proxy_handler.proxies.get("http"), "http://127.0.0.1:7890", "ProxyHandler must match specified http endpoint")
        self.assertEqual(proxy_handler.proxies.get("https"), "http://127.0.0.1:7890", "ProxyHandler must match specified https endpoint")

if __name__ == "__main__":
    unittest.main()
