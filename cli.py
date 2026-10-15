#!/usr/bin/env python3
"""
Linux PC Sandbox - Unified Command-Line Interface (CLI)
Cloud-Native High-Throughput Headless / Virtual Display Browser Anti-Detect Infrastructure.
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge.shared_schema import PCBrowserProfile
from bridge.state_bridge import StateBridge
from core.stealth_profile import LinuxStealthProfileGenerator
from core.container_orchestrator import LinuxContainerOrchestrator
from core.cloud_network_router import LinuxCloudNetworkRouter
from automation.headless_driver import LinuxHeadlessDriver
from automation.task_worker import LinuxTaskWorker

def get_base_dir() -> str:
    """Return local or cloud base directory for Linux profiles."""
    if sys.platform == "win32":
        return os.path.join(os.path.expanduser("~"), ".linux_sandboxes")
    return "/data/linux_sandboxes"

def main():
    parser = argparse.ArgumentParser(
        description="Linux PC Sandbox - Cloud-Native High-Throughput Browser Infrastructure"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list
    subparsers.add_parser("list", help="List all configured Linux browser profiles")

    # create
    create_p = subparsers.add_parser("create", help="Create a new Mesa-cloaked Linux profile")
    create_p.add_argument("profile_id", help="Unique profile ID (e.g. cloud_worker_01)")
    create_p.add_argument("--proxy-host", default="172.17.0.1", help="Upstream proxy host")
    create_p.add_argument("--proxy-port", type=int, default=7890, help="Upstream proxy port")
    create_p.add_argument("--no-proxy", action="store_true", help="Disable proxy routing")
    create_p.add_argument("--email", default="", help="Account email")

    # launch
    launch_p = subparsers.add_parser("launch", help="Launch profile container or local process")
    launch_p.add_argument("profile_id", help="Profile ID to launch")
    launch_p.add_argument("--port", type=int, default=0, help="Explicit CDP port (0 for auto)")
    launch_p.add_argument("--mode", choices=["container", "local"], default="container", help="Launch mode")
    launch_p.add_argument("--url", default="https://en.wikipedia.org", help="Initial navigation URL")

    # worker
    worker_p = subparsers.add_parser("worker", help="Run automated warm-up and maintenance cycle")
    worker_p.add_argument("profile_id", help="Profile ID to run worker on")
    worker_p.add_argument("--port", type=int, default=9222, help="Target CDP port")
    worker_p.add_argument("--cycles", type=int, default=2, help="Number of warm-up cycles")

    # audit
    audit_p = subparsers.add_parser("audit", help="Audit CDP endpoint stealth and Mesa cloaking")
    audit_p.add_argument("--port", type=int, default=9222, help="CDP port to audit")

    # import
    import_p = subparsers.add_parser("import", help="Import session bundle from Windows sandbox")
    import_p.add_argument("bundle_path", help="Path to profile bundle .json")

    # export
    export_p = subparsers.add_parser("export", help="Export profile bundle for migration")
    export_p.add_argument("profile_id", help="Profile ID to export")
    export_p.add_argument("output_path", help="Destination path for bundle .json")

    args = parser.parse_args()
    base_dir = get_base_dir()
    os.makedirs(base_dir, exist_ok=True)
    orchestrator = LinuxContainerOrchestrator(base_data_dir=base_dir)

    if args.command == "list":
        profiles = []
        for d in os.listdir(base_dir):
            cfg_path = os.path.join(base_dir, d, "profile.json")
            try:
                # EAFP: open directly instead of an exists/isfile probe (TOCTOU, CWE-367)
                with open(cfg_path, "r", encoding="utf-8") as f:
                    p = PCBrowserProfile.from_dict(json.load(f))
                    profiles.append(p)
            except FileNotFoundError:
                continue  # directory without profile.json: not a profile, skip
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"[!] Skipping corrupt profile config {cfg_path}: {e}", file=sys.stderr)

        print(f"\n[Linux-PC-Sandbox] Found {len(profiles)} registered profiles:")
        print(f"{'Profile ID':<20} {'Platform':<10} {'GPU Renderer':<45} {'Proxy':<20}")
        print("-" * 100)
        for p in profiles:
            proxy_str = f"{p.proxy.host}:{p.proxy.port}" if p.proxy.enabled else "Direct"
            print(f"{p.profile_id:<20} {p.platform:<10} {p.gpu.gl_renderer[:42]:<45} {proxy_str:<20}")
        print()

    elif args.command == "create":
        profile = LinuxStealthProfileGenerator.create_profile(
            profile_id=args.profile_id,
            proxy_host=args.proxy_host,
            proxy_port=args.proxy_port,
            use_proxy=not args.no_proxy,
            email=args.email
        )
        p_dir = orchestrator.get_profile_data_dir(args.profile_id)
        os.makedirs(p_dir, exist_ok=True)
        cfg_file = os.path.join(p_dir, "profile.json")
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"[Linux-PC-Sandbox] Successfully created profile: {profile.profile_id}")
        print(f"  - Config file: {cfg_file}")
        print(f"  - Cloaked GPU: {profile.gpu.gl_renderer}")
        print(f"  - Concurrency: {profile.hardware_concurrency} cores, Memory: {profile.device_memory_gb}GB")

    elif args.command == "launch":
        cfg_file = os.path.join(orchestrator.get_profile_data_dir(args.profile_id), "profile.json")
        if not os.path.isfile(cfg_file):
            print(f"Error: Profile '{args.profile_id}' not found.")
            sys.exit(1)

        with open(cfg_file, "r", encoding="utf-8") as f:
            profile = PCBrowserProfile.from_dict(json.load(f))

        port = args.port or orchestrator.get_free_port(9222)
        print(f"[Linux-PC-Sandbox] Launching profile '{profile.profile_id}' in {args.mode} mode on port {port}...")

        if args.mode == "container":
            cmd = orchestrator.build_docker_run_command(profile, cdp_port=port)
            print("Generated Docker run command:")
            print(" ".join(cmd))
            print("\nNote: Execute command on Docker host or run with --mode local on desktop.")
        else:
            cmd = orchestrator.build_local_chromium_command(profile, cdp_port=port, url=args.url)
            print("Generated Local Chromium command:")
            print(" ".join(cmd))

    elif args.command == "audit":
        profile = LinuxStealthProfileGenerator.create_profile("audit_probe")
        driver = LinuxHeadlessDriver(cdp_port=args.port, profile=profile)
        if not driver.is_connected():
            print(f"Error: No responsive Chromium browser found on port {args.port}.")
            sys.exit(1)

        print(f"[Linux-PC-Sandbox] Connected to CDP on port {args.port}. Running stealth audit...")
        worker = LinuxTaskWorker(driver)
        driver.inject_stealth()
        audit_res = worker.verify_stealth_integrity()
        print(json.dumps(audit_res, indent=2))
        driver.close()

    elif args.command == "worker":
        cfg_file = os.path.join(orchestrator.get_profile_data_dir(args.profile_id), "profile.json")
        if not os.path.isfile(cfg_file):
            print(f"Error: Profile '{args.profile_id}' not found.")
            sys.exit(1)

        with open(cfg_file, "r", encoding="utf-8") as f:
            profile = PCBrowserProfile.from_dict(json.load(f))

        driver = LinuxHeadlessDriver(cdp_port=args.port, profile=profile)
        if not driver.is_connected():
            print(f"Error: CDP endpoint on port {args.port} unreachable.")
            sys.exit(1)

        print(f"[Linux-PC-Sandbox] Starting worker cycle for '{profile.profile_id}'...")
        worker = LinuxTaskWorker(driver)
        results = worker.warm_up_session()
        print(f"[Linux-PC-Sandbox] Warm-up finished ({len(results)} pages processed):")
        for r in results:
            print(f"  - {r['url']}: {'OK' if r['success'] else 'FAIL'} ({r['elapsed_seconds']}s)")
        driver.close()

    elif args.command == "import":
        bridge = StateBridge(base_profile_dir=base_dir)
        imported = bridge.import_profile_bundle(args.bundle_path)
        print(f"[Linux-PC-Sandbox] Successfully imported bundle for profile: {imported.profile_id}")
        print(f"  - Platform: {imported.platform}")
        print(f"  - Directory: {bridge.get_profile_dir(imported.profile_id)}")

    elif args.command == "export":
        bridge = StateBridge(base_profile_dir=base_dir)
        out = bridge.export_profile_bundle(args.profile_id, args.output_path)
        print(f"[Linux-PC-Sandbox] Exported profile '{args.profile_id}' to: {out}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
