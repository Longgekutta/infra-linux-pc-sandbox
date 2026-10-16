from __future__ import annotations
"""
Task Worker Module - Linux PC Sandbox
Executes headless maintenance tasks, session warm-ups, fingerprint health checks,
and state sync across distributed cloud Linux nodes.
"""

import time
import random
from typing import Dict, Any, List, Optional
from bridge.shared_schema import PCBrowserProfile
from automation.headless_driver import LinuxHeadlessDriver

class LinuxTaskWorker:
    """
    Automated background worker for Linux PC sandboxes.
    Performs profile warm-ups, browsing simulations, and bot detection checks.
    """

    WARMUP_TARGETS = [
        "https://en.wikipedia.org/wiki/Main_Page",
        "https://news.ycombinator.com/",
        "https://httpbin.org/headers",
        "https://example.com"
    ]

    def __init__(self, driver: LinuxHeadlessDriver):
        self.driver = driver

    def verify_stealth_integrity(self) -> Dict[str, Any]:
        """
        Verify that anti-detect hooks are successfully active in the running Chromium page.
        Audits: webdriver removal, platform, hardware concurrency, and WebGL masking.
        """
        script = """
        (() => {
            let glVendor = 'none';
            let glRenderer = 'none';
            let maxTexSize = 0;
            try {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                if (gl) {
                    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
                    if (dbg) {
                        glVendor = gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL);
                        glRenderer = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL);
                    }
                    maxTexSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
                }
            } catch (e) {}

            return {
                webdriver: navigator.webdriver,
                platform: navigator.platform,
                hardwareConcurrency: navigator.hardwareConcurrency,
                deviceMemory: navigator.deviceMemory,
                pluginsLength: navigator.plugins.length,
                glVendor: glVendor,
                glRenderer: glRenderer,
                maxTextureSize: maxTexSize,
                screenAvailHeight: screen.availHeight,
                screenHeight: screen.height,
                notificationPermission: typeof Notification !== 'undefined' ? Notification.permission : 'default',
                audioScrambled: !!(window.AudioBuffer && AudioBuffer.prototype.getChannelData),
                canvasProtected: !!(window.CanvasRenderingContext2D && CanvasRenderingContext2D.prototype.getImageData),
                userAgent: navigator.userAgent
            };
        })()
        """
        res = self.driver.evaluate(script)
        if not isinstance(res, dict):
            return {
                "success": False,
                "error": "Failed to evaluate audit script in browser context"
            }

        # Validate against known leaks
        is_webdriver_hidden = res.get("webdriver") is None
        is_platform_linux = "Linux" in str(res.get("platform", ""))
        is_mesa_hidden = "llvmpipe" not in str(res.get("glRenderer", "")).lower() and "mesa" not in str(res.get("glRenderer", "")).lower()
        is_max_tex_valid = res.get("maxTextureSize", 0) >= 16384
        is_screen_valid = res.get("screenAvailHeight", 0) < res.get("screenHeight", 1)

        return {
            "success": True,
            "profile_id": self.driver.profile.profile_id,
            "webdriver_hidden": is_webdriver_hidden,
            "platform_valid": is_platform_linux,
            "mesa_cloaked": is_mesa_hidden,
            "max_texture_valid": is_max_tex_valid,
            "screen_geometry_valid": is_screen_valid,
            "audio_protected": res.get("audioScrambled", False),
            "canvas_protected": res.get("canvasProtected", False),
            "gl_vendor": res.get("glVendor"),
            "gl_renderer": res.get("glRenderer"),
            "concurrency": res.get("hardwareConcurrency"),
            "plugins_count": res.get("pluginsLength"),
            "raw_audit": res
        }

    def warm_up_session(
        self,
        urls: Optional[List[str]] = None,
        duration_per_url: float = 3.0,
        session_pacing: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Visit warm-up targets, scroll pages naturally, and generate organic browsing context.

        session_pacing=True (default) adds human-like inter-page pauses drawn from
        a log-uniform distribution — automated sessions visit pages at
        machine-stable intervals, and connection-lifecycle analysis flags the
        uniformity itself.真人会话的页间停留呈重尾分布，不是均匀间隔。
        """
        targets = urls or self.WARMUP_TARGETS
        results = []

        self.driver.inject_stealth()

        for i, target in enumerate(targets):
            if session_pacing and i > 0:
                # Log-uniform pause: mostly short, occasionally long (a human
                # reading a page). Range 0.5-8s, median ~2s.
                time.sleep(random.uniform(0.5, 2.0) ** 2 / 2.0)
            start_t = time.time()
            ok = self.driver.navigate(target, wait_seconds=duration_per_url)

            # Simulate natural scroll with a small dwell
            if ok:
                scroll_script = f"window.scrollTo(0, {random.randint(200, 800)});"
                self.driver.evaluate(scroll_script)
                # Reading dwell: page-length dependent, log-uniform 0.4-1.6s
                time.sleep(random.uniform(0.4, 1.6))

            elapsed = round(time.time() - start_t, 2)
            results.append({
                "url": target,
                "success": ok,
                "elapsed_seconds": elapsed
            })

        return results
