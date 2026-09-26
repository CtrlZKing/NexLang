"""
NexIDE application identity
=============================

Everything needed to make NexIDE *look* like its own application
instead of a generic Python/Tk window - window icon, taskbar icon,
and (on Windows) decoupling NexIDE's taskbar grouping/icon from
python.exe's.

Why this file exists (see docs/IDE_IDENTITY.md for the full writeup):

Tkinter is a GUI toolkit bundled with Python. When you run a Tk app
with `python.exe`/`pythonw.exe`, three separate things decide what the
user sees, and all three have to be set independently or Windows falls
back to python.exe's own identity:

1. The window/title-bar icon      -> Tk's `iconphoto()` / `iconbitmap()`
2. The taskbar button's icon      -> normally inherited from #1, BUT
   Windows can still show the icon embedded in python.exe itself if a
   window has no icon of its own, or during the brief moment before
   the real icon is set.
3. The taskbar GROUPING identity  -> Windows groups/labels taskbar
   buttons by an internal "Application User Model ID" (AppUserModelID).
   If it's never set, every Tk/Python GUI app defaults to sharing
   python.exe's AppUserModelID, so Windows may show/group them as
   "Python" regardless of the window icon. This is set via
   `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID`
   and only applies on Windows.

Setting (1) and (3) together is the actual fix; setting only the
window icon is a common half-fix that still leaves the taskbar
grouping/identity as "Python" in some Windows versions/configurations.
"""

from __future__ import annotations

import os
import sys

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
ICON_PNG = os.path.join(ASSETS_DIR, "nexide.png")
ICON_ICO = os.path.join(ASSETS_DIR, "nexide.ico")

# Stable, unique identifier for NexIDE's Windows taskbar grouping.
# Must be unique per-application and stable across versions/updates -
# don't change this string casually once NexIDE has real users, since
# doing so resets any taskbar pins.
APP_USER_MODEL_ID = "NexLang.NexIDE.App"


def apply_identity(window) -> None:
    """Call once, right after creating the root Tk window, before it's
    shown. Sets the window/taskbar icon everywhere Tk can.

    NOTE: the AppUserModelID call (`ensure_windows_app_identity_set_early`)
    is deliberately NOT done here - it must run before Tk creates the
    window, not after, or Windows may have already associated the
    process with the default identity. Call that function first, then
    construct the Tk root, then call this function."""
    _set_window_icon(window)


def ensure_windows_app_identity_set_early() -> None:
    """Must be called BEFORE any Tk window (even a hidden root) is
    constructed - ideally the first line of `launch_ide()`. Windows
    decides a process's taskbar identity (AppUserModelID) at some point
    during its first window's creation; calling this after that point
    can be too late for the taskbar button to be grouped/labeled as
    NexIDE instead of Python. This is a no-op on non-Windows platforms."""
    _set_windows_app_user_model_id()


def _set_windows_app_user_model_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        # Best-effort: older Windows, restricted environments, or a
        # non-standard Python build. The window icon (below) still
        # gets set even if this fails.
        pass


def _set_window_icon(window) -> None:
    # .ico gives Windows a proper multi-resolution icon (16..256px) for
    # the title bar, taskbar, Alt+Tab, and any shortcut created from the
    # running window. iconbitmap(default=...) applies it to this window
    # AND any Toplevel windows it creates (dialogs, etc.).
    if sys.platform == "win32" and os.path.isfile(ICON_ICO):
        try:
            window.iconbitmap(default=ICON_ICO)
        except Exception:
            pass

    # iconphoto is the cross-platform mechanism (Linux window managers,
    # macOS dock via Tk, and a fallback on Windows too). Requires Tcl/Tk
    # 8.6+ for native PNG support, which is standard since Python 3.4.
    if os.path.isfile(ICON_PNG):
        try:
            import tkinter as tk
            icon_image = tk.PhotoImage(file=ICON_PNG)
            window.iconphoto(True, icon_image)
            # Keep a reference alive - Tk does not retain one itself and
            # the image can otherwise be garbage-collected.
            window._nexide_icon_ref = icon_image
        except Exception:
            pass
