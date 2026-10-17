from __future__ import annotations
"""
Container Orchestrator Module - Linux PC Sandbox
Manages isolated Docker / OCI container sandboxes and local Xvfb virtual displays on Linux.
Enforces cgroup v2 resource quotas (memory/CPU limits) to maximize container concurrency.
"""

import os
import sys
import shutil
import socket
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from bridge.shared_schema import PCBrowserProfile

def _shared_disable_features() -> str:
    """Chromium disable-features list from the shared knowledge base."""
    from core.knowledge_sync import load_shared
    return load_shared().get("chromium_disable_features",
                             "Translate,OptimizationHints,AudioServiceSandbox")


class LinuxContainerOrchestrator:
    """
    Orchestrates the lifecycle of scalable Linux desktop browser sandboxes.
    Supports both Containerized (Docker) and Local Virtual Display (Xvfb) modes.
    """

    def __init__(
        self,
        base_data_dir: str = "/data/linux_sandboxes",
        image_name: str = "linux-pc-sandbox:latest",
        memory_limit: str = "768m",
        cpu_quota: float = 1.0
    ):
        self.base_data_dir = base_data_dir
        self.image_name = image_name
        self.memory_limit = memory_limit
        self.cpu_quota = cpu_quota

    def get_profile_data_dir(self, profile_id: str) -> str:
        return os.path.join(self.base_data_dir, profile_id)

    @staticmethod
    def get_free_port(start_port: int = 9222) -> int:
        """Find an available TCP port for remote debugging by verifying atomic bindability."""
        port = start_port
        while port < 60000:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", port))
                    return port
            except OSError:
                port += 1
        return 9222

    def build_docker_run_command(
        self,
        profile: PCBrowserProfile,
        cdp_port: int,
        bind_host: str = "127.0.0.1"
    ) -> List[str]:
        """
        Assemble hardened Docker run command with cgroup v2 limits and profile isolation.
        """
        data_dir = self.get_profile_data_dir(profile.profile_id)
        os.makedirs(data_dir, exist_ok=True)
        container_name = f"browser_{profile.profile_id}"

        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "--restart", "unless-stopped",
            "--shm-size", "2g",
            "--memory", self.memory_limit,
            "--cpus", str(self.cpu_quota),
            "-v", f"{data_dir}:/data/profile",
            "-p", f"{bind_host}:{cdp_port}:9222",
            "-e", f"DISPLAY_WIDTH={profile.screen.width}",
            "-e", f"DISPLAY_HEIGHT={profile.screen.height}",
            "-e", f"DISPLAY_DEPTH=24",
            "-e", f"TIMEZONE={profile.timezone}",
            self.image_name
        ]

        if profile.proxy.enabled:
            cmd.extend(["-e", f"HTTP_PROXY={profile.proxy.to_chrome_arg()}"])

        return cmd

    def build_local_chromium_command(
        self,
        profile: PCBrowserProfile,
        cdp_port: int,
        target_url: str = "https://accounts.google.com",
        url: Optional[str] = None
    ) -> List[str]:
        """
        Assemble direct Linux Chromium command (used in headless or Xvfb environments).
        """
        target = url or target_url
        data_dir = self.get_profile_data_dir(profile.profile_id)
        os.makedirs(data_dir, exist_ok=True)

        # Chromium automation switches from the shared knowledge base
        # (patchright-derived: which stock automation switches are tells).
        from core.knowledge_sync import automation_switches_to_remove
        args = [
            "chromium",
            f"--user-data-dir={data_dir}",
            f"--remote-debugging-port={cdp_port}",
            "--headless=new",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--force-color-profile=srgb",
            "--no-first-run",
            "--no-default-browser-check",
            f"--window-size={profile.screen.width},{profile.screen.height}",
            f"--webrtc-ip-handling-policy={profile.webrtc_mode}",
            f"--lang={profile.languages[0]}",
        ]
        # patchright-derived switch list: these are the stock automation switches
        # Playwright passes by default — we build our own command, so the correct
        # absorption is to NOT pass any of them (verify none leaked in).
        for sw in automation_switches_to_remove():
            if sw in args:
                args.remove(sw)
        args.append("--disable-features=" + _shared_disable_features())
        args.append(target)

        if profile.proxy.enabled:
            proxy_arg = profile.proxy.to_chrome_arg()
            if proxy_arg:
                args.append(proxy_arg)

        return args

    def destroy_sandbox(self, profile_id: str, wipe_data: bool = False) -> bool:
        """Stop and remove container and optionally wipe data directory."""
        container_name = f"browser_{profile_id}"
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        if wipe_data:
            data_dir = self.get_profile_data_dir(profile_id)
            if os.path.exists(data_dir):
                shutil.rmtree(data_dir, ignore_errors=True)
        return True
