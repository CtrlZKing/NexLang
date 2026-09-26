import os
import time

from ide.runner import run_file, check_file


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def _run_and_collect(path, inputs=None, timeout=5.0):
    inputs = list(inputs or [])
    outputs = []
    done = {}

    def on_output(text):
        outputs.append(text)

    def on_finished(code):
        done["code"] = code

    handle = run_file(path, on_output, on_finished)
    deadline = time.time() + timeout
    input_iter = iter(inputs)
    next_input = next(input_iter, None)

    while "code" not in done and time.time() < deadline:
        if next_input is not None:
            handle.send_input(next_input)
            next_input = next(input_iter, None)
        time.sleep(0.1)

    return "".join(outputs), done.get("code")


def test_run_hello_world(tmp_path):
    path = _write(tmp_path, "hello.nex", 'SAY "Hello, World!"\n')
    out, code = _run_and_collect(path)
    assert "Hello, World!" in out
    assert code == 0


def test_run_reports_runtime_error(tmp_path):
    path = _write(tmp_path, "bad.nex", "SAY undefined_var\n")
    out, code = _run_and_collect(path)
    assert "ERROR" in out
    assert code == 1


def test_ask_prompt_appears_before_input_is_sent(tmp_path):
    path = _write(tmp_path, "ask.nex",
                  'ASK "WHAT IS YOUR NAME?" INTO name\nSAY "Hi {name}"\n')
    outputs = []
    done = {}
    handle = run_file(path, outputs.append, lambda c: done.setdefault("code", c))
    # Give the prompt a moment to arrive before we answer it.
    deadline = time.time() + 5
    while "WHAT IS YOUR NAME?" not in "".join(outputs) and time.time() < deadline:
        time.sleep(0.05)
    assert "WHAT IS YOUR NAME?" in "".join(outputs), "prompt should stream before input is sent"
    handle.send_input("Aditya")
    deadline = time.time() + 3
    while "code" not in done and time.time() < deadline:
        time.sleep(0.05)
    assert "Hi Aditya" in "".join(outputs)


def test_stop_terminates_running_program(tmp_path):
    path = _write(tmp_path, "loop.nex", "REPEAT UNTIL 1 IS 2\n    SAY \"loop\"\nEND\n")
    done = {}
    handle = run_file(path, lambda t: None, lambda c: done.setdefault("code", c))
    time.sleep(0.3)
    assert handle.is_running()
    handle.stop()
    deadline = time.time() + 3
    while handle.is_running() and time.time() < deadline:
        time.sleep(0.05)
    assert not handle.is_running()


def test_check_file_valid(tmp_path):
    path = _write(tmp_path, "ok.nex", 'SAY "ok"\n')
    assert check_file(path) is None


def test_check_file_invalid_reports_missing_end(tmp_path):
    path = _write(tmp_path, "bad.nex", "IF 1 IS 1 THEN\n    SAY \"x\"\n")
    error = check_file(path)
    assert error is not None
    assert "END" in error
