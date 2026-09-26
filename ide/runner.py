"""
NexLang IDE - program execution controller
============================================

The IDE never re-implements the interpreter. Running a program means
spawning the *real* NexLang CLI (`python -m cli.main run <file>`) as a
subprocess and streaming its stdout/stderr back into the Output panel,
forwarding whatever the user types in the Input panel to the process's
stdin. That's it - see PART 5/6 of the project brief ("do not create a
second fake interpreter", "the editor is only editing source code, the
program executes only when the user presses RUN").

This module has no Tkinter dependency, so its process-management logic
can be exercised directly in tests (see tests/ide/test_runner.py)
without a display.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from typing import Callable, Optional

# The repository root (parent of this `ide` package) so the subprocess's
# `python -m cli.main` can find the `cli`/`compiler` packages regardless
# of the IDE's own current working directory.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class RunHandle:
    """A running (or finished) program, plus the callbacks that deliver
    its output back to whoever started it."""
    process: subprocess.Popen
    _reader_thread: threading.Thread

    def is_running(self) -> bool:
        return self.process.poll() is None

    def send_input(self, text: str) -> None:
        """Forward one line of user input (from the IDE's Input panel) to
        the running program's stdin, e.g. in response to `ASK`."""
        if not self.is_running() or self.process.stdin is None:
            return
        try:
            self.process.stdin.write(text + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def stop(self) -> None:
        """Terminate the program immediately (the IDE's Stop button)."""
        if self.is_running():
            try:
                self.process.terminate()
            except OSError:
                pass


def run_file(
    path: str,
    on_output: Callable[[str], None],
    on_finished: Callable[[int], None],
) -> RunHandle:
    """Start `path` (a saved .nex file) running in a subprocess.

    `on_output(text)` is called (from a background thread - the caller
    must marshal it to wherever it needs to go, e.g. an SSE queue in the
    web IDE) for every chunk of combined stdout+stderr text produced.

    `on_finished(returncode)` is called once the process exits.
    """
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        [sys.executable, "-m", "cli.main", "run", path],
        cwd=_REPO_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )

    def _pump():
        try:
            stream = process.stdout
            if stream is None:
                return
            # Read char-by-char (not readline()) so a prompt printed
            # without a trailing newline - e.g. `ASK "..."` - reaches the
            # Output panel immediately instead of waiting for the next
            # newline (which may not come until after the user replies).
            while True:
                ch = stream.read(1)
                if ch == "":
                    break
                on_output(ch)
        finally:
            process.wait()
            on_finished(process.returncode)

    thread = threading.Thread(target=_pump, daemon=True)
    handle = RunHandle(process=process, _reader_thread=thread)
    thread.start()
    return handle


def check_file(path: str) -> Optional[str]:
    """Run `nex check` synchronously and return an error message string,
    or None if the file has no syntax errors. Used by the IDE for
    inline error highlighting on Save (see PART 7)."""
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "check", path],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return None
    return result.stderr or result.stdout
