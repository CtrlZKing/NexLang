import io
import os
import pytest
from compiler.api import run_source
from compiler.errors.errors import NexError
from compiler.interpreter.interpreter import Interpreter
from compiler.parser.parser import Parser
from compiler.lexer.lexer import tokenize


def run_in_dir(src, base_dir):
    out = io.StringIO()
    tokens = tokenize(src, "<test>")
    program = Parser(tokens, src, "<test>").parse_program()
    interp = Interpreter(source=src, filename=os.path.join(base_dir, "script.nex"), output=out)
    interp.run(program)
    return out.getvalue()


def test_write_and_read_file(tmp_path):
    src = (
        'WRITE "hello file" TO FILE "out.txt"\n'
        'SET content TO READ FILE "out.txt"\n'
        "SAY content\n"
    )
    out = run_in_dir(src, str(tmp_path))
    assert out == "hello file\n"
    assert (tmp_path / "out.txt").read_text() == "hello file"


def test_write_overwrites_existing_content(tmp_path):
    src = (
        'WRITE "first" TO FILE "out.txt"\n'
        'WRITE "second" TO FILE "out.txt"\n'
        'SAY READ FILE "out.txt"\n'
    )
    out = run_in_dir(src, str(tmp_path))
    assert out == "second\n"


def test_append_to_file(tmp_path):
    src = (
        'WRITE "a" TO FILE "out.txt"\n'
        'APPEND "b" TO FILE "out.txt"\n'
        'SAY READ FILE "out.txt"\n'
    )
    out = run_in_dir(src, str(tmp_path))
    assert out == "ab\n"


def test_file_exists_true_and_false(tmp_path):
    (tmp_path / "present.txt").write_text("x")
    src = (
        'IF FILE "present.txt" EXISTS THEN\n    SAY "yes"\nEND\n'
        'IF FILE "absent.txt" EXISTS THEN\n    SAY "yes"\nOTHERWISE\n    SAY "no"\nEND\n'
    )
    out = run_in_dir(src, str(tmp_path))
    assert out == "yes\nno\n"


def test_delete_file(tmp_path):
    (tmp_path / "temp.txt").write_text("x")
    src = 'DELETE FILE "temp.txt"\nIF FILE "temp.txt" EXISTS THEN\n    SAY "yes"\nOTHERWISE\n    SAY "no"\nEND\n'
    out = run_in_dir(src, str(tmp_path))
    assert out == "no\n"
    assert not (tmp_path / "temp.txt").exists()


def test_delete_missing_file_is_clear_error(tmp_path):
    with pytest.raises(NexError) as exc_info:
        run_in_dir('DELETE FILE "nope.txt"\n', str(tmp_path))
    assert exc_info.value.code == "NX220"


def test_reading_missing_file_is_clear_error(tmp_path):
    with pytest.raises(NexError) as exc_info:
        run_in_dir('SAY READ FILE "nope.txt"\n', str(tmp_path))
    assert exc_info.value.code == "NX223"


def test_file_errors_can_be_caught(tmp_path):
    src = 'TRY\n    SAY READ FILE "nope.txt"\nCATCH err\n    SAY "caught"\nEND\n'
    out = run_in_dir(src, str(tmp_path))
    assert out == "caught\n"
