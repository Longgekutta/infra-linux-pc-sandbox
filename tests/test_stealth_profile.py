from __future__ import annotations
import unittest
from core.stealth_profile import LinuxStealthProfileGenerator
from bridge.shared_schema import PCBrowserProfile

class TestLinuxStealthProfile(unittest.TestCase):

    def test_create_profile(self):
        p = LinuxStealthProfileGenerator.create_profile(
            profile_id="test_worker_01",
            proxy_host="10.0.0.1",
            proxy_port=8080,
            use_proxy=True,
            email="bot@test.com"
        )
        self.assertEqual(p.profile_id, "test_worker_01", "Profile ID must match created ID")
        self.assertEqual(p.platform, "linux", "Platform must be linux")
        self.assertEqual(p.account.email, "bot@test.com", "Account email must match initialization value")
        self.assertTrue(p.proxy.enabled, "Proxy should be enabled")
        self.assertEqual(p.proxy.port, 8080, "Proxy port must match assigned port 8080")
        self.assertTrue(any(brand in (p.gpu.gl_vendor + p.gpu.gl_renderer) for brand in ["NVIDIA", "Intel", "Google"]), "GPU profile must match authentic vendor")
        self.assertGreaterEqual(p.hardware_concurrency, 8, "Linux profile hardware concurrency must be at least 8 cores")
        self.assertGreaterEqual(p.device_memory_gb, 16, "Linux profile device memory must be at least 16 GB")

    def test_build_stealth_script(self):
        p = LinuxStealthProfileGenerator.create_profile("stealth_test")
        script = LinuxStealthProfileGenerator.build_linux_stealth_script(p)
        self.assertIn("navigator, 'webdriver'", script, "Script must include navigator.webdriver definition")
        self.assertIn("Linux x86_64", script, "Script must set platform to Linux x86_64")
        self.assertIn(str(p.hardware_concurrency), script, "Script must inject profile hardware concurrency")
        self.assertIn(str(p.device_memory_gb), script, "Script must inject profile device memory")
        self.assertIn("UNMASKED_RENDERER_WEBGL", script, "Script must mock UNMASKED_RENDERER_WEBGL")
        self.assertIn("window.chrome", script, "Script must inject window.chrome mock")
        self.assertIn("MAX_TEXTURE_SIZE", script, "Script must mask MAX_TEXTURE_SIZE")
        self.assertIn("AudioBuffer.prototype.getChannelData", script, "Script must hook AudioBuffer getChannelData")
        self.assertIn("CanvasRenderingContext2D.prototype.getImageData", script, "Script must hook Canvas 2D getImageData")
        self.assertIn("availHeight", script, "Script must set screen availHeight")
        self.assertIn("Notification", script, "Script must set Notification permission")
        self.assertIn("navigator.getBattery", script, "Script must simulate Battery API")
        self.assertIn("makeNative", script, "Script must include makeNative camouflage utility")
        self.assertIn("getShaderPrecisionFormat", script, "Script must configure WebGL getShaderPrecisionFormat")

if __name__ == "__main__":
    unittest.main()
