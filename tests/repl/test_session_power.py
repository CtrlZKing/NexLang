"""
Phase 2 ("POWER") additions to the REPL: FUNCTION and TRY are now real
block openers, so `repl/session.py`'s depth tracker must treat them the
same way it already treats IF/WHILE/REPEAT/FOR - only submitting once
every opened block is closed. See tests/repl/test_session.py for the
original (Phase 1) behavior these build on.
"""

from repl.session import ReplSession
from unittest.mock import patch
from repl.repl import run_repl


def feed_all(lines):
    session = ReplSession()
    return [session.feed(line) for line in lines]


def test_function_declaration_needs_its_own_end():
    results = feed_all([
        "FUNCTION greet(name)",
        '    RETURN "Hi " + name',
    ])
    assert results[-1].ready is False


def test_function_declaration_end_submits_when_nothing_else_open():
    results = feed_all([
        "FUNCTION greet(name)",
        '    RETURN "Hi " + name',
        "END",
    ])
    assert results[-1].ready is True
    assert "FUNCTION" in results[-1].source


def test_try_catch_end_submits():
    results = feed_all([
        "TRY",
        "    SAY 1 / 0",
        "CATCH err",
        "    SAY err",
        "END",
    ])
    assert results[-1].ready is True


def test_function_containing_if_needs_two_ends():
    results = feed_all([
        "FUNCTION classify(n)",
        "    IF n IS AT LEAST 0 THEN",
        '        RETURN "non-negative"',
        "    END",
    ])
    assert results[-1].ready is False


def test_function_containing_if_second_end_submits():
    session = ReplSession()
    session.feed("FUNCTION classify(n)")
    session.feed("    IF n IS AT LEAST 0 THEN")
    session.feed('        RETURN "non-negative"')
    r = session.feed("    END")  # closes IF only
    assert r.ready is False
    r2 = session.feed("END")  # closes FUNCTION and submits
    assert r2.ready is True


def run_repl_with_input(lines):
    it = iter(lines)

    def fake_input(prompt=""):
        if prompt:
            print(prompt, end="")
        try:
            return next(it)
        except StopIteration:
            raise EOFError()

    with patch("builtins.input", fake_input):
        run_repl()


def test_repl_end_to_end_function_definition_and_call(capsys):
    run_repl_with_input([
        "FUNCTION greet(name)",
        '    RETURN "Hi, " + name',
        "END",
        'SAY greet("Aditya")',
        "END",
        "exit",
    ])
    out = capsys.readouterr().out
    assert "Hi, Aditya" in out


def test_repl_end_to_end_try_catch(capsys):
    run_repl_with_input([
        "TRY",
        "    SAY 1 / 0",
        "CATCH err",
        '    SAY "caught it"',
        "END",
        "exit",
    ])
    out = capsys.readouterr().out
    assert "caught it" in out


def test_repl_end_to_end_list_and_for_each(capsys):
    run_repl_with_input([
        "SET numbers TO [1, 2, 3]",
        "END",
        "FOR EACH n IN numbers",
        "    SAY n",
        "END",
        "exit",
    ])
    out = capsys.readouterr().out
    assert out.count("\n") >= 3  # 1, 2, 3 each on their own line
    assert "1" in out and "2" in out and "3" in out
