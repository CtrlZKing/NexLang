"""
NexIDE web server
===================

Backend for the browser-based NexIDE (replaces the old Tkinter GUI -
see docs/IDE_IDENTITY.md for why). This process is the ONLY thing that
touches the filesystem or spawns NexLang programs; the frontend
(ide/web/static/*.html/css/js) is a plain browser page that talks to
it over HTTP + Server-Sent Events. There is still exactly one NexLang
implementation - this server calls the same `compiler.api` functions
and the same `ide/runner.py` subprocess runner the old Tkinter IDE
used; it does not re-implement the language.

Endpoints
---------
GET  /                          -> static/index.html
GET  /static/<path>              -> static assets (css/js/icons)
GET  /manifest.json, /sw.js, /favicon.ico
GET  /api/browse?path=DIR        -> list a server-side directory (Explorer / Open / Save-As)
GET  /api/file?path=FILE          -> read a file's content
POST /api/file                    -> {path, content} write a file
POST /api/highlight                -> {source} -> real-lexer syntax-highlight spans
POST /api/indent                   -> {source} -> smart-indent suggestion for the next line
POST /api/check                     -> {source, filename} -> real-parser syntax check
POST /api/run/start                  -> {path} -> {run_id}; starts the program as a subprocess
GET  /api/run/stream?run_id=ID        -> Server-Sent Events: output chunks, then `exit`
POST /api/run/input                    -> {run_id, text} -> forwarded to the program's stdin
POST /api/run/stop                      -> {run_id} -> terminates the program

Everything binds to 127.0.0.1 only - this server is not meant to be
reachable from the network, only from the browser window NexIDE opens
on the same machine.
"""

from __future__ import annotations

import json
import mimetypes
import os
import queue
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from compiler.api import check_source
from compiler.errors.errors import NexError
from compiler import indent as indent_engine
from ide.highlight import compute_spans
from ide.runner import run_file, RunHandle

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


class RunManager:
    """Tracks in-flight `nex run` subprocesses started from the browser,
    keyed by an opaque run_id the frontend uses for streaming/input/stop."""

    def __init__(self):
        self._runs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def start(self, path: str) -> str:
        run_id = uuid.uuid4().hex
        q: "queue.Queue" = queue.Queue()

        def on_output(text: str):
            q.put(("data", text))

        def on_finished(code: int):
            q.put(("exit", str(code)))

        handle = run_file(path, on_output=on_output, on_finished=on_finished)
        with self._lock:
            self._runs[run_id] = {"handle": handle, "queue": q}
        return run_id

    def get(self, run_id: str):
        with self._lock:
            return self._runs.get(run_id)

    def stop(self, run_id: str):
        entry = self.get(run_id)
        if entry:
            entry["handle"].stop()

    def send_input(self, run_id: str, text: str):
        entry = self.get(run_id)
        if entry:
            entry["handle"].send_input(text)

    def cleanup(self, run_id: str):
        with self._lock:
            self._runs.pop(run_id, None)


RUNS = RunManager()

# Project root the file explorer / open / save dialogs start from. Set
# once at startup by `ide/web/launcher.py`; can move around as the user
# browses (the frontend always sends explicit paths back).
STATE = {"project_dir": os.getcwd()}


def _json_bytes(obj) -> bytes:
    return json.dumps(obj).encode("utf-8")


def _safe_static_path(rel: str) -> str | None:
    rel = rel.lstrip("/")
    full = os.path.normpath(os.path.join(STATIC_DIR, rel))
    if not full.startswith(os.path.normpath(STATIC_DIR)):
        return None
    return full


