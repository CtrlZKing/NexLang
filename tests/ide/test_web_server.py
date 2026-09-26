"""
Tests for ide/web/server.py - the backend behind the browser-based
NexIDE. These exercise the real HTTP API (no Tkinter/browser needed),
replacing tests/ide/test_app_gui.py which tested the old Tkinter GUI
directly (see docs/IDE_IDENTITY.md for why NexIDE moved to HTML/CSS/JS).
"""
import http.client
import json
import os
import threading
import time

import pytest

from ide.web.server import create_server, STATE


@pytest.fixture
def server(tmp_path):
    STATE["project_dir"] = str(tmp_path)
    srv = create_server()
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    yield srv
    srv.shutdown()


def _get(server, path):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    conn.request("GET", path)
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    return resp.status, body


def _post(server, path, obj):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    data = json.dumps(obj).encode("utf-8")
    conn.request("POST", path, body=data, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    return resp.status, json.loads(body)


def test_index_page_served(server):
    status, body = _get(server, "/")
    assert status == 200
    assert b"NexIDE" in body


def test_manifest_served_and_valid_json(server):
    status, body = _get(server, "/manifest.json")
    assert status == 200
    data = json.loads(body)
    assert data["name"] == "NexIDE"
    assert len(data["icons"]) >= 2


def test_static_assets_served(server):
    status, body = _get(server, "/static/style.css")
    assert status == 200
    assert len(body) > 100
    status, body = _get(server, "/static/app.js")
    assert status == 200
    assert len(body) > 100


def test_static_path_traversal_blocked(server):
    status, body = _get(server, "/static/../../server.py")
    assert status in (403, 404)


def test_favicon_served(server):
    status, body = _get(server, "/favicon.ico")
    assert status == 200
    assert len(body) > 0


def test_browse_lists_nex_files_and_dirs(server, tmp_path):
    (tmp_path / "hello.nex").write_text('SAY "hi"\n')
    (tmp_path / "notes.txt").write_text("not nex")
    (tmp_path / "subdir").mkdir()
    status, data = _post(server, "/api/browse", {})  # unused, GET-only endpoint check below
    # /api/browse is a GET endpoint
    status, body = _get(server, f"/api/browse?path={tmp_path}")
    data = json.loads(body)
    names = {e["name"] for e in data["entries"]}
    assert "hello.nex" in names
    assert "subdir" in names
    assert "notes.txt" not in names  # non-.nex files are filtered out


def test_file_write_then_read(server, tmp_path):
    target = str(tmp_path / "prog.nex")
    status, result = _post(server, "/api/file", {"path": target, "content": 'SAY "x"\n'})
    assert status == 200
    assert result["ok"] is True

    status, body = _get(server, f"/api/file?path={target}")
    data = json.loads(body)
    assert data["content"] == 'SAY "x"\n'


def test_read_missing_file_returns_404(server, tmp_path):
    status, body = _get(server, f"/api/file?path={tmp_path}/does_not_exist.nex")
    assert status == 404


def test_highlight_endpoint_returns_spans(server):
    status, data = _post(server, "/api/highlight", {"source": 'SET x TO 10\nSAY "hi"\n'})
    assert status == 200
    tags = {s["tag"] for s in data["spans"]}
    assert "keyword" in tags
    assert "string" in tags
    assert "number" in tags


def test_indent_endpoint_reuses_real_indent_engine(server):
    status, data = _post(server, "/api/indent", {"source": "IF x IS 10 THEN"})
    assert data["indent"] == "    "
    status, data = _post(server, "/api/indent", {"source": "SET x TO 10"})
    assert data["indent"] == ""


def test_check_endpoint_valid_program(server):
    status, data = _post(server, "/api/check", {"source": 'SAY "hi"\n', "filename": "t.nex"})
    assert data["ok"] is True


def test_check_endpoint_reports_structured_error(server):
    status, data = _post(server, "/api/check", {"source": "IF x IS 10 THEN\nSAY 1\n", "filename": "t.nex"})
    assert data["ok"] is False
    assert data["code"]
    assert data["line"] is not None


def _read_sse_events(resp, deadline):
    """Read Server-Sent Events from `resp` until `deadline` (a time.time()
    value), yielding (event_name, data_string) pairs. This parses the SSE
    framing properly (unlike a raw byte/substring scan), matching what a
    real browser's EventSource does."""
    buf = ""
    event_name = "message"
    while time.time() < deadline:
        chunk = resp.read(1)
        if not chunk:
            break
        buf += chunk.decode(errors="replace")
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            line = line.rstrip("\r")
            if line == "":
                continue  # blank line = event boundary; we yield per-field instead
            if line.startswith("event:"):
                event_name = line[len("event:"):].strip()
            elif line.startswith("data:"):
                yield event_name, line[len("data:"):].strip()
                event_name = "message"


def test_run_lifecycle_output_input_exit(server, tmp_path):
    prog = tmp_path / "interactive.nex"
    prog.write_text('SAY "before"\nASK "name?" INTO n\nSAY "hello " + n\n')

    status, data = _post(server, "/api/run/start", {"path": str(prog)})
    assert status == 200
    run_id = data["run_id"]

    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
    conn.request("GET", f"/api/run/stream?run_id={run_id}")
    resp = conn.getresponse()

    produced = []
    sent = False
    exited = False
    deadline = time.time() + 8
    for event_name, data_str in _read_sse_events(resp, deadline):
        if event_name == "output":
            produced.append(json.loads(data_str))
            joined = "".join(produced)
            if "before" in joined and not sent:
                _post(server, "/api/run/input", {"run_id": run_id, "text": "World"})
                sent = True
        elif event_name == "exit":
            exited = True
            break
    conn.close()

    full_output = "".join(produced)
    assert "before" in full_output
    assert "hello World" in full_output
    assert exited


def test_run_missing_file_errors(server):
    status, data = _post(server, "/api/run/start", {"path": "/no/such/file.nex"})
    assert status == 404


def test_stop_unknown_run_id_does_not_crash(server):
    status, data = _post(server, "/api/run/stop", {"run_id": "does-not-exist"})
    assert status == 200
    assert data["ok"] is True


def test_stop_running_process(server, tmp_path):
    prog = tmp_path / "loop.nex"
    prog.write_text("REPEAT 999999999 TIMES\n    SAY \"tick\"\nEND\n")
    status, data = _post(server, "/api/run/start", {"path": str(prog)})
    run_id = data["run_id"]
    time.sleep(0.2)
    status, data = _post(server, "/api/run/stop", {"run_id": run_id})
    assert data["ok"] is True
