#!/usr/bin/env python3
"""
Example: Linux Cloud PC Sandbox Workflow
Demonstrates:
1. Profile synthesis with discrete GPU cloaking (eradicating Mesa llvmpipe).
2. Docker / cgroup v2 container command assembly.
3. DNS-over-HTTPS (DoH) resolution & network leak prevention.
4. StateBridge export/import for synchronization with Windows PC Sandbox.
"""

import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge.shared_schema import PCBrowserProfile
from bridge.state_bridge import StateBridge
from core.stealth_profile import LinuxStealthProfileGenerator
from core.container_orchestrator import LinuxContainerOrchestrator
from core.cloud_network_router import LinuxCloudNetworkRouter
from core.consistency_audit import audit_profile_coherence
from core.leak_selftest import run_leak_selftest
from automation.headless_driver import LinuxHeadlessDriver
from automation.task_worker import LinuxTaskWorker

def main():
    print("=" * 80)
    print(" Linux PC Sandbox - Cloud-Native High-Throughput Worker Demo")
    print("=" * 80)

    # 1. Synthesize a hardened Linux profile
    print("\n[Step 1] Synthesizing Linux Stealth Profile (Mesa llvmpipe eradication)...")
    profile = LinuxStealthProfileGenerator.create_profile(
        profile_id="cloud_worker_us_01",
        proxy_host="198.23.190.46",
        proxy_port=17301,
        use_proxy=True,
        email="worker.us01@gmail.com"
    )
    print(f"  - Profile ID: {profile.profile_id}")
    print(f"  - Platform: {profile.platform}")
    print(f"  - Cloaked GPU: {profile.gpu.gl_renderer}")
    print(f"  - Concurrency: {profile.hardware_concurrency} Cores | Memory: {profile.device_memory_gb} GB")
    print(f"  - Timezone: {profile.timezone}")

    # 1b. Cross-layer coherence audit (catches configuration contradictions)
    print("\n[Step 1b] Cross-layer fingerprint coherence audit...")
    coherence = audit_profile_coherence(profile, egress_country="US")
    print(f"  - Coherence score: {coherence['score']}/100 | coherent: {coherence['coherent']}")
    for issue in coherence["issues"]:
        print(f"  - ⚠️ {issue}")

    # 2. Container Orchestration & cgroup v2 Limits
    print("\n[Step 2] Building Containerized Execution Plan (cgroup v2 quotas)...")
    orchestrator = LinuxContainerOrchestrator(
        base_data_dir=tempfile.gettempdir(),
        memory_limit="768m",
        cpu_quota=1.0
    )
    docker_cmd = orchestrator.build_docker_run_command(profile, cdp_port=9222)
    print(f"  - Generated Docker Command (First 6 flags): {' '.join(docker_cmd[:8])} ...")
    print(f"  - Memory Limit: {orchestrator.memory_limit}")
    print(f"  - CPU Limit: {orchestrator.cpu_quota} cores")

    # 3. Network Router & Anti-Leak Hardening
    print("\n[Step 3] Hardening Cloud Network Routing & DoH Leak Protection...")
    router = LinuxCloudNetworkRouter()
    chrome_net_args = router.get_chrome_network_args(profile.proxy)
    print("  - Chromium Network Hardening Flags:")
    for arg in chrome_net_args:
        print(f"      {arg}")

    # 4. Stealth Script Generation
    print("\n[Step 4] Inspecting Dynamic Injected Stealth Script...")
    script = LinuxStealthProfileGenerator.build_linux_stealth_script(profile)
    lines = script.strip().split("\n")
    print(f"  - Total Script Lines: {len(lines)}")
    print(f"  - Sample Head: {lines[0]}")
    print(f"  - Sample Body: {lines[10]}")

    # 5. StateBridge Cross-Sandbox Synchronization
    print("\n[Step 5] Demonstrating StateBridge Profile Export/Import...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        bridge = StateBridge(base_profile_dir=tmp_dir)

        # Save profile
        p_dir = bridge.get_profile_dir(profile.profile_id)
        os.makedirs(p_dir, exist_ok=True)
        with open(os.path.join(p_dir, "profile.json"), "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)

        # Create dummy session cookie state
        with open(os.path.join(p_dir, "session_state.json"), "w", encoding="utf-8") as f:
            json.dump({"cookies": [{"name": "SSID", "value": "test_token_xyz"}]}, f)

        # Export bundle
        bundle_file = os.path.join(tmp_dir, "exported_bundle.json")
        bridge.export_profile_bundle(profile.profile_id, bundle_file)
        print(f"  - Successfully exported bundle to: {bundle_file}")

        # Import into another workspace
        imported = bridge.import_profile_bundle(bundle_file)
        print(f"  - Successfully imported bundle: {imported.profile_id} (Platform: {imported.platform})")

    print("\n" + "=" * 80)
    print(" Linux PC Sandbox Workflow Completed Successfully!")
    print("=" * 80)

if __name__ == "__main__":
    main()
