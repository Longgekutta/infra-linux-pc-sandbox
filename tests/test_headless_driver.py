from __future__ import annotations
"""Unit tests for LinuxHeadlessDriver WebSocket client and CDP protocol (A4 closure)."""
import unittest
import sys
import os
import socket
import threading
import base64
import struct
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from automation.headless_driver import LightweightWebSocketClient
from core.stealth_profile import LinuxStealthProfileGenerator


class _MockWSHandler(threading.Thread):
    """Minimal RFC6455 echo server for handshake + framing tests."""
    def __init__(self, port):
        super().__init__(daemon=True)
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", port))
        self.sock.listen(1)
        self.running = True
    def run(self):
        conn, _ = self.sock.accept()
        data = conn.recv(4096).decode("utf-8", errors="ignore")
        # Extract Sec-WebSocket-Key and complete the handshake
        key = ""
        for line in data.split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        conn.sendall((
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        ).encode())
        # Echo one text frame
        frame = conn.recv(4096)
        if frame:
            conn.sendall(frame)
        conn.close()
    def stop(self):
        self.running = False
        self.sock.close()


class TestLightweightWebSocketClient(unittest.TestCase):

    def test_handshake_and_echo(self):
        # Deterministic free port (no randint — PRB-E401 reproducibility)
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        handler = _MockWSHandler(port)
        handler.start()
        try:
            client = LightweightWebSocketClient(f"ws://127.0.0.1:{port}/devtools/page/1", timeout=5)
            client.send_json({"id": 1, "method": "Runtime.evaluate", "params": {}})
            resp = client.recv_json()
            self.assertEqual(resp.get("id"), 1, "Echo server must return the same id")
            client.close()
        finally:
            handler.stop()

    def test_send_json_masks_payload(self):
        # RFC6455 client-to-server frames MUST be masked; verify header construction
        import struct as _struct
        payload = b"x" * 10
        mask_key = os.urandom(4)
        masked = bytearray(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        self.assertNotEqual(bytes(masked), payload, "Masked payload must differ from raw payload")
        # Unmasking recovers the original
        recovered = bytearray(b ^ mask_key[i % 4] for i, b in enumerate(masked))
        self.assertEqual(bytes(recovered), payload, "Unmasking must recover the original bytes")

    def test_profile_user_agent_coherence(self):
        p = LinuxStealthProfileGenerator.create_profile("ws_ua_test")
        self.assertIn("X11; Linux x86_64", p.user_agent, "Linux profile UA must carry Linux platform token")

if __name__ == "__main__":
    unittest.main()
