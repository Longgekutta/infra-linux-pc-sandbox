"""
Camoufox Driver Module - Linux PC Sandbox (Gecko Kernel, Fourth Engine in the Fleet)
Wraps the official `camoufox` Python launcher (Camoufox = Firefox fork with
engine-level anti-fingerprinting done in C++) as the fourth automation driver.

Why this exists (breaking out of the Blink kernel):
  All previous drivers drive Chromium (Blink). Camoufox is Gecko — a different
  kernel lineage. Fleet strategy "dual-kernel formation": routine targets ride
  the Blink drivers (CDP ecosystem complete), high-adversarial targets switch
  to the Gecko driver. Same IP, different fingerprint lineage — the anti-bot
  sees two entirely different "people".

Kernel lineage note:
  - Camoufox = Gecko (Firefox fork), engine-level patches, Juggler protocol
    (CDP Runtime.enable leaks structurally cannot exist).
  - Our other drivers = Blink (Chromium).

Reliability contract (verified, not assumed):
  - `camoufox` package installed (pip) + browser binary fetched
    (`python -m camoufox fetch`) -> full engine-level stealth.
  - package missing -> loud degradation (report unavailable), never silently
    fall back to Blink pretending to be Gecko.
"""
from __future__ import annotations

import json
import logging
import shutil
from typing import Dict, Any, Optional, List

logger = logging.getLogger("CamoufoxDriver")


def camoufox_available() -> bool:
    """Check the camoufox package AND its browser binary are installed.
    Both dimensions are required: a package without the Gecko binary cannot
    provide engine-level stealth, and must never silently fall back to Blink."""
    try:
        import camoufox  # noqa: F401
    except ImportError:
        return False
    return binary_installed()


def binary_installed() -> bool:
    """Check the Camoufox browser binary has been fetched."""
    try:
        from camoufox.pkgman import installed_path
        installed_path()
        return True
    except ImportError as e:
        import logging
        logging.getLogger("CamoufoxDriver").debug("pkgman missing: %s", e)
        return False
    except Exception as e:
        import logging
        logging.getLogger("CamoufoxDriver").debug("binary check: %s", e)
        return False


class CamoufoxDriver:
    """
    Fourth fleet driver: Gecko kernel via the Camoufox launcher (Playwright API
    under the hood — Camoufox patches Firefox and drives it over Juggler).
    """

    KERNEL = "gecko"

    def __init__(self, profile: Optional[Any] = None, headless: bool = True,
                 proxy: Optional[Dict[str, str]] = None):
        self.profile = profile
        self.headless = headless
        self.proxy = proxy
        self._pw = None
        self._browser = None
        self._page = None

    @property
    def available(self) -> bool:
        return camoufox_available()

    def launch(self, url: str = "https://example.com", **launch_opts) -> bool:
        """Launch Camoufox (Gecko) with engine-level anti-fingerprinting."""
        if not self.available:
            raise RuntimeError(
                "camoufox package not installed — pip install camoufox && "
                "python -m camoufox fetch. Loud failure: no Blink fallback.")
        try:
            from camoufox.sync_api import Camoufox
            opts: Dict[str, Any] = {"headless": self.headless}
            if self.proxy:
                opts["proxy"] = self.proxy
            opts.update(launch_opts)
            self._pw = Camoufox(**opts)
            self._browser = self._pw.__enter__()
            context = self._browser.new_context()
            self._page = context.new_page()
            if url:
                self._page.goto(url, timeout=30000)
            return True
        except Exception as e:
            logger.error("Camoufox launch failed: %s", e)
            self.close()
            return False

    def evaluate(self, expression: str) -> Any:
        """Evaluate JS in the Gecko page. Juggler protocol: no Runtime.enable
        exposure by construction."""
        if not self._page:
            return None
        return self._page.evaluate(expression)

    def get_cookies(self) -> List[Dict[str, Any]]:
        if not self._page:
            return []
        return self._page.context.cookies()

    def navigate(self, url: str) -> bool:
        if not self._page:
            return False
        self._page.goto(url, timeout=30000)
        return True

    def close(self) -> None:
        try:
            if self._pw:
                self._pw.__exit__(None, None, None)
        except Exception as e:
            logger.debug("Camoufox close: %s", e)
        finally:
            self._pw = self._browser = self._page = None

    def status(self) -> Dict[str, Any]:
        return {
            "kernel": self.KERNEL,
            "package_available": camoufox_available(),
            "binary_installed": binary_installed(),
            "launched": self._browser is not None,
        }
