"""
Language-level tests: run the actual example programs in examples/ the way
a user would with `nex run`, and confirm they behave as documented.

`examples/errors.nex` is intentionally excluded from the "runs cleanly"
test below and instead has its own test confirming it raises the expected
diagnostic - it exists to demonstrate error output, not to run cleanly.
"""

import io
import os
import glob
import pytest

from compiler.api import run_source
from compiler.errors.errors import NexError

EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "examples")

CLEAN_EXAMPLES = [
    "hello.nex", "variables.nex", "conditions.nex", "loops.nex", "calculator.nex",
    "functions.nex", "collections.nex", "exceptions.nex", "files.nex",
    "maps_and_more.nex", "types.nex",
]


class Capture:
    def __init__(self):
        self.buf = io.StringIO()

    def write(self, text):
        self.buf.write(text)


@pytest.mark.parametrize("filename", CLEAN_EXAMPLES)
def test_example_runs_without_error(filename):
    path = os.path.join(EXAMPLES_DIR, filename)
    with open(path, encoding="utf-8") as f:
        source = f.read()
    out = Capture()
    run_source(source, filename=path, output=out)
    # every clean example should produce at least one line of output
    assert out.buf.getvalue().strip() != ""


def test_all_example_files_are_accounted_for():
    all_examples = {os.path.basename(p) for p in glob.glob(os.path.join(EXAMPLES_DIR, "*.nex"))}
    accounted_for = set(CLEAN_EXAMPLES) | {"errors.nex"}
    assert all_examples == accounted_for, (
        "A new example file was added but not registered in this test file "
        "(either add it to CLEAN_EXAMPLES or explain why it's excluded)."
    )


def test_errors_example_demonstrates_a_real_diagnostic():
    path = os.path.join(EXAMPLES_DIR, "errors.nex")
    with open(path, encoding="utf-8") as f:
        source = f.read()
    with pytest.raises(NexError) as exc_info:
        run_source(source, filename=path, output=Capture())
    assert exc_info.value.code == "NX204"


def test_hello_world_exact_output():
    path = os.path.join(EXAMPLES_DIR, "hello.nex")
    with open(path, encoding="utf-8") as f:
        source = f.read()
    out = Capture()
    run_source(source, filename=path, output=out)
    assert out.buf.getvalue() == "Hello, World!\n"
