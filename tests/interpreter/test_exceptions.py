import io
import pytest
from compiler.api import run_source
from compiler.errors.errors import NexError


def run(src):
    out = io.StringIO()
    run_source(src, filename="<test>", output=out)
    return out.getvalue()


def test_try_catch_handles_runtime_error():
    src = "TRY\n    SAY 1 / 0\nCATCH err\n    SAY \"caught\"\nEND\n"
    assert run(src) == "caught\n"


def test_catch_variable_holds_readable_message():
    src = "TRY\n    SAY 1 / 0\nCATCH err\n    SAY err\nEND\n"
    out = run(src)
    assert "caught" not in out  # sanity: not the string "caught"
    assert "divide" in out.lower() or "zero" in out.lower()


def test_finally_always_runs_on_success():
    src = "TRY\n    SAY \"ok\"\nCATCH err\n    SAY \"never\"\nFINALLY\n    SAY \"cleanup\"\nEND\n"
    assert run(src) == "ok\ncleanup\n"


def test_finally_always_runs_on_error():
    src = "TRY\n    SAY 1 / 0\nCATCH err\n    SAY \"caught\"\nFINALLY\n    SAY \"cleanup\"\nEND\n"
    assert run(src) == "caught\ncleanup\n"


def test_no_error_skips_catch_body():
    src = "TRY\n    SAY \"fine\"\nCATCH err\n    SAY \"should not run\"\nEND\n"
    assert run(src) == "fine\n"


def test_try_finally_without_catch_reraises():
    src = "TRY\n    SAY 1 / 0\nFINALLY\n    SAY \"cleanup\"\nEND\n"
    with pytest.raises(NexError):
        run(src)


def test_try_finally_without_catch_still_runs_finally_before_raising():
    out = io.StringIO()
    src = "TRY\n    SAY 1 / 0\nFINALLY\n    SAY \"cleanup\"\nEND\n"
    with pytest.raises(NexError):
        run_source(src, filename="<test>", output=out)
    assert out.getvalue() == "cleanup\n"


def test_nested_try_blocks():
    src = (
        "TRY\n"
        "    TRY\n"
        "        SAY 1 / 0\n"
        "    CATCH inner_err\n"
        "        SAY \"inner caught\"\n"
        "    END\n"
        "    SAY \"outer continues\"\n"
        "CATCH outer_err\n"
        "    SAY \"outer caught\"\n"
        "END\n"
    )
    assert run(src) == "inner caught\nouter continues\n"


def test_error_inside_function_can_be_caught_by_caller():
    src = (
        "FUNCTION risky()\n    RETURN 1 / 0\nEND\n"
        "TRY\n    SAY risky()\nCATCH err\n    SAY \"caught in caller\"\nEND\n"
    )
    assert run(src) == "caught in caller\n"


def test_undefined_variable_can_be_caught():
    src = "TRY\n    SAY totally_undefined\nCATCH err\n    SAY \"caught\"\nEND\n"
    assert run(src) == "caught\n"


def test_break_inside_try_inside_loop_still_breaks():
    src = (
        "FOR EACH n IN [1, 2, 3]\n"
        "    TRY\n"
        "        IF n IS 2 THEN\n"
        "            BREAK\n"
        "        END\n"
        "        SAY n\n"
        "    CATCH err\n"
        "        SAY \"unexpected\"\n"
        "    END\n"
        "END\n"
    )
    assert run(src) == "1\n"
