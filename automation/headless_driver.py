from __future__ import annotations
"""
Headless Driver Module - Linux PC Sandbox
Pure Python, zero-dependency Chrome DevTools Protocol (CDP) client over RFC 6455 WebSockets.
Communicates directly with headless or Xvfb-backed Chromium processes on cloud Linux servers.
Injects stealth hooks, handles navigation, DOM evaluations, screenshots, and cookie synchronization.
"""

import os
import sys
import json
import time
import random
import socket
import struct
import base64
import hashlib
import urllib.request
import urllib.parse
import logging
from typing import Dict, Any, List, Optional, Tuple
from bridge.shared_schema import PCBrowserProfile
from core.stealth_profile import LinuxStealthProfileGenerator

logger = logging.getLogger("HeadlessDriver")

class LightweightWebSocketClient:
    """
    Standard-library RFC 6455 WebSocket client for lightweight CDP communication.
    Zero external dependencies, ideal for minimalist Linux container environments.
    """

    def __init__(self, ws_url: str, timeout: float = 10.0):
        self.ws_url = ws_url
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self._msg_id = 0
        self._connect()

    def _connect(self):
        parsed = urllib.parse.urlparse(self.ws_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        self.sock = socket.create_connection((host, port), timeout=self.timeout)

        # Generate Sec-WebSocket-Key
        raw_key = os.urandom(16)
        sec_key = base64.b64encode(raw_key).decode("ascii")

        # Browser-grade handshake headers: anti-bot systems fingerprint the WebSocket
        # handshake (Origin / UA / header set), and minimal handshakes are a bot tell
        # (WebSocket bot detection: handshake fingerprinting). Chrome CDP connections
        # to localhost do not send Origin, but a Chrome-consistent UA and the full
        # standard header set keep the upgrade indistinguishable from a
        # browser-initiated one to any middlebox inspecting the handshake.
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Pragma: no-cache\r\n"
            f"Cache-Control: no-cache\r\n"
            f"User-Agent: {self.profile.user_agent}\r\n"
            f"Sec-WebSocket-Key: {sec_key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits\r\n"
            f"\r\n"
        )
        self.sock.sendall(handshake.encode("utf-8"))

        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("WebSocket handshake connection closed unexpectedly")
            response += chunk

        status_line = response.split(b"\r\n")[0].decode("latin-1")
        if "101" not in status_line:
            raise ConnectionError(f"WebSocket handshake failed: {status_line}")

    def send_json(self, payload: Dict[str, Any]) -> None:
        """Send JSON payload as a masked text frame (RFC 6455)."""
        data = json.dumps(payload).encode("utf-8")
        length = len(data)

        # Byte 0: FIN (0x80) | Text Opcode (0x01)
        header = bytearray([0x81])

        # Byte 1+: Mask bit (0x80) + payload len
        mask_key = os.urandom(4)
        if length <= 125:
            header.append(0x80 | length)
        elif length <= 65535:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))

        header.extend(mask_key)

        # Mask data
        masked_data = bytearray(length)
        for i in range(length):
            masked_data[i] = data[i] ^ mask_key[i % 4]

        self.sock.sendall(header + masked_data)

    def recv_json(self) -> Dict[str, Any]:
        """Receive and decode a WebSocket text frame."""
        # Read first 2 bytes
        head = self._recv_exact(2)
        opcode = head[0] & 0x0F
        if opcode == 0x08:  # Close frame
            raise ConnectionResetError("WebSocket closed by remote peer")

        masked = bool(head[1] & 0x80)
        pay_len = head[1] & 0x7F

        if pay_len == 126:
            pay_len = struct.unpack("!H", self._recv_exact(2))[0]
        elif pay_len == 127:
            pay_len = struct.unpack("!Q", self._recv_exact(8))[0]

        mask = self._recv_exact(4) if masked else None
        body = bytearray(self._recv_exact(pay_len))

        if masked and mask:
            for i in range(pay_len):
                body[i] ^= mask[i % 4]

        return json.loads(body.decode("utf-8", errors="replace"))

    def _recv_exact(self, num_bytes: int) -> bytes:
        data = bytearray()
        while len(data) < num_bytes:
            packet = self.sock.recv(num_bytes - len(data))
            if not packet:
                raise ConnectionResetError("Socket closed prematurely while reading frame")
            data.extend(packet)
        return bytes(data)

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError as e:
                logger.debug("Error closing socket: %s", e)
            self.sock = None


