from compiler.lexer.lexer import tokenize
from compiler.lexer.tokens import TokenType


def types_of(tokens):
    return [t.type for t in tokens]


def test_braces_and_colon_tokenize():
    toks = tokenize('{"a": 1}')
    assert types_of(toks)[:5] == [
        TokenType.LBRACE, TokenType.STRING, TokenType.COLON,
        TokenType.NUMBER, TokenType.RBRACE,
    ]


def test_empty_map_tokenizes():
    toks = tokenize("{}")
    assert types_of(toks)[:2] == [TokenType.LBRACE, TokenType.RBRACE]


def test_colon_alone_tokenizes():
    toks = tokenize(":")
    assert toks[0].type == TokenType.COLON


def test_braces_do_not_suppress_newlines_outside_them():
    # sanity: braces use the same paren-depth newline suppression as
    # brackets/parens, so a multi-line map literal is one logical line.
    toks = tokenize('{\n    "a": 1\n}')
    newline_count = sum(1 for t in toks if t.type == TokenType.NEWLINE)
    assert newline_count == 1  # only the trailing NEWLINE, not the internal ones
