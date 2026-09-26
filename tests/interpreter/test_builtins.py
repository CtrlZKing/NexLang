import io
import re
import pytest
from compiler.api import run_source
from compiler.errors.errors import NexError


def run(src):
    out = io.StringIO()
    run_source(src, filename="<test>", output=out)
    return out.getvalue()


# ---- text ----

def test_uppercase_lowercase():
    assert run('SAY UPPERCASE("hi")\n') == "HI\n"
    assert run('SAY LOWERCASE("HI")\n') == "hi\n"


def test_trim():
    assert run('SAY TRIM("  hi  ")\n') == "hi\n"


def test_split_and_join():
    assert run('SAY SPLIT("a-b-c", "-")\n') == "[a, b, c]\n"
    assert run('SAY JOIN(["a", "b"], ",")\n') == "a,b\n"


def test_replace():
    assert run('SAY REPLACE("hello world", "world", "there")\n') == "hello there\n"


def test_round_no_digits_and_with_digits():
    assert run("SAY ROUND(3.7)\n") == "4\n"
    assert run("SAY ROUND(3.14159, 2)\n") == "3.14\n"


def test_uppercase_on_non_text_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run("SAY UPPERCASE(5)\n")
    assert exc_info.value.code == "NX204"


def test_wrong_argument_count_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run('SAY UPPERCASE("a", "b")\n')
    assert exc_info.value.code == "NX214"


# ---- randomness and time ----

def test_random_between_int_range_stays_in_bounds():
    src = "FOR i FROM 1 TO 20\n    SET n TO RANDOM_BETWEEN(1, 5)\n    IF n IS AT LEAST 1 THEN\n        IF n IS AT MOST 5 THEN\n            SAY \"ok\"\n        END\n    END\nEND\n"
    out = run(src)
    assert out.count("ok\n") == 20


def test_current_time_format():
    out = run("SAY CURRENT_TIME()\n").strip()
    assert re.match(r"^\d{2}:\d{2}:\d{2}$", out)


def test_current_date_format():
    out = run("SAY CURRENT_DATE()\n").strip()
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", out)


def test_wait_with_zero_seconds_returns_immediately():
    # Regression guard: must not hang or raise for the zero-second case.
    assert run("WAIT(0)\nSAY \"done\"\n") == "done\n"


def test_wait_negative_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run("WAIT(-1)\n")
    assert exc_info.value.code == "NX204"


# ---- combining builtins with the rest of the language ----

def test_builtins_compose_with_functions_and_collections():
    src = (
        "FUNCTION shout(text)\n    RETURN UPPERCASE(text) + \"!\"\nEND\n"
        'SET words TO ["hi", "there"]\n'
        "FOR EACH w IN words\n    SAY shout(w)\nEND\n"
    )
    assert run(src) == "HI!\nTHERE!\n"
