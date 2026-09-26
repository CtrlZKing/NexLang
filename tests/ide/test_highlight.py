from ide.highlight import compute_spans


def _tags(spans):
    return [s.tag for s in spans]


def test_keywords_and_string_and_number_tagged():
    spans = compute_spans('SET x TO 10\nSAY "hi"\n')
    tags = _tags(spans)
    assert "keyword" in tags
    assert "number" in tags
    assert "string" in tags
    assert "identifier" in tags


def test_valid_program_full_span_coverage():
    src = 'IF x IS 10 THEN\n    SAY "yes"\nEND\n'
    spans = compute_spans(src)
    assert any(s.tag == "keyword" and s.line == 1 for s in spans)
    assert any(s.tag == "string" and s.line == 2 for s in spans)
    assert any(s.tag == "keyword" and s.line == 3 for s in spans)


def test_unterminated_string_does_not_kill_highlighting_for_other_lines():
    src = 'SET x TO 10\nSAY "unterminated\nSET y TO 20\n'
    spans = compute_spans(src)
    lines_with_spans = {s.line for s in spans}
    # Lines 1 and 3 are valid on their own and should still be highlighted
    # even though line 2 has a lexer error.
    assert 1 in lines_with_spans
    assert 3 in lines_with_spans


def test_empty_source_has_no_spans():
    assert compute_spans("") == []