class LinuxHeadlessDriver:
    """
    Automated Headless & Virtual Display (Xvfb) Chromium controller.
    Provides stealth script injection, page navigation, DOM query, and cookie management.
    """

    def __init__(self, cdp_port: int, profile: PCBrowserProfile):
        self.cdp_port = cdp_port
        self.profile = profile
        self.ws_client: Optional[LightweightWebSocketClient] = None
        self._command_id = 1

    def is_connected(self) -> bool:
        """Verify CDP port responsiveness."""
        try:
            url = f"http://127.0.0.1:{self.cdp_port}/json/version"
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return "webSocketDebuggerUrl" in data
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            logger.debug("CDP port %s not connected: %s", self.cdp_port, e)
            return False

    def get_pages(self) -> List[Dict[str, Any]]:
        """List active Chromium pages."""
        try:
            url = f"http://127.0.0.1:{self.cdp_port}/json/list"
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            logger.debug("Failed to list CDP pages: %s", e)
            return []

    def get_stealth_script(self) -> str:
        """Retrieve Linux anti-detect stealth script for this profile."""
        return LinuxStealthProfileGenerator.build_linux_stealth_script(self.profile)

    def attach_page(self, page_index: int = 0) -> bool:
        """Attach WebSocket client to the target page."""
        pages = self.get_pages()
        if not pages:
            # Try to create a new page if none exists
            try:
                new_url = f"http://127.0.0.1:{self.cdp_port}/json/new"
                with urllib.request.urlopen(new_url, timeout=2.0) as resp:
                    page = json.loads(resp.read().decode("utf-8"))
                    pages = [page]
            except Exception as e:
                logger.debug("Failed to create new CDP page: %s", e)
                return False

        target = pages[min(page_index, len(pages) - 1)]
        ws_url = target.get("webSocketDebuggerUrl")
        if not ws_url:
            return False

        try:
            if self.ws_client:
                self.ws_client.close()
            self.ws_client = LightweightWebSocketClient(ws_url, timeout=8.0)
            return True
        except Exception as e:
            logger.debug("Failed to connect WebSocket client: %s", e)
            return False

    def call_cdp(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a synchronous CDP protocol call over the page WebSocket."""
        if not self.ws_client:
            if not self.attach_page():
                return {"error": "Failed to attach CDP page"}

        cmd_id = self._command_id
        self._command_id += 1

        payload = {
            "id": cmd_id,
            "method": method,
            "params": params or {}
        }

        try:
            # Human-like inter-command jitter (see windows-pc-sandbox stealth_cdp):
            # keeps the CDP command stream timing distribution human-paced.
            time.sleep(random.uniform(0.002, 0.012))
            self.ws_client.send_json(payload)
            # Loop until response with matching ID is received (ignore asynchronous events)
            start_t = time.time()
            while time.time() - start_t < 15.0:
                res = self.ws_client.recv_json()
                if res.get("id") == cmd_id:
                    return res
            return {"error": "CDP call timed out waiting for response"}
        except Exception as e:
            return {"error": str(e)}

    def inject_stealth(self) -> bool:
        """Inject Linux stealth payload to evaluate on every new document."""
        script = self.get_stealth_script()
        res = self.call_cdp("Page.addScriptToEvaluateOnNewDocument", {"source": script})
        return "result" in res

    def navigate(self, url: str, wait_seconds: float = 2.0) -> bool:
        """Navigate to target URL and wait for initial render."""
        res = self.call_cdp("Page.navigate", {"url": url})
        time.sleep(wait_seconds)
        return "result" in res

    def evaluate(self, expression: str) -> Any:
        """Evaluate a JavaScript expression in the current page context."""
        res = self.call_cdp("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True
        })
        if "result" in res and "result" in res["result"]:
            return res["result"]["result"].get("value")
        return None

    def evaluate_in_isolated_world(self, expression: str, world_name: str = "linux_isolated_world") -> Dict[str, Any]:
        """
        Execute JavaScript within an isolated execution world (Page.createIsolatedWorld).
        Prevents WAFs and anti-bot systems from observing CDP evaluations or prototype changes.
        """
        frame_tree = self.call_cdp("Page.getFrameTree")
        frame_id = None
        if isinstance(frame_tree, dict):
            res_obj = frame_tree.get("result")
            if isinstance(res_obj, dict):
                ft_obj = res_obj.get("frameTree")
                if isinstance(ft_obj, dict):
                    f_obj = ft_obj.get("frame")
                    if isinstance(f_obj, dict):
                        frame_id = f_obj.get("id")

        if not frame_id:
            return self.call_cdp("Runtime.evaluate", {"expression": expression, "returnByValue": True})

        world_res = self.call_cdp("Page.createIsolatedWorld", {
            "frameId": frame_id,
            "worldName": world_name,
            "grantUniveralAccess": True
        })

        context_id = None
        if isinstance(world_res, dict):
            w_res = world_res.get("result")
            if isinstance(w_res, dict):
                context_id = w_res.get("executionContextId")

        if not context_id:
            return self.call_cdp("Runtime.evaluate", {"expression": expression, "returnByValue": True})

        return self.call_cdp("Runtime.evaluate", {
            "expression": expression,
            "contextId": context_id,
            "returnByValue": True
        })

    def get_cookies(self) -> List[Dict[str, Any]]:
        """Extract decrypted cookies from running browser session via Network.getCookies."""
        res = self.call_cdp("Network.getCookies")
        if "result" in res and "cookies" in res["result"]:
            return res["result"]["cookies"]
        elif "cookies" in res:
            return res["cookies"]
        return []

    def set_cookies(self, cookies: List[Dict[str, Any]]) -> bool:
        """Inject cookies into running browser session via Network.setCookies."""
        if not cookies:
            return True
        res = self.call_cdp("Network.setCookies", {"cookies": cookies})
        return "error" not in res

    def capture_screenshot(self, output_file: str) -> bool:
        """Capture viewport screenshot and save as PNG file."""
        res = self.call_cdp("Page.captureScreenshot", {"format": "png"})
        if "result" in res and "data" in res["result"]:
            raw_b64 = res["result"]["data"]
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            with open(output_file, "wb") as f:
                f.write(base64.b64decode(raw_b64))
            return True
        return False

    def close(self):
        """Close WebSocket session."""
        if self.ws_client:
            self.ws_client.close()
            self.ws_client = None

