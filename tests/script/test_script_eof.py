"""
Tests for PART 2 / PART 7 of the project brief: script mode is different
from interactive mode. A `.nex` file's last block closes itself with its
own `END`; there is no additional "submission END" required, and reaching
EOF with everything closed simply finishes the program. An EOF reached
while a block is still open must be a clear, located syntax error.
"""

import io
import pytest

from compiler.api import run_source, check_source
from compiler.errors.errors import NexError


def run(src):
    out = io.StringIO()
    run_source(src, filename="<test>", output=out)
    return out.getvalue()


def test_script_with_no_blocks_needs_no_end():
    assert run('SAY "Hello, World!"') == "Hello, World!\n"


def test_if_else_closing_end_is_sufficient_no_extra_end_needed():
    src = (
        'SET name TO "Aditya"\n'
        '\n'
        'SAY "Hello, {name}"\n'
        '\n'
        'IF name IS "Aditya" THEN\n'
        '    SAY "Welcome!"\n'
        'OTHERWISE\n'
        '    SAY "Hello!"\n'
        'END\n'
    )
    out = run(src)
    assert out == "Hello, Aditya\nWelcome!\n"


def test_nested_blocks_close_naturally_at_eof():
    src = (
        "IF 1 IS 1 THEN\n"
        "    IF 2 IS 2 THEN\n"
        '        SAY "both"\n'
        "    END\n"
        "END\n"
    )
    assert run(src) == "both\n"


def test_script_ending_without_final_newline_still_works():
    src = 'SAY "no trailing newline"'
    assert run(src) == "no trailing newline\n"


def test_unclosed_if_block_raises_clear_eof_error():
    src = "IF 1 IS 1 THEN\n    SAY \"yes\"\n"
    with pytest.raises(NexError) as exc_info:
        check_source(src, filename="unclosed.nex")
    err = exc_info.value
    assert err.code == "NX203"
    assert "END" in err.render()


def test_unclosed_while_block_raises_clear_eof_error():
    src = "WHILE 1 IS 1\n    SAY \"loop\"\n"
    with pytest.raises(NexError) as exc_info:
        check_source(src, filename="unclosed.nex")
    assert exc_info.value.code == "NX203"


def test_valid_script_has_no_syntax_errors():
    src = (
        "REPEAT 3 TIMES\n"
        '    SAY "hi"\n'
        "END\n"
    )
    check_source(src, filename="ok.nex")  # should not raise
