import io
import pytest
from compiler.api import run_source
from compiler.errors.errors import NexError


def run(src, inputs=None):
    out = io.StringIO()
    inputs = inputs or []
    it = iter(inputs)
    run_source(src, filename="<test>", output=out, input_fn=lambda prompt="": next(it))
    return out.getvalue()


def test_simple_function_call():
    src = 'FUNCTION greet(name)\n    RETURN "Hello, " + name\nEND\nSAY greet("Aditya")\n'
    assert run(src) == "Hello, Aditya\n"


def test_default_parameter_used_when_omitted():
    src = 'FUNCTION greet(name = "friend")\n    RETURN "Hi, " + name\nEND\nSAY greet()\n'
    assert run(src) == "Hi, friend\n"


def test_default_parameter_overridden_when_given():
    src = 'FUNCTION greet(name = "friend")\n    RETURN "Hi, " + name\nEND\nSAY greet("Sam")\n'
    assert run(src) == "Hi, Sam\n"


def test_multiple_parameters():
    src = "FUNCTION combine(a, b)\n    RETURN a + b\nEND\nSAY combine(2, 3)\n"
    assert run(src) == "5\n"


def test_function_with_no_return_yields_nothing():
    src = 'FUNCTION greet(name)\n    SAY "hi " + name\nEND\nSET r TO greet("x")\nSAY r\n'
    assert run(src) == "hi x\nnothing\n"


def test_recursion_factorial():
    src = (
        "FUNCTION fact(n)\n"
        "    IF n IS AT MOST 1 THEN\n"
        "        RETURN 1\n"
        "    END\n"
        "    RETURN n * fact(n - 1)\n"
        "END\n"
        "SAY fact(6)\n"
    )
    assert run(src) == "720\n"


def test_recursion_fibonacci():
    src = (
        "FUNCTION fib(n)\n"
        "    IF n IS AT MOST 1 THEN\n"
        "        RETURN n\n"
        "    END\n"
        "    RETURN fib(n - 1) + fib(n - 2)\n"
        "END\n"
        "SAY fib(10)\n"
    )
    assert run(src) == "55\n"


def test_nested_function_calls():
    src = (
        "FUNCTION square(x)\n    RETURN x * x\nEND\n"
        "FUNCTION sum_of_squares(a, b)\n    RETURN square(a) + square(b)\nEND\n"
        "SAY sum_of_squares(3, 4)\n"
    )
    assert run(src) == "25\n"


def test_function_local_scope_does_not_leak():
    src = (
        "FUNCTION f()\n    SET local_var TO 42\n    RETURN local_var\nEND\n"
        "SAY f()\n"
        "SAY local_var\n"
    )
    with pytest.raises(NexError) as exc_info:
        run(src)
    assert exc_info.value.code == "NX301"


def test_function_can_read_global_variable():
    src = "SET shared TO 10\nFUNCTION f()\n    RETURN shared + 1\nEND\nSAY f()\n"
    assert run(src) == "11\n"


def test_closure_captures_enclosing_function_scope():
    src = (
        "FUNCTION make_adder(base)\n"
        "    FUNCTION adder(x)\n"
        "        RETURN base + x\n"
        "    END\n"
        "    RETURN adder(5)\n"
        "END\n"
        "SAY make_adder(10)\n"
    )
    assert run(src) == "15\n"


def test_missing_required_argument_is_clear_error():
    src = "FUNCTION f(a, b)\n    RETURN a + b\nEND\nSAY f(1)\n"
    with pytest.raises(NexError) as exc_info:
        run(src)
    assert exc_info.value.code == "NX214"


def test_too_many_arguments_is_clear_error():
    src = "FUNCTION f(a)\n    RETURN a\nEND\nSAY f(1, 2, 3)\n"
    with pytest.raises(NexError) as exc_info:
        run(src)
    assert exc_info.value.code == "NX214"


def test_calling_unknown_function_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run("SAY not_a_real_function(1)\n")
    assert exc_info.value.code == "NX301"


def test_calling_a_non_function_variable_is_clear_error():
    src = "SET x TO 5\nSAY x(1)\n"
    with pytest.raises(NexError) as exc_info:
        run(src)
    assert exc_info.value.code == "NX222"


def test_default_expression_can_reference_earlier_parameter():
    src = "FUNCTION f(a, b = a + 1)\n    RETURN b\nEND\nSAY f(10)\n"
    assert run(src) == "11\n"
