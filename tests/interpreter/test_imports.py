import io
import os
import pytest
from compiler.errors.errors import NexError
from compiler.interpreter.interpreter import Interpreter
from compiler.parser.parser import Parser
from compiler.lexer.lexer import tokenize


def run_file(main_path):
    with open(main_path, "r", encoding="utf-8") as f:
        src = f.read()
    out = io.StringIO()
    tokens = tokenize(src, main_path)
    program = Parser(tokens, src, main_path).parse_program()
    interp = Interpreter(source=src, filename=main_path, output=out)
    interp.run(program)
    return out.getvalue()


def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return str(path)


def test_import_brings_in_function(tmp_path):
    write(tmp_path / "lib.nex", "FUNCTION doubled(x)\n    RETURN x * 2\nEND\n")
    main = write(tmp_path / "main.nex", 'IMPORT "lib.nex"\nSAY doubled(21)\n')
    assert run_file(main) == "42\n"


def test_import_brings_in_top_level_variables(tmp_path):
    write(tmp_path / "lib.nex", "SET shared_value TO 99\n")
    main = write(tmp_path / "main.nex", 'IMPORT "lib.nex"\nSAY shared_value\n')
    assert run_file(main) == "99\n"


def test_import_missing_file_is_clear_error(tmp_path):
    main = write(tmp_path / "main.nex", 'IMPORT "does_not_exist.nex"\n')
    with pytest.raises(NexError) as exc_info:
        run_file(main)
    assert exc_info.value.code == "NX217"


def test_import_non_text_path_is_clear_error(tmp_path):
    main = write(tmp_path / "main.nex", "IMPORT 5\n")
    with pytest.raises(NexError) as exc_info:
        run_file(main)
    assert exc_info.value.code == "NX204"


def test_double_import_does_not_redefine_or_error(tmp_path):
    write(tmp_path / "lib.nex", "FUNCTION doubled(x)\n    RETURN x * 2\nEND\n")
    main = write(
        tmp_path / "main.nex",
        'IMPORT "lib.nex"\nIMPORT "lib.nex"\nSAY doubled(5)\n',
    )
    assert run_file(main) == "10\n"


def test_imported_function_can_call_another_imported_function(tmp_path):
    write(
        tmp_path / "lib.nex",
        "FUNCTION helper(x)\n    RETURN x + 1\nEND\n"
        "FUNCTION doubled_helper(x)\n    RETURN helper(x) * 2\nEND\n",
    )
    main = write(tmp_path / "main.nex", 'IMPORT "lib.nex"\nSAY doubled_helper(4)\n')
    assert run_file(main) == "10\n"
