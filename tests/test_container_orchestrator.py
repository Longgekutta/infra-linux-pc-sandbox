from __future__ import annotations
import unittest
import tempfile
import os
import shutil
from core.container_orchestrator import LinuxContainerOrchestrator
from core.stealth_profile import LinuxStealthProfileGenerator

class TestLinuxContainerOrchestrator(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = LinuxContainerOrchestrator(
            base_data_dir=self.temp_dir,
            memory_limit="512m",
            cpu_quota=0.75
        )
        self.profile = LinuxStealthProfileGenerator.create_profile("docker_test_01")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_docker_run_command(self):
        cmd = self.orchestrator.build_docker_run_command(self.profile, cdp_port=9230)
        self.assertIn("docker", cmd, "Command must invoke docker binary")
        self.assertIn("run", cmd, "Command must execute docker run")
        self.assertIn("--memory", cmd, "Command must set container memory limit")
        self.assertIn("512m", cmd, "Memory limit flag must match configured 512m")
        self.assertIn("--cpus", cmd, "Command must set container CPU quota")
        self.assertIn("--shm-size", cmd, "Command must configure shm-size to prevent crash")
        self.assertIn("2g", cmd, "shm-size must be at least 2g")
        self.assertIn("127.0.0.1:9230:9222", cmd, "Port binding must map 9230 to container 9222")

    def test_build_local_chromium_command(self):
        cmd = self.orchestrator.build_local_chromium_command(self.profile, cdp_port=9231, url="https://example.com")
        self.assertIn("--remote-debugging-port=9231", cmd, "Command must set allocated remote debugging port")
        self.assertIn("--headless=new", cmd, "Command must enable modern Chrome new headless mode")
        self.assertIn("https://example.com", cmd, "Command must pass target navigation URL")

    def test_get_free_port(self):
        port = LinuxContainerOrchestrator.get_free_port(9200)
        self.assertGreaterEqual(port, 9200, f"Allocated free port {port} must be >= 9200")

if __name__ == "__main__":
    unittest.main()
