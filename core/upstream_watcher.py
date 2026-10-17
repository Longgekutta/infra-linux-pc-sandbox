from __future__ import annotations
"""
Upstream Watcher Module - Linux PC Sandbox (Long-term Self-Update Engine)
Monitors the upstream anti-detect projects (patchright / rebrowser-patches /
PIFork / tls-client / curl_cffi) for release and commit changes, diffs what is
new, and generates an absorption report: what changed, which of our modules it
affects, and whether it can be auto-absorbed into shared_knowledge.json.

Why this exists (the manual-maintenance problem):
  Camoufox rebases its C++ patches per Firefox release; CloakBrowser accumulates
  bypass knowledge in its community; tls-client adds Chrome profiles per release;
  PIFork updates its Canary fingerprint extraction. None of this knowledge is a
  copyable code file — it is a moving target. This module turns "watch upstream"
  into a periodic, diffable, automatable step so the sandbox self-updates.

Watch strategy (GitHub API, token optional):
  - commits?since=  -> new commits since last check (stored in watcher state)
  - releases/latest -> new version tags
  - contents diff   -> did driver_patches/*.ts, profiles/*.go, autopif4.sh change?
Auto-absorption:
  - tls-client new Chrome profile in profiles/internal_browser_profiles.go
    -> update tls_chrome_profiles_available in shared_knowledge.json
  - patchright new/changed driver_patches/*.ts -> flag for review (needs human
    judgment: it patches Playwright's TS source, ours is a CDP driver)
  - PIFork autopif4.sh change -> update mobile_pif_ecosystem insights
"""

import json
import os
import subprocess
import time
from typing import Dict, Any, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED_KNOWLEDGE = os.path.join(ROOT, "shared_knowledge.json")
WATCHER_STATE = os.path.join(ROOT, "data", "watcher_state.json")

DEFAULT_WATCH_TARGETS = [
    {"repo": "Kaliiiiiiiiii-Vinyzu/patchright", "paths": ["driver_patches/"], "auto_absorb": False},
    {"repo": "rebrowser/rebrowser-patches", "paths": ["patches/"], "auto_absorb": False},
    {"repo": "osm0sis/PlayIntegrityFork", "paths": ["module/autopif4.sh"], "auto_absorb": True,
     "absorb_key": "mobile_pif_ecosystem"},
    {"repo": "bogdanfinn/tls-client", "paths": ["profiles/"], "auto_absorb": True,
     "absorb_key": "tls_chrome_profiles_available"},
]


def _token() -> str:
    return os.environ.get("GITHUB_TOKEN", "")


def _gh(url: str, timeout: int = 20) -> Optional[Any]:
    cmd = ["curl", "-sL", "-m", str(timeout), "-H", "Accept: application/vnd.github+json"]
    tok = _token()
    if tok:
        cmd += ["-H", f"Authorization: token {tok}"]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def load_state() -> Dict[str, Any]:
    try:
        with open(WATCHER_STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(WATCHER_STATE), exist_ok=True)
    with open(WATCHER_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def check_repo(repo: str, since_iso: Optional[str] = None) -> Dict[str, Any]:
    """Check one upstream repo: latest release + commits since last check."""
    out: Dict[str, Any] = {"repo": repo}
    rel = _gh(f"https://api.github.com/repos/{repo}/releases/latest")
    if isinstance(rel, dict):
        latest = {
            "tag": rel.get("tag_name"),
            "published": rel.get("published_at"),
        }
        out["latest_release"] = latest
    commits_url = f"https://api.github.com/repos/{repo}/commits?per_page=5"
    if since_iso:
        commits_url += f"&since={since_iso}"
    commits = _gh(commits_url)
    if isinstance(commits, list):
        recent = []
        for c in commits:
            if not isinstance(c, dict):
                continue
            commit = c.get("commit") or {}
            author = commit.get("author") or {}
            recent.append({
                "sha": (c.get("sha") or "")[:8],
                "message": (commit.get("message") or "")[:80],
                "date": author.get("date"),
            })
        out["recent_commits"] = recent
    return out


def _extract_chrome_profiles_from_tls_client() -> List[str]:
    """Parse tls-client profiles/internal_browser_profiles.go for Chrome profile names."""
    url = "https://raw.githubusercontent.com/bogdanfinn/tls-client/master/profiles/internal_browser_profiles.go"
    r = subprocess.run(["curl", "-sL", "-m", "20", url], capture_output=True, text=True, timeout=30)
    import re
    return sorted(set(re.findall(r"var (Chrome_\d+)", r.stdout)))


def run_watch(targets: Optional[List[Dict[str, Any]]] = None,
              auto_absorb: bool = True) -> Dict[str, Any]:
    """
    Run a full watch cycle over the upstream targets.
    Returns {"checked": [..], "changes": [..], "absorbed": [..], "review": [..]}.
    """
    state = load_state()
    targets = targets or DEFAULT_WATCH_TARGETS
    checked, changes, absorbed, review = [], [], [], []

    for t in targets:
        repo = t["repo"]
        repo_state = state.get(repo) or {}
        since = repo_state.get("last_commit_date")
        res = check_repo(repo, since_iso=since)
        checked.append(res)

        new_commits = res.get("recent_commits", [])
        if new_commits:
            changes.append({
                "repo": repo,
                "new_commits": len(new_commits),
                "latest": new_commits[0]["message"] if new_commits else None,
            })

        # auto-absorb tls-client Chrome profile list
        if auto_absorb and repo == "bogdanfinn/tls-client":
            profiles = _extract_chrome_profiles_from_tls_client()
            if profiles:
                shared = json.load(open(SHARED_KNOWLEDGE, encoding="utf-8"))
                current = set(shared.get("tls_chrome_profiles_available", []))
                new_profiles = [p for p in profiles if p not in current]
                if new_profiles:
                    shared["tls_chrome_profiles_available"] = sorted(current | set(profiles))
                    shared["_updated"] = time.strftime("%Y-%m-%d")
                    with open(SHARED_KNOWLEDGE, "w", encoding="utf-8") as f:
                        json.dump(shared, f, ensure_ascii=False, indent=2)
                    absorbed.append({"repo": repo, "new_profiles": new_profiles})
                else:
                    absorbed.append({"repo": repo, "new_profiles": []})

        # flag non-auto-absorbable changes for review
        if new_commits and not t.get("auto_absorb"):
            review.append({"repo": repo,
                           "reason": f"{len(new_commits)} new commits — needs human judgment "
                                     f"(patches Playwright TS source)"})

        # update state
        if new_commits:
            state[repo] = {"last_commit_date": new_commits[0]["date"]}
    save_state(state)

    return {"checked": checked, "changes": changes, "absorbed": absorbed, "review": review}


def status() -> Dict[str, Any]:
    state = load_state()
    return {
        "watching": [t["repo"] for t in DEFAULT_WATCH_TARGETS],
        "last_checked": {k: v.get("last_commit_date") for k, v in state.items()},
        "token_configured": bool(_token()),
    }
