"""
End-to-end tests for `nex repl`, simulating a user typing at the prompt
by feeding canned lines to `builtins.input` (the fallback line-editing
backend used when prompt_toolkit isn't installed - see `repl/repl.py`).
"""

from unittest.mock import patch

from repl.repl import run_repl


def run_repl_with_input(lines):
    it = iter(lines)

    def fake_input(prompt=""):
        # Mirror real input()'s behaviour of writing the prompt to stdout
        # before reading a line, since `ASK "..." INTO x` relies on that
        # (see Interpreter._exec_AskStatement, which calls input_fn(prompt)).
        if prompt:
            print(prompt, end="")
        try:
            return next(it)
        except StopIteration:
            raise EOFError()

    with patch("builtins.input", fake_input):
        run_repl()


def test_single_statement_needs_end_to_print(capsys):
    run_repl_with_input(['SAY "Hello"', "", "END", "exit"])
    out = capsys.readouterr().out
    assert "Hello" in out


def test_enter_alone_does_not_execute(capsys):
    """Regression test for the core bug being fixed: pressing ENTER after
    a statement must not run it prematurely."""
    run_repl_with_input(['SAY "should not print yet"', "exit"])
    out = capsys.readouterr().out
    assert "should not print yet" not in out


def test_if_block_runs_after_single_end(capsys):
    run_repl_with_input([
        "SET x TO 10",
        "IF x IS 10 THEN",
        '    SAY "yes"',
        "END",
        "exit",
    ])
    out = capsys.readouterr().out
    assert "yes" in out


def test_nested_blocks_wait_for_both_ends(capsys):
    run_repl_with_input([
        "IF 1 IS 1 THEN",
        "    IF 2 IS 2 THEN",
        '        SAY "both"',
        "    END",
        "END",
        "exit",
    ])
    out = capsys.readouterr().out
    assert "both" in out


def test_variables_persist_across_submissions(capsys):
    run_repl_with_input([
        "SET x TO 42",
        "END",
        "SAY x",
        "END",
        "exit",
    ])
    out = capsys.readouterr().out
    assert "42" in out


def test_ask_only_prompts_during_execution_not_while_typing(capsys):
    run_repl_with_input([
        'ASK "WHAT IS YOUR NAME?" INTO name',
        'SAY "Hi {name}"',
        "END",
        "Aditya",
        "exit",
    ])
    out = capsys.readouterr().out
    assert "WHAT IS YOUR NAME?" in out
    assert "Hi Aditya" in out


def test_incomplete_block_reports_error_not_silent(capsys):
    """If the user submits (bare END) while a block the parser doesn't
    consider closed remains - i.e. malformed input reaches the parser -
    a clear error should be shown, not a silent no-op or crash."""
    run_repl_with_input([
        "IF 1 IS 1",  # missing THEN - parse error, not a block-tracking issue
        "END",
        "exit",
    ])
    out = capsys.readouterr().out
    assert "ERROR" in out


def test_exit_command_quits_cleanly():
    # Should simply return without raising.
    run_repl_with_input(["exit"])
