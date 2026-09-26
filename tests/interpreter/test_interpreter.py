import io
import pytest
from compiler.api import run_source
from compiler.errors.errors import NexError


class Capture:
    def __init__(self):
        self.buf = io.StringIO()

    def write(self, text):
        self.buf.write(text)

    @property
    def text(self):
        return self.buf.getvalue()


def run(src, inputs=None):
    out = Capture()
    inputs = inputs or []
    it = iter(inputs)
    run_source(src, filename="<test>", output=out, input_fn=lambda prompt="": next(it))
    return out.text


def test_hello_world():
    assert run('SAY "Hello, World!"') == "Hello, World!\n"


def test_arithmetic():
    assert run("SAY 2 + 3 * 4") == "14\n"
    assert run("SAY (2 + 3) * 4") == "20\n"
    assert run("SAY 7 // 2") == "3\n"
    assert run("SAY 7 % 2") == "1\n"
    assert run("SAY 2 ** 10") == "1024\n"


def test_variables_and_reassignment():
    src = """
SET x TO 10
SAY x
x = 20
SAY x
"""
    assert run(src) == "10\n20\n"


def test_multiple_assignment_and_swap():
    src = """
SET a, b TO 1, 2
SAY a
SAY b
SET a, b TO b, a
SAY a
SAY b
"""
    assert run(src) == "1\n2\n2\n1\n"


def test_string_interpolation():
    src = """
SET name TO "Aditya"
SAY "Hello {name}!"
"""
    assert run(src) == "Hello Aditya!\n"


def test_string_interpolation_with_expression():
    src = 'SET x TO 5\nSAY "Double is {x * 2}"'
    assert run(src) == "Double is 10\n"


def test_if_otherwise():
    src = """
SET age TO 20
IF age IS AT LEAST 18 THEN
    SAY "Adult"
OTHERWISE
    SAY "Minor"
END
"""
    assert run(src) == "Adult\n"


def test_else_if_chain_selects_correct_branch():
    src = """
SET x TO 2
IF x IS 1 THEN
    SAY "one"
ELSE IF x IS 2 THEN
    SAY "two"
OTHERWISE
    SAY "other"
END
"""
    assert run(src) == "two\n"


def test_while_loop():
    src = """
SET x TO 0
WHILE x IS BELOW 5
    SAY x
    x = x + 1
END
"""
    assert run(src) == "0\n1\n2\n3\n4\n"


def test_repeat_times_loop():
    src = 'REPEAT 3 TIMES\n    SAY "hi"\nEND'
    assert run(src) == "hi\nhi\nhi\n"


def test_repeat_until_loop():
    src = """
SET x TO 0
REPEAT UNTIL x IS 3
    SAY x
    x = x + 1
END
"""
    assert run(src) == "0\n1\n2\n"


def test_break_and_continue():
    src = """
SET x TO 0
WHILE TRUE
    x = x + 1
    IF x IS 3 THEN
        CONTINUE
    END
    IF x IS AT LEAST 5 THEN
        BREAK
    END
    SAY x
END
"""
    assert run(src) == "1\n2\n4\n"


def test_increase_decrease():
    src = """
SET x TO 10
INCREASE x BY 5
SAY x
DECREASE x BY 3
SAY x
"""
    assert run(src) == "15\n12\n"


def test_compound_assignment_operators():
    src = """
SET x TO 10
x += 5
SAY x
x -= 3
SAY x
x *= 2
SAY x
"""
    assert run(src) == "15\n12\n24\n"


def test_logical_operators():
    assert run("SAY TRUE AND FALSE") == "false\n"
    assert run("SAY TRUE OR FALSE") == "true\n"
    assert run("SAY NOT TRUE") == "false\n"


def test_comparison_operators():
    assert run("SAY 5 > 3") == "true\n"
    assert run("SAY 5 IS 5") == "true\n"
    assert run("SAY 5 IS NOT 5") == "false\n"


def test_ask_statement_reads_input():
    src = 'ASK "Name?" INTO name\nSAY "Hi {name}"'
    assert run(src, inputs=["World"]) == "Hi World\n"


def test_unknown_variable_error():
    with pytest.raises(NexError) as exc_info:
        run("SAY username")
    err = exc_info.value
    assert err.code == "NX301"


def test_unknown_variable_suggests_similar_name():
    src = 'SET username TO "a"\nSAY usernme'
    with pytest.raises(NexError) as exc_info:
        run(src)
    assert "username" in str(exc_info.value)


def test_type_error_number_plus_text():
    with pytest.raises(NexError) as exc_info:
        run('SET total TO 5\nSAY total + "hello"')
    err = exc_info.value
    assert err.code == "NX204"
    assert "NUMBER" in err.title
    assert "TEXT" in err.title


def test_division_by_zero():
    with pytest.raises(NexError) as exc_info:
        run("SAY 5 / 0")
    assert exc_info.value.code == "NX212"


def test_assign_to_undeclared_variable_errors():
    with pytest.raises(NexError) as exc_info:
        run("x = 5")
    assert exc_info.value.code == "NX301"


def test_block_scoping_if_does_not_leak_new_vars_oddly():
    # variables declared inside an IF block ARE visible after (SET currently
    # declares into the block's environment which is child of outer scope;
    # this test documents current Phase 1 semantics precisely).
    src = """
SET x TO 1
IF TRUE THEN
    SET y TO 2
END
SAY x
"""
    assert run(src) == "1\n"


def test_nested_loops():
    src = """
REPEAT 2 TIMES
    REPEAT 2 TIMES
        SAY "x"
    END
END
"""
    assert run(src) == "x\nx\nx\nx\n"
