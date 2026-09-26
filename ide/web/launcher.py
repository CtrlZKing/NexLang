"""
NexIDE launcher
==================

Starts the local NexIDE web server (ide/web/server.py) and opens it in
a browser window. See docs/IDE_IDENTITY.md for the full story, but in
short: this is what makes NexIDE stop looking like "a Python program"
at all, rather than just changing an icon on a Tkinter window.

Two ways the window can appear, tried in order:

1. **App-mode window** (preferred): if Chrome, Edge, or another
   Chromium-based browser is on PATH, launch it with `--app=<url>`.
   That opens a window with no address bar/tabs - it looks and behaves
   like a standalone desktop app, and the OS taskbar shows *our*
   favicon (from ide/web/static/icons/), not python.exe's icon, because
   the window belongs to the browser process, not Python.
2. **Plain browser tab** (fallback): if no Chromium browser is found,
   `webbrowser.open()` is used instead - NexIDE still works, but shows
   inside a normal browser tab with that browser's own UI/icon.

For a permanent fix (a real, separate taskbar/Start-Menu icon that
persists across launches, independent of both Python and the browser),
see the "Install NexIDE" button inside the app itself - it uses the
page's Web App Manifest (ide/web/static/manifest.json) so Chrome/Edge
can install NexIDE as a standalone PWA. That is a one-time, user-driven
action (browsers require a user gesture to install an app) - this
launcher cannot do it silently on the user's behalf.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import webbrowser

from ide.web.server import create_server, STATE

# Executable names to look for, in preference order, per platform.
_CHROMIUM_CANDIDATES = {
    "win32": ["msedge.exe", "chrome.exe", "brave.exe"],
    "darwin": ["Google Chrome", "Microsoft Edge"],  # resolved via `open -a` instead of PATH
    "linux": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
              "microsoft-edge", "microsoft-edge-stable", "brave-browser"],
}


def _find_chromium_windows_mac() -> str | None:
    """On Windows, common browsers usually aren't on PATH even when
    installed - check the well-known install locations too."""
    if sys.platform != "win32":
        return None
    program_files = [os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                      os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                      os.environ.get("LOCALAPPDATA", "")]
    relative_paths = [
        r"Microsoft\Edge\Application\msedge.exe",
        r"Google\Chrome\Application\chrome.exe",
        r"BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
    for base in program_files:
        if not base:
            continue
        for rel in relative_paths:
            candidate = os.path.join(base, rel)
            if os.path.isfile(candidate):
                return candidate
    return None


def find_browser_executable() -> str | None:
    plat = sys.platform
    if plat == "win32":
        found = _find_chromium_windows_mac()
        if found:
            return found
        for name in _CHROMIUM_CANDIDATES["win32"]:
            path = shutil.which(name)
            if path:
                return path
        return None
    if plat == "darwin":
        for app_name in ["/Applications/Google Chrome.app", "/Applications/Microsoft Edge.app",
                          "/Applications/Brave Browser.app"]:
            if os.path.isdir(app_name):
                return app_name
        return None
    for name in _CHROMIUM_CANDIDATES.get("linux", []):
        path = shutil.which(name)
        if path:
            return path
    return None


def _launch_app_window(url: str, browser_path: str) -> "subprocess.Popen | None":
    """Launch a Chromium browser in --app mode with an isolated profile
    (so it doesn't merge into an already-open normal browser window,
    which would otherwise steal NexIDE's taskbar identity)."""
    profile_dir = os.path.join(tempfile.gettempdir(), "nexide-app-profile")
    os.makedirs(profile_dir, exist_ok=True)
    args = [
        browser_path,
        f"--app={url}",
        f"--user-data-dir={profile_dir}",
        "--window-size=1280,820",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if sys.platform == "darwin":
        # `browser_path` is a .app bundle here; use `open -na` to launch it
        # with arguments as a fresh instance.
        args = ["open", "-na", browser_path, "--args"] + args[1:]
    try:
        return subprocess.Popen(args)
    except OSError:
        return None


def launch_web_ide(initial_path: str = None) -> None:
    if initial_path and os.path.isfile(initial_path):
        STATE["project_dir"] = os.path.dirname(os.path.abspath(initial_path))

    server = create_server()
    port = server.server_port
    url = f"http://127.0.0.1:{port}/"
    if initial_path and os.path.isfile(initial_path):
        from urllib.parse import quote
        url += f"?open={quote(os.path.abspath(initial_path))}"

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print(f"NexIDE is running at {url}")
    print("(Close the NexIDE window, or press Ctrl+C here, to stop it.)")

    browser_path = find_browser_executable()
    app_process = _launch_app_window(url, browser_path) if browser_path else None

    if app_process is None:
        if browser_path is None:
            print("No Chrome/Edge/Chromium install found - opening in your default browser instead.")
            print("Install Chrome or Edge for a proper app-style window without browser tabs/toolbar.")
        webbrowser.open(url)
        try:
            server_thread.join()
        except KeyboardInterrupt:
            pass
        return

    try:
        app_process.wait()
    except KeyboardInterrupt:
        app_process.terminate()
    finally:
        server.shutdown()


if __name__ == "__main__":
    launch_web_ide(sys.argv[1] if len(sys.argv) > 1 else None)
