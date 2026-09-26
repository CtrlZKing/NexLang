import pytest
from compiler.lexer.lexer import tokenize
from compiler.lexer.tokens import TokenType
from compiler.errors.errors import NexError


def types_of(tokens):
    return [t.type for t in tokens]


def test_numbers():
    toks = tokenize("42 3.14")
    assert types_of(toks)[:2] == [TokenType.NUMBER, TokenType.NUMBER]
    assert toks[0].value == 42
    assert isinstance(toks[0].value, int)
    assert toks[1].value == 3.14
    assert isinstance(toks[1].value, float)


def test_strings_single_and_double_quotes():
    toks = tokenize('"hello" \'world\'')
    assert toks[0].type == TokenType.STRING
    assert toks[0].value == "hello"
    assert toks[1].type == TokenType.STRING
    assert toks[1].value == "world"


def test_string_escapes():
    toks = tokenize(r'"line1\nline2"')
    assert toks[0].value == "line1\nline2"


def test_unterminated_string_raises_friendly_error():
    with pytest.raises(NexError) as exc_info:
        tokenize('"unterminated')
    err = exc_info.value
    assert err.code == "NX102"


def test_keywords_case_insensitive():
    toks = tokenize("set X to 10\nSAY x\nEnd")
    kinds = types_of(toks)
    assert TokenType.SET in kinds
    assert TokenType.SAY in kinds
    assert TokenType.END in kinds


def test_identifiers_vs_keywords():
    toks = tokenize("SET total TO 5")
    assert toks[0].type == TokenType.SET
    assert toks[1].type == TokenType.IDENTIFIER
    assert toks[1].value == "total"
    assert toks[2].type == TokenType.TO


def test_operators():
    src = "+ - * / // % ** == != < > <= >= = += -= *= /= //= %="
    toks = tokenize(src)
    expected = [
        TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH,
        TokenType.DOUBLE_SLASH, TokenType.PERCENT, TokenType.DOUBLE_STAR,
        TokenType.EQEQ, TokenType.NEQ, TokenType.LT, TokenType.GT,
        TokenType.LE, TokenType.GE, TokenType.EQ, TokenType.PLUS_EQ,
        TokenType.MINUS_EQ, TokenType.STAR_EQ, TokenType.SLASH_EQ,
        TokenType.DOUBLE_SLASH_EQ, TokenType.PERCENT_EQ,
    ]
    assert types_of(toks)[:len(expected)] == expected


def test_comments_are_ignored():
    toks = tokenize("SET x TO 1  # this is a comment\nSAY x")
    kinds = types_of(toks)
    assert TokenType.SAY in kinds
    # comment text must not appear as tokens
    values = [t.value for t in toks]
    assert "this" not in values


def test_unexpected_character_error():
    with pytest.raises(NexError) as exc_info:
        tokenize("SET x TO @")
    assert exc_info.value.code == "NX101"


def test_line_and_column_tracking():
    toks = tokenize("SET x TO 1\nSAY x")
    say_tok = next(t for t in toks if t.type == TokenType.SAY)
    assert say_tok.line == 2
    assert say_tok.column == 1


def test_newlines_collapsed():
    toks = tokenize("SET x TO 1\n\n\nSAY x")
    kinds = types_of(toks)
    # Only one NEWLINE token should separate the two statements
    newline_run = 0
    max_run = 0
    for k in kinds:
        if k == TokenType.NEWLINE:
            newline_run += 1
            max_run = max(max_run, newline_run)
        else:
            newline_run = 0
    assert max_run == 1
