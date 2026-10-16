from __future__ import annotations
"""
Leak Selftest Module - Linux PC Sandbox (CDP Detection Leak Self-Verifier)
Runs an in-page probe against the running browser and asserts that the stealth
layer has not regressed after upgrades. Detects the two industry-standard CDP
leak vectors (cf. V8 value-mirror analysis):
  1. console.debug error.stack getter probe (Runtime domain enabled signal)
  2. prototype-chain Proxy ownKeys probe (console groupEnd preview signal)

Every probe returns a boolean that is computed entirely page-side; the host
side only reads the verdict. Run this after any stealth-script change: a
regression shows up as leak_detected=true before a real target flags you.
"""

from typing import Dict, Any
from automation.headless_driver import LinuxHeadlessDriver

# Page-side probes. Each returns {leak: bool} computed inside the page.
PROBE_CONSOLE_STACK = r"""
(() => {
    let detected = false;
    try {
        const e = new Error();
        Object.defineProperty(e, "stack", {
            configurable: false, enumerable: false,
            get() { detected = true; return ""; },
        });
        console.debug(e);
    } catch (err) { detected = false; }
    return {probe: "console_stack", leak: detected};
})()
"""

PROBE_PROXY_OWNKEYS = r"""
(() => {
    let detected = false;
    try {
        const trap = new Proxy({}, { ownKeys() { detected = true; return []; } });
        const obj = Object.create(trap);
        console.groupEnd(obj);
    } catch (err) { detected = false; }
    return {probe: "proxy_ownkeys", leak: detected};
})()
"""

PROBE_WEBDRIVER = r"""
(() => {
    return {probe: "webdriver", leak: navigator.webdriver === true};
})()
"""

PROBE_PLUGINS_COUNT = r"""
(() => {
    return {probe: "plugins", leak: navigator.plugins.length === 0};
})()
"""

ALL_PROBES = [PROBE_CONSOLE_STACK, PROBE_PROXY_OWNKEYS, PROBE_WEBDRIVER, PROBE_PLUGINS_COUNT]


def run_leak_selftest(driver: LinuxHeadlessDriver) -> Dict[str, Any]:
    """
    Run every leak probe against the active browser page.
    Returns {"clean": bool, "leaks": [..], "results": [..]}.
    clean=True means no leak vector fired — stealth layer intact.
    """
    results = []
    for probe_src in ALL_PROBES:
        res = driver.evaluate(probe_src)
        if isinstance(res, dict):
            results.append(res)
        else:
            results.append({"probe": "unknown", "leak": True, "error": "probe evaluation failed"})

    leaks = [r["probe"] for r in results if r.get("leak")]
    return {"clean": not leaks, "leaks": leaks, "results": results}
