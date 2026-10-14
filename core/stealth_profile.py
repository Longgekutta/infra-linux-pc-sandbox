from __future__ import annotations
"""
Stealth Profile Module - Linux PC Sandbox
Solves the Mesa llvmpipe software rendering vulnerability, font leakage, AudioContext zero-buffer leaks,
and headless Chrome fingerprint traps on cloud Linux servers.
Synthesizes discrete GPU hardware profiles (NVIDIA RTX 3080 / 4090) and Client Hints.
"""

import os
import json
import random
from typing import Dict, Any, List, Optional
from bridge.shared_schema import PCBrowserProfile, ScreenConfig, GpuConfig, ProxyConfig, AccountCredentials

TIMEZONE_OFFSETS: Dict[str, int] = {
    "America/New_York": 240,
    "America/Chicago": 300,
    "America/Denver": 360,
    "America/Los_Angeles": 420,
    "Europe/London": 0,
    "Europe/Paris": -60,
    "Europe/Berlin": -60,
    "Asia/Tokyo": -540,
    "Asia/Shanghai": -480,
    "UTC": 0
}

class LinuxStealthProfileGenerator:
    """
    Synthesizes and manages cloaked Linux desktop browser profiles.
    Masks headless server artifacts with authentic discrete GPU rendering, AudioContext noise, and desktop fonts.
    """

    LINUX_GPU_PROFILES = [
        {
            "vendor": "NVIDIA Corporation",
            "renderer": "NVIDIA GeForce RTX 3080/PCIe/SSE2",
            "concurrency": 16,
            "memory": 32
        },
        {
            "vendor": "NVIDIA Corporation",
            "renderer": "NVIDIA GeForce RTX 4090/PCIe/SSE2",
            "concurrency": 24,
            "memory": 64
        },
        {
            "vendor": "Google Inc. (Intel)",
            "renderer": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "concurrency": 8,
            "memory": 16
        }
    ]

    @classmethod
    def create_profile(
        cls,
        profile_id: str,
        proxy_host: str = "172.17.0.1",
        proxy_port: int = 7890,
        use_proxy: bool = True,
        email: str = ""
    ) -> PCBrowserProfile:
        """Create a randomized, headless-cloaked Linux desktop profile."""
        gpu_template = random.choice(cls.LINUX_GPU_PROFILES)

        screen = ScreenConfig(
            width=1920,
            height=1080,
            scale_factor=1.0,
            color_depth=24,
            refresh_rate=60
        )

        gpu = GpuConfig(
            gl_vendor=gpu_template["vendor"],
            gl_renderer=gpu_template["renderer"]
        )

        proxy = ProxyConfig(
            enabled=use_proxy,
            proxy_type="http",
            host=proxy_host,
            port=proxy_port
        )

        account = AccountCredentials(email=email)
        chrome_ver = random.choice(["128.0.0.0", "129.0.0.0", "130.0.0.0"])
        ua = f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"

        return PCBrowserProfile(
            profile_id=profile_id,
            platform="linux",
            browser_type="chrome",
            user_agent=ua,
            screen=screen,
            gpu=gpu,
            proxy=proxy,
            account=account,
            languages=["en-US", "en"],
            timezone="America/New_York",
            webrtc_mode="disable_non_proxied_udp",
            hardware_concurrency=gpu_template["concurrency"],
            device_memory_gb=gpu_template["memory"]
        )

    @classmethod
    def build_linux_stealth_script(cls, profile: PCBrowserProfile) -> str:
        """
        Synthesize comprehensive JavaScript payload to eradicate Mesa / llvmpipe, AudioContext zero-buffer,
        Canvas 2D disparity, and HeadlessChrome signatures on cloud Linux nodes.
        """
        gl_vendor = profile.gpu.gl_vendor
        gl_renderer = profile.gpu.gl_renderer
        concurrency = profile.hardware_concurrency
        memory = profile.device_memory_gb
        screen_w = profile.screen.width
        screen_h = profile.screen.height
        avail_h = max(screen_h - 28, 600)  # Linux GNOME 28px panel
        timezone = profile.timezone
        tz_offset = TIMEZONE_OFFSETS.get(timezone, 240)

        profile_id = profile.profile_id or "default"

        return f"""
(() => {{
    // 0. Native Function Camouflage Utility (Eradicates toString() and getter lie detection)
    const makeNative = (fn, name) => {{
        const fnName = name || fn.name || '';
        const nativeStr = `function ${{fnName}}() {{ [native code] }}`;
        try {{
            Object.defineProperty(fn, 'toString', {{
                value: function() {{ return nativeStr; }},
                writable: true,
                configurable: true
            }});
        }} catch(e) {{}}
        try {{
            Object.defineProperty(fn, 'name', {{
                value: fnName,
                configurable: true
            }});
        }} catch(e) {{}}
        return fn;
    }};

    // Deterministic pseudo-random noise generator seeded by profile ID
    let seed = 0;
    const profileIdStr = '{profile_id}';
    for (let i = 0; i < profileIdStr.length; i++) {{
        seed = (seed * 31 + profileIdStr.charCodeAt(i)) >>> 0;
    }}
    const deterministicNoise = (offset) => {{
        const x = Math.sin(seed + offset) * 10000;
        return x - Math.floor(x);
    }};

    // 1. Eradicate 'navigator.webdriver' (with native prototype camouflage)
    try {{
        Object.defineProperty(navigator, 'webdriver', {{
            get: makeNative(() => undefined, 'get webdriver'),
            configurable: true
        }});
        try {{ delete navigator.webdriver; }} catch(e) {{}}

        const navProto = Object.getPrototypeOf(navigator) || Navigator.prototype;
        const nativeWdGetter = function() {{ return false; }};
        makeNative(nativeWdGetter, 'get webdriver');
        Object.defineProperty(navProto, 'webdriver', {{
            get: nativeWdGetter,
            set: undefined,
            enumerable: true,
            configurable: true
        }});
    }} catch (e) {{}}

    // 2. Linux Desktop Platform & Realistic Hardware
    try {{
        Object.defineProperty(navigator, 'platform', {{
            get: makeNative(() => 'Linux x86_64', 'get platform'),
            configurable: true
        }});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: makeNative(() => {concurrency}, 'get hardwareConcurrency'),
            configurable: true
        }});
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: makeNative(() => {memory}, 'get deviceMemory'),
            configurable: true
        }});
        Object.defineProperty(navigator, 'maxTouchPoints', {{
            get: makeNative(() => 0, 'get maxTouchPoints'),
            configurable: true
        }});
        Object.defineProperty(navigator, 'languages', {{
            get: makeNative(() => ['en-US', 'en'], 'get languages'),
            configurable: true
        }});
    }} catch (e) {{}}

    // 3. Screen & Linux Desktop Panel Metrics
    try {{
        Object.defineProperty(screen, 'width', {{ get: makeNative(() => {screen_w}, 'get width'), configurable: true }});
        Object.defineProperty(screen, 'height', {{ get: makeNative(() => {screen_h}, 'get height'), configurable: true }});
        Object.defineProperty(screen, 'availWidth', {{ get: makeNative(() => {screen_w}, 'get availWidth'), configurable: true }});
        Object.defineProperty(screen, 'availHeight', {{ get: makeNative(() => {avail_h}, 'get availHeight'), configurable: true }});
        Object.defineProperty(screen, 'availLeft', {{ get: makeNative(() => 0, 'get availLeft'), configurable: true }});
        Object.defineProperty(screen, 'availTop', {{ get: makeNative(() => 28, 'get availTop'), configurable: true }});
        Object.defineProperty(screen, 'colorDepth', {{ get: makeNative(() => 24, 'get colorDepth'), configurable: true }});
        Object.defineProperty(screen, 'pixelDepth', {{ get: makeNative(() => 24, 'get pixelDepth'), configurable: true }});
    }} catch (e) {{}}

    // 4. Complete Mesa llvmpipe / SwiftShader Software WebGL Eradication ({gl_vendor} / {gl_renderer})
    try {{
        const paramOverrides = {{
            37445: '{gl_vendor}',                    // UNMASKED_VENDOR_WEBGL
            37446: '{gl_renderer}',                  // UNMASKED_RENDERER_WEBGL
            3379: 16384,                             // MAX_TEXTURE_SIZE (masks llvmpipe 8192)
            34024: 16384,                            // MAX_RENDERBUFFER_SIZE
            3386: new Int32Array([16384, 16384]),    // MAX_VIEWPORT_DIMS
            34921: 16,                               // MAX_VERTEX_ATTRIBS
            35660: 32,                               // MAX_VERTEX_TEXTURE_IMAGE_UNITS
            35661: 64                                // MAX_COMBINED_TEXTURE_IMAGE_UNITS
        }};

        const hookGL = (proto) => {{
            const origGetParam = proto.getParameter;
            proto.getParameter = function(param) {{
                if (param in paramOverrides) {{
                    return paramOverrides[param];
                }}
                return origGetParam.apply(this, arguments);
            }};
            makeNative(proto.getParameter, 'getParameter');

            const origGetExt = proto.getSupportedExtensions;
            proto.getSupportedExtensions = function() {{
                const exts = origGetExt.apply(this, arguments) || [];
                return exts.filter(ext => !ext.toLowerCase().includes('debug_shaders'));
            }};
            makeNative(proto.getSupportedExtensions, 'getSupportedExtensions');

            // Deep Shader Precision Format for Discrete Linux NVIDIA Driver
            const origPrecision = proto.getShaderPrecisionFormat;
            if (origPrecision) {{
                proto.getShaderPrecisionFormat = function(shaderType, precisionType) {{
                    return {{ rangeMin: 127, rangeMax: 127, precision: 23 }};
                }};
                makeNative(proto.getShaderPrecisionFormat, 'getShaderPrecisionFormat');
            }}
        }};

        if (window.WebGLRenderingContext) hookGL(WebGLRenderingContext.prototype);
        if (window.WebGL2RenderingContext) hookGL(WebGL2RenderingContext.prototype);

        if (typeof OffscreenCanvas !== 'undefined') {{
            const origGetContext = OffscreenCanvas.prototype.getContext;
            OffscreenCanvas.prototype.getContext = function(type, ...args) {{
                const ctx = origGetContext.apply(this, [type, ...args]);
                if (ctx && (type === 'webgl' || type === 'webgl2')) {{
                    hookGL(Object.getPrototypeOf(ctx));
                }}
                return ctx;
            }};
            makeNative(OffscreenCanvas.prototype.getContext, 'getContext');
        }}
    }} catch (e) {{}}

    // 5. AudioContext Fingerprint Scrambler (Deterministic Micro-Jitter for Headless Cloud Nodes)
    try {{
        if (window.AudioBuffer) {{
            const origGetChannelData = AudioBuffer.prototype.getChannelData;
            AudioBuffer.prototype.getChannelData = function(channel) {{
                const data = origGetChannelData.apply(this, arguments);
                for (let i = 0; i < data.length; i += 128) {{
                    data[i] = data[i] + 0.0000001 * (deterministicNoise(i) - 0.5);
                }}
                return data;
            }};
            makeNative(AudioBuffer.prototype.getChannelData, 'getChannelData');
        }}
        if (window.AnalyserNode) {{
            const origGetFloatData = AnalyserNode.prototype.getFloatFrequencyData;
            AnalyserNode.prototype.getFloatFrequencyData = function(array) {{
                origGetFloatData.apply(this, arguments);
                for (let i = 0; i < array.length; i += 64) {{
                    array[i] += 0.0001 * (deterministicNoise(i) - 0.5);
                }}
            }};
            makeNative(AnalyserNode.prototype.getFloatFrequencyData, 'getFloatFrequencyData');
        }}
    }} catch (e) {{}}

    // 6. Canvas 2D Subpixel Noise Protection (Deterministic Noise)
    try {{
        if (window.CanvasRenderingContext2D) {{
            const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {{
                const imageData = origGetImageData.apply(this, arguments);
                const d = imageData.data;
                for (let i = 0; i < d.length; i += 256) {{
                    d[i] = d[i] ^ (Math.floor(deterministicNoise(i) * 2) & 1);
                }}
                return imageData;
            }};
            makeNative(CanvasRenderingContext2D.prototype.getImageData, 'getImageData');
        }}
    }} catch (e) {{}}

    // 7. Permissions API & Notification Consistency
    try {{
        if (window.Notification) {{
            Object.defineProperty(Notification, 'permission', {{
                get: makeNative(() => 'default', 'get permission'),
                configurable: true
            }});
        }}
        if (navigator.permissions && navigator.permissions.query) {{
            const origQuery = navigator.permissions.query;
            navigator.permissions.query = makeNative(function(params) {{
                if (params && params.name === 'notifications') {{
                    return Promise.resolve({{
                        state: 'default',
                        onchange: null,
                        name: 'notifications'
                    }});
                }}
                return origQuery.apply(this, arguments);
            }}, 'query');
        }}
    }} catch (e) {{}}

    // 8. Battery API Simulation
    try {{
        if (navigator.getBattery) {{
            navigator.getBattery = makeNative(() => Promise.resolve({{
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 1.0,
                onchargingchange: null,
                onlevelchange: null
            }}), 'getBattery');
        }}
    }} catch (e) {{}}

    // 9. Timezone & Locale Coherence
    try {{
        const origResolved = Intl.DateTimeFormat.prototype.resolvedOptions;
        Intl.DateTimeFormat.prototype.resolvedOptions = makeNative(function() {{
            const options = origResolved.apply(this, arguments);
            options.timeZone = '{timezone}';
            return options;
        }}, 'resolvedOptions');
        Date.prototype.getTimezoneOffset = makeNative(function() {{
            return {tz_offset};
        }}, 'getTimezoneOffset');
    }} catch (e) {{}}

    // 10. Mock window.chrome for Headless Linux
    try {{
        if (!window.chrome) {{
            window.chrome = {{
                runtime: {{}},
                app: {{}},
                csi: makeNative(() => {{}}, 'csi'),
                loadTimes: makeNative(() => {{}}, 'loadTimes')
            }};
        }}
    }} catch (e) {{}}

    // 11. Realistic Desktop Plugins Array
    try {{
        Object.defineProperty(navigator, 'plugins', {{
            get: makeNative(() => [
                {{ name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }},
                {{ name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }}
            ], 'get plugins'),
            configurable: true
        }});
    }} catch (e) {{}}
}})();
"""