class Handler(BaseHTTPRequestHandler):
    server_version = "NexIDE/1.0"

    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet; errors still raise/are caught below

    # ---- helpers --------------------------------------------------------
    def _send_json(self, obj, status=200):
        body = _json_bytes(obj)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: str, content_type: str = None):
        if not os.path.isfile(path):
            self._send_json({"error": f"not found: {path}"}, 404)
            return
        ctype = content_type or mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    # ---- routing --------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        try:
            if path == "/":
                self._send_file(os.path.join(STATIC_DIR, "index.html"), "text/html")
            elif path == "/manifest.json":
                self._send_file(os.path.join(STATIC_DIR, "manifest.json"), "application/manifest+json")
            elif path == "/sw.js":
                self._send_file(os.path.join(STATIC_DIR, "sw.js"), "application/javascript")
            elif path == "/favicon.ico":
                self._send_file(os.path.join(ASSETS_DIR, "nexide.ico"), "image/x-icon")
            elif path.startswith("/static/"):
                full = _safe_static_path(path[len("/static/"):])
                if full is None:
                    self._send_json({"error": "forbidden"}, 403)
                else:
                    self._send_file(full)
            elif path == "/api/browse":
                self._api_browse(params.get("path") or STATE["project_dir"])
            elif path == "/api/file":
                self._api_read_file(params.get("path", ""))
            elif path == "/api/run/stream":
                self._api_run_stream(params.get("run_id", ""))
            else:
                self._send_json({"error": "not found"}, 404)
        except BrokenPipeError:
            pass
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self._read_json_body()
            if path == "/api/file":
                self._api_write_file(body)
            elif path == "/api/highlight":
                self._api_highlight(body)
            elif path == "/api/indent":
                self._api_indent(body)
            elif path == "/api/check":
                self._api_check(body)
            elif path == "/api/run/start":
                self._api_run_start(body)
            elif path == "/api/run/input":
                self._api_run_input(body)
            elif path == "/api/run/stop":
                self._api_run_stop(body)
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    # ---- filesystem / explorer -------------------------------------------
    def _api_browse(self, dir_path: str):
        dir_path = os.path.abspath(dir_path)
        if not os.path.isdir(dir_path):
            dir_path = STATE["project_dir"]
        STATE["project_dir"] = dir_path
        entries = []
        try:
            for name in sorted(os.listdir(dir_path)):
                full = os.path.join(dir_path, name)
                is_dir = os.path.isdir(full)
                if is_dir or name.endswith(".nex"):
                    entries.append({"name": name, "is_dir": is_dir})
        except OSError as e:
            self._send_json({"error": str(e)}, 400)
            return
        parent = os.path.dirname(dir_path) if dir_path != os.path.dirname(dir_path) else None
        self._send_json({"path": dir_path, "parent": parent, "entries": entries})

    def _api_read_file(self, path: str):
        if not path or not os.path.isfile(path):
            self._send_json({"error": f"file not found: {path}"}, 404)
            return
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self._send_json({"path": path, "content": content})

    def _api_write_file(self, body: dict):
        path = body.get("path")
        content = body.get("content", "")
        if not path:
            self._send_json({"error": "missing path"}, 400)
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            self._send_json({"error": str(e)}, 400)
            return
        self._send_json({"ok": True, "path": os.path.abspath(path)})

    # ---- language services (real lexer/parser, no re-implementation) -----
    def _api_highlight(self, body: dict):
        source = body.get("source", "")
        spans = compute_spans(source)
        self._send_json({
            "spans": [{"line": s.line, "col": s.col, "length": s.length, "tag": s.tag} for s in spans]
        })

    def _api_indent(self, body: dict):
        source = body.get("source", "")
        state = indent_engine.IndentState()
        for line in source.splitlines():
            state.feed(line)
        self._send_json({"indent": state.indent_for_next_line()})

    def _api_check(self, body: dict):
        source = body.get("source", "")
        filename = body.get("filename", "<ide>")
        try:
            check_source(source, filename)
            self._send_json({"ok": True})
        except NexError as e:
            loc = e.location
            self._send_json({
                "ok": False,
                "code": e.code,
                "title": e.title,
                "explanation": e.explanation,
                "suggestions": e.suggestions,
                "line": loc.line if loc else None,
                "column": loc.column if loc else None,
                "length": loc.length if loc else 1,
                "source_line": e.source_line,
                "rendered": e.render(use_color=False),
            })

    # ---- run / stop / input (real subprocess, streamed via SSE) ----------
    def _api_run_start(self, body: dict):
        path = body.get("path")
        if not path or not os.path.isfile(path):
            self._send_json({"error": f"file not found: {path}"}, 404)
            return
        run_id = RUNS.start(path)
        self._send_json({"run_id": run_id})

    def _api_run_stream(self, run_id: str):
        entry = RUNS.get(run_id)
        if entry is None:
            self._send_json({"error": "unknown run_id"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = entry["queue"]
        try:
            while True:
                try:
                    kind, payload = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue
                if kind == "data":
                    data = json.dumps(payload)
                    self.wfile.write(f"event: output\ndata: {data}\n\n".encode("utf-8"))
                else:  # exit
                    self.wfile.write(f"event: exit\ndata: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    break
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            RUNS.cleanup(run_id)

    def _api_run_input(self, body: dict):
        RUNS.send_input(body.get("run_id", ""), body.get("text", ""))
        self._send_json({"ok": True})

    def _api_run_stop(self, body: dict):
        RUNS.stop(body.get("run_id", ""))
        self._send_json({"ok": True})


def create_server(host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    """port=0 lets the OS pick a free port; read it back via server.server_port."""
    return ThreadingHTTPServer((host, port), Handler)
