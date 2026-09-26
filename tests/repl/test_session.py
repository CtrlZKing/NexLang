"""
Tests for `repl/session.py` - the logic that decides whether a line
typed at the interactive prompt closes a block or submits the whole
program (see PART 1 / "REPL BLOCK TERMINATION RULE" of the project
brief). These are pure-logic tests: no terminal, no subprocess.
"""

from repl.session import ReplSession


def feed_all(lines):
    session = ReplSession()
    results = []
    for line in lines:
        results.append(session.feed(line))
    return results


def test_single_line_requires_explicit_end():
    results = feed_all(['SAY "Hello"'])
    assert results[0].ready is False, "ENTER alone must never execute anything"


def test_single_line_executes_only_after_bare_end():
    results = feed_all(['SAY "Hello"', "END"])
    assert results[0].ready is False
    assert results[1].ready is True
    assert results[1].source.strip() == 'SAY "Hello"'


def test_blank_lines_before_end_are_fine():
    results = feed_all(['SAY "Hello"', "", "END"])
    assert results[-1].ready is True
    assert 'SAY "Hello"' in results[-1].source


def test_if_block_single_end_both_closes_and_submits():
    results = feed_all([
        "SET x TO 10",
        "IF x IS 10 THEN",
        '    SAY "yes"',
        "END",
    ])
    assert [r.ready for r in results] == [False, False, False, True]
    assert results[-1].source.strip().endswith("END")


def test_ask_does_not_execute_while_buffering():
    """Typing an ASK statement, then more lines, must not run anything
    until an explicit submitting END - matching the brief's requirement
    that `ASK "..." INTO x` must not fire just because Enter was pressed."""
    results = feed_all(['ASK "WHAT IS YOUR NAME?" INTO x', "SAY x"])
    assert all(r.ready is False for r in results)


def test_nested_blocks_inner_end_does_not_submit():
    results = feed_all([
        "IF x IS 10 THEN",
        "    IF y IS 20 THEN",
        '        SAY "both"',
        "    END",   # closes inner IF only
    ])
    assert results[-1].ready is False, "the inner END must not submit the outer program"


def test_nested_blocks_outer_end_submits():
    lines = [
        "IF x IS 10 THEN",
        "    IF y IS 20 THEN",
        '        SAY "both"',
        "    END",
        "END",
    ]
    results = feed_all(lines)
    assert results[-2].ready is False  # inner END
    assert results[-1].ready is True   # outer END submits
    src = results[-1].source
    assert src.count("END") == 2


def test_multiple_extra_bare_ends_are_harmless():
    session = ReplSession()
    r1 = session.feed("END")   # nothing buffered - ignored
    assert r1.ready is True
    assert not r1.source.strip()
    r2 = session.feed('SAY "still works"')
    assert r2.ready is False
    r3 = session.feed("END")
    assert r3.ready is True
    assert 'SAY "still works"' in r3.source


def test_session_resets_after_submission():
    session = ReplSession()
    session.feed('SAY "one"')
    session.feed("END")
    assert session.is_empty
    r = session.feed('SAY "two"')
    assert r.ready is False
    assert session.lines == ['SAY "two"']


def test_end_is_case_insensitive():
    results = feed_all(['SAY "Hello"', "end"])
    assert results[-1].ready is True


def test_reset_clears_buffer():
    session = ReplSession()
    session.feed("IF x IS 10 THEN")
    session.reset()
    assert session.is_empty
    assert session.current_depth() == 0
