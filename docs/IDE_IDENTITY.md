# NexIDE Application Identity: from a Python icon to a real, independent app

## Where this landed

NexIDE was rebuilt from a Tkinter desktop GUI into a **local HTML/CSS/JS
web app**, served by a small Python backend
(`ide/web/server.py` + `ide/web/launcher.py`). The old Tkinter code is
preserved (not deleted) under `ide/legacy_tkinter/` for reference. This
document explains why, and exactly what problem each stage solved.

## Stage 0 (original problem): Tkinter + no branding at all

NexIDE was built with **Tkinter**, the GUI toolkit bundled with Python.
Running `nex ide` created a `tk.Tk()` window owned by the running
`python.exe`/`pythonw.exe` process, and nothing in the code ever set a
window icon or a Windows "Application User Model ID" (the identifier
Windows actually uses to decide how to group/label a taskbar button).
Every unbranded Tk/Python GUI defaults to sharing python.exe's identity,
so the taskbar showed Python's icon.

## Stage 1 (first patch): icon + AppUserModelID on the Tkinter window

A real NexIDE icon was added (`ide/assets/nexide.ico`/`.png`, built from
the X-mark logo) and wired in via `ide/legacy_tkinter/identity.py`:
`iconbitmap`/`iconphoto` for the window icon, and
`SetCurrentProcessExplicitAppUserModelID` (Windows-only) for taskbar
grouping. This was a real, working fix for the *visible* identity - but
it left the fundamental issue untouched: NexIDE was still, underneath,
a Python process, and every "Run" click spawned a second `python.exe`.

## Stage 2 (this change): stop being a Python GUI at all

Rather than continuing to patch a Tkinter window's identity, NexIDE was
rebuilt as a **browser-based application**:

```
NexIDE (HTML/CSS/JS, in a browser window)
        │  fetch() / EventSource (Server-Sent Events)
        ▼
ide/web/server.py  (Python, localhost-only HTTP server)
        │  same functions the CLI/REPL already use - no second interpreter
        ▼
compiler.api (lexer/parser/interpreter) + ide/runner.py (subprocess execution)
```

This solves the identity problem structurally instead of cosmetically:

- The **window itself belongs to the browser process** (Chrome/Edge),
  not to Python. `ide/web/launcher.py` opens it with `--app=<url>`, a
  Chromium flag that removes the address bar/tabs so it looks and feels
  like a standalone desktop app.
- The **favicon becomes the window/taskbar icon** because that's how
  Chromium app-mode windows work - no `iconbitmap()`/AppUserModelID
  hacks needed for this part.
- For a **permanent, fully independent** icon (a real Start-Menu/taskbar
  entry that isn't "Chrome" or "Python" at all), the page ships a Web
  App Manifest (`ide/web/static/manifest.json`) and a minimal service
  worker (`ide/web/static/sw.js`), so Chrome/Edge can install NexIDE as
  a standalone PWA via the in-app "Install NexIDE" button. Once
  installed, Windows treats it as a genuinely separate application with
  its own icon - this is the most robust fix available without writing
  a native (non-Python, non-browser) shell, and it's a one-time,
  user-driven action (browsers require a user gesture to install).

## What this does NOT change (be precise about this)

- **The backend is still Python.** `ide/web/server.py` runs as a
  `python.exe`/`pythonw.exe` process in the background, and
  `ide/runner.py` still spawns a *second* `python.exe` subprocess to
  actually run the user's NexLang program (unchanged from before -
  this was already true under Tkinter). `Task Manager` will still show
  these Python processes; only the **window the user interacts with**
  has stopped being a Python-owned window.
- **No new NexLang implementation was written.** The web server calls
  `compiler.api.check_source`, `ide.highlight.compute_spans`,
  `compiler.indent`, and `ide.runner.run_file` - the exact same,
  already-tested modules the Tkinter IDE called. There is still exactly
  one lexer/parser/interpreter.
- Self-hosting, a bytecode VM, and removing the Python dependency
  entirely are separate, much larger efforts - see
  `docs/ROADMAP.md`/`docs/PROJECT_STATUS.md`. This change only touches
  the IDE's presentation layer.

## What could not be verified in this sandbox

This sandbox has **no `tkinter` module and no display/browser**
installed, so:
- The old Tkinter GUI's tests (`tests/ide/test_app_gui.py`) already
  skipped themselves here before this change, and were removed as part
  of retiring that GUI (the underlying Tkinter code itself is kept in
  `ide/legacy_tkinter/`, not deleted).
- The new web IDE's **backend** (`ide/web/server.py`) is fully tested
  headlessly via real HTTP requests - `tests/ide/test_web_server.py`
  covers file I/O, syntax highlighting, smart indent, syntax checking,
  and a full run/output/input/exit lifecycle over Server-Sent Events
  (304/304 tests pass; see `docs/PROJECT_STATUS.md`).
- The **frontend** (`ide/web/static/*.html/css/js`) and the **app-mode
  browser window / PWA install flow** could not be visually verified -
  there is no browser to render them in this environment. Please check
  on your own machine that:
  1. `nex ide` opens a clean, chromeless window (not a normal browser
     tab with an address bar).
  2. Its taskbar icon is the NexIDE logo, not Chrome's or Python's.
  3. The "Install NexIDE" button appears and, after clicking it and
     confirming, creates a separate Start-Menu/taskbar entry that
     persists across launches.

If any of these don't hold, tell me exactly what you see (including
your browser and Windows version) so we can fix it against the real
behavior rather than guesswork.

