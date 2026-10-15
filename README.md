# Linux PC Sandbox

> **Cloud-Native, High-Throughput Desktop Browser Anti-Detect Infrastructure for Headless Linux Fleets & Docker Containers.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Architecture: Master/Worker](https://img.shields.io/badge/Architecture-Cloud--Worker%20Fleet-orange.svg)](#architecture)
[![Mesa Cloaking](https://img.shields.io/badge/WebGL-Mesa%20llvmpipe%20Masked-success.svg)](#stealth-mechanics)

---

## 📖 Executive Summary

While **Windows PC Sandbox** acts as the high-trust Master node (leveraging authentic DirectX 11/12 ANGLE hardware rendering, native typography, and DPAPI encryption for account creation and human-in-the-loop workflows), **Linux PC Sandbox** is engineered from first principles as the **high-density, cloud-native Worker fleet**.

Running headless browsers on cloud Linux instances (AWS EC2, Alibaba Cloud, Hetzner, etc.) is notoriously vulnerable to detection by modern anti-bot systems (Cloudflare Turnstile, DataDome, Google reCAPTCHA Enterprise, Akamai Bot Manager) due to:
1. **Mesa / llvmpipe Software Rendering Leaks**: Headless Linux lacks physical GPUs, exposing software rasterizer strings.
2. **Headless Chrome Automation Artifacts**: `navigator.webdriver = true`, missing `window.chrome`, inconsistent plugins arrays.
3. **Typography & Font Starvation**: Bare-metal Linux containers only have generic Monospace fonts, failing canvas text fingerprint audits.
4. **Network & DNS Exposure**: Datacenter IP leaks, WebRTC UDP IP disclosure, and ISP DNS interception.

`linux-pc-sandbox` completely solves these cloud-native challenges, delivering an ultra-lightweight (768MB RAM/worker), containerized, anti-detect execution engine.

---

## 🏗️ Architecture & Cross-Platform Relationship

```
+-----------------------------------------------------------------------------------+
|                           THE TWO-TIER PC SANDBOX ECOSYSTEM                       |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [Tier 1: Master Node]                                                            |
|  windows-pc-sandbox (Native Windows 10/11)                                         |
|  * 100% Genuine DirectX D3D11 ANGLE Hardware Shaders                              |
|  * Native Segoe UI / DirectWrite Subpixel Font Metrics                           |
|  * Windows DPAPI Credential Vault & Real-Time RFC 6238 TOTP                       |
|  * Human-in-the-loop Account Creation, Identity Verification, Captcha Solver      |
|                                                                                   |
|                                       │                                           |
|                                       ▼  (StateBridge Export / Import)            |
|                     [Session Tokens, Cookies, LocalStorage]                       |
|                                       │                                           |
|                                       ▼                                           |
|  [Tier 2: High-Density Worker Fleet]                                              |
|  linux-pc-sandbox (Cloud Containers / Debian / Docker / Xvfb)                     |
|  * Mesa llvmpipe -> Discrete NVIDIA RTX 3080/4090 WebGL Cloaking                  |
|  * Multi-Font Pre-installed Packs (Liberation, Noto CJK, Emoji)                   |
|  * Pure Python RFC 6455 WebSocket CDP Automation (Zero Heavy Binaries)           |
|  * cgroup v2 Resource Quotas (768M RAM / 1.0 CPU limit per worker)                |
|  * DNS-over-HTTPS (DoH) Leak Shield & WebRTC IP Strict Isolation                 |
|  * 24/7 Automated Account Warm-up, Heartbeats, Session Keep-alive                 |
+-----------------------------------------------------------------------------------+
```

---

## 🛡️ Anti-Detect & Stealth Mechanics

### 1. Mesa llvmpipe Software Rendering Eradication
Cloud servers without dedicated GPUs default to software rendering (`Mesa llvmpipe`, `SwiftShader`). Anti-bot engines immediately flag these signatures as automated scrapers. `linux-pc-sandbox` injects dynamic WebGL prototypes at the engine boundary (`Page.addScriptToEvaluateOnNewDocument`), masking:
- `UNMASKED_VENDOR_WEBGL (37445)` -> Discrete GPU Vendor (e.g. `NVIDIA Corporation`)
- `UNMASKED_RENDERER_WEBGL (37446)` -> High-end GPU Model (e.g. `NVIDIA GeForce RTX 4090/PCIe/SSE2`)

### 2. Elimination of Headless Automation Traps
- Removes `navigator.webdriver` from prototypes and property descriptors.
- Establishes realistic `navigator.hardwareConcurrency` (8-24 cores) and `navigator.deviceMemory` (16-64 GB).
- Restores `window.chrome.runtime` and realistic desktop plugins array.

### 3. Typography & Subpixel Font Rendering
The deployment image embeds full font packs:
- `fonts-liberation`, `fonts-noto-color-emoji`, `fonts-dejavu-core`, `fonts-noto-cjk`
Guarantees consistent text metrics on HTML5 Canvas and offscreen rendering contexts.

### 4. Zero-Leak Cloud Network Protection
- Strict WebRTC policy: `--force-webrtc-ip-handling-policy=disable_non_proxied_udp`
- Encrypted DNS: Enforces DNS-over-HTTPS (`--dns-over-https-mode=secure`) preventing ISP/cloud DNS eavesdropping.
- Proxy egress verification via integrated `LinuxCloudNetworkRouter`.

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- Chromium Browser (or Docker for containerized fleet deployment)
- Xvfb (for virtual X11 display on headless Linux servers)

### 2. Installation
```bash
git clone https://github.com/Longgekutta/infra-linux-pc-sandbox.git
cd linux-pc-sandbox
pip install -r requirements.txt
```

### 3. Run Self-Verification Demo
```bash
python examples/linux_task_runner.py
```

### 4. Run Full Test Suite
```bash
python -m unittest discover tests
```

---

## 💻 CLI Command Reference

The unified CLI provides full orchestration over profiles, containers, and maintenance cycles:

```bash
# 1. List configured profiles
python cli.py list

# 2. Create a new Mesa-cloaked profile
python cli.py create worker_us_01 --proxy-host 198.23.190.46 --proxy-port 17301 --email worker01@gmail.com

# 3. Launch container execution
python cli.py launch worker_us_01 --mode container --port 9222

# 4. Run automated warm-up and maintenance cycle
python cli.py worker worker_us_01 --port 9222 --cycles 2

# 5. Audit active browser stealth parameters
python cli.py audit --port 9222

# 6. Import session state bundle exported from Windows PC Sandbox
python cli.py import /path/to/windows_bundle.json

# 7. Export profile bundle for backup or migration
python cli.py export worker_us_01 /backup/worker_us_01_bundle.json
```

---

## 🐳 Docker Fleet Deployment

Run isolated, resource-governed worker nodes in seconds:

```bash
cd deploy
docker compose up -d
```

Inspect worker status and CDP ports:
- Worker 01: `http://localhost:9222/json/version`
- Worker 02: `http://localhost:9223/json/version`

Each worker operates under strict cgroup limits (768MB RAM, 1 CPU core), allowing dozens of parallel sandboxes per cloud host.

---

## 🔄 Synergy with Windows PC Sandbox

| Dimension | Windows PC Sandbox (Master) | Linux PC Sandbox (Worker) |
| :--- | :--- | :--- |
| **Primary Role** | Account Genesis, Registration, 2FA, Human-in-the-Loop | Session Keep-alive, Warm-up, High-Throughput Scrape |
| **GPU Subsystem** | Native Direct3D 11/12 ANGLE Hardware Shaders | Synthesized Discrete GPU Profile (Mesa Cloaked) |
| **Credentials** | Encrypted Windows DPAPI Vault + RFC 6238 TOTP | StateBridge Ingested Session Storage & Cookies |
| **Display Mode** | Physical High-DPI Desktop Multi-Window | Xvfb Virtual Framebuffer / Headless Mode |
| **Footprint** | Full Desktop Environment | Containerized (768MB RAM / 1 Core) |
| **Scaling** | Low (Assisted Human-Scale) | Massive (100+ Cloud Containers) |

---

## 📄 License

MIT License. Designed and engineered for high-concurrency browser automation and anti-detect research.
