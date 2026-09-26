from compiler import indent as indent_engine


def test_if_then_indents_next_line():
    assert indent_engine.next_line_indent("IF x IS 10 THEN") == "    "


def test_non_opener_keeps_same_indent():
    assert indent_engine.next_line_indent('    SAY "yes"') == "    "


def test_nested_if_indents_twice():
    state = indent_engine.IndentState()
    state.feed("IF x IS 10 THEN")
    assert state.indent_for_next_line() == "    "
    state.feed("    IF y IS 20 THEN")
    assert state.indent_for_next_line() == "        "


def test_end_dedents():
    state = indent_engine.IndentState()
    state.feed("IF x IS 10 THEN")
    state.feed('    SAY "yes"')
    assert state.indent_for_line("END") == ""


def test_otherwise_is_a_midpoint_not_a_dedent_forever():
    state = indent_engine.IndentState()
    state.feed("IF x IS 10 THEN")
    state.feed('    SAY "yes"')
    assert state.indent_for_line("OTHERWISE") == ""
    state.feed("OTHERWISE")
    assert state.indent_for_next_line() == "    "


def test_repeat_and_for_each_recognized_as_openers():
    """`REPEAT`/`WHILE` are real, implemented block statements today.
    `FOR EACH` is only reserved syntax (Phase 2) - the indent engine
    recognizes its shape now so it needs no changes once the parser
    actually implements it (see docs/ROADMAP.md)."""
    assert indent_engine.is_opener("REPEAT 5 TIMES")
    assert indent_engine.is_opener("FOR EACH item IN items")
    assert indent_engine.is_opener("WHILE x IS 1")


def test_future_constructs_recognized_for_extensibility():
    assert indent_engine.is_opener("FUNCTION greet")
    assert indent_engine.is_opener("CLASS Animal")
    assert indent_engine.is_opener("TRY")
    assert indent_engine.is_midpoint("CATCH")
    assert indent_engine.is_midpoint("FINALLY")


def test_reindent_buffer_reformats_from_scratch():
    messy = "IF x IS 10 THEN\nSAY \"yes\"\nEND"
    assert indent_engine.reindent_buffer(messy) == 'IF x IS 10 THEN\n    SAY "yes"\nEND'


def test_reindent_buffer_handles_nested_and_blank_lines():
    messy = "IF x IS 10 THEN\n\n    IF y IS 20 THEN\nSAY \"both\"\n    END\nEND"
    result = indent_engine.reindent_buffer(messy)
    assert result == (
        "IF x IS 10 THEN\n"
        "\n"
        "    IF y IS 20 THEN\n"
        '        SAY "both"\n'
        "    END\n"
        "END"
    )
