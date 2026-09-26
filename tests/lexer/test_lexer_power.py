from compiler.lexer.lexer import tokenize
from compiler.lexer.tokens import TokenType


def types_of(tokens):
    return [t.type for t in tokens]


def test_new_keywords_tokenize():
    toks = tokenize("FUNCTION RETURN IMPORT TRY CATCH FINALLY")
    assert types_of(toks)[:6] == [
        TokenType.FUNCTION, TokenType.RETURN, TokenType.IMPORT,
        TokenType.TRY, TokenType.CATCH, TokenType.FINALLY,
    ]


def test_collection_and_file_keywords_tokenize():
    toks = tokenize("ADD REMOVE FILE WRITE APPEND READ DELETE SIZE OF EXISTS")
    assert types_of(toks)[:10] == [
        TokenType.ADD, TokenType.REMOVE, TokenType.FILE, TokenType.WRITE,
        TokenType.APPEND, TokenType.READ, TokenType.DELETE, TokenType.SIZE,
        TokenType.OF, TokenType.EXISTS,
    ]


def test_comparison_keywords_tokenize():
    toks = tokenize("CONTAINS STARTS ENDS WITH EMPTY BETWEEN")
    assert types_of(toks)[:6] == [
        TokenType.CONTAINS, TokenType.STARTS, TokenType.ENDS,
        TokenType.WITH, TokenType.EMPTY, TokenType.BETWEEN,
    ]


def test_null_is_an_alias_for_nothing():
    toks = tokenize("NULL")
    assert toks[0].type == TokenType.NOTHING


def test_brackets_tokenize():
    toks = tokenize("[1, 2, 3]")
    assert toks[0].type == TokenType.LBRACKET
    assert toks[-3].type == TokenType.RBRACKET  # before trailing NEWLINE, EOF


def test_keywords_are_case_insensitive():
    toks = tokenize("function Function FUNCTION")
    assert all(t.type == TokenType.FUNCTION for t in toks[:3])


def test_from_and_down_tokenize_for_ranges():
    toks = tokenize("FOR i FROM 1 DOWN TO 10")
    assert types_of(toks)[:6] == [
        TokenType.FOR, TokenType.IDENTIFIER, TokenType.FROM,
        TokenType.NUMBER, TokenType.DOWN, TokenType.TO,
    ]
