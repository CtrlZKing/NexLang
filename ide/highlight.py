"""
NexLang syntax highlighting - span computation
================================================

Turns a buffer of NexLang source into a list of `(start, end, tag)` spans
(character offsets into the *whole* buffer) describing how each piece of
text should be styled. This module has no Tkinter dependency at all, so
it can be unit tested directly (see tests/ide/test_highlight.py) and
reused unchanged if NexLang ever grows a different GUI front end.

It reuses the REAL NexLang lexer rather than inventing a second, fake
one - the IDE should highlight code the same way the language actually
sees it (see PART 5 of the project brief: "the IDE is a frontend for the
real NexLang implementation").

Because the buffer being edited is frequently *not* valid/complete
NexLang (the user is mid-keystroke), tokenizing can raise a lexer error
partway through (e.g. an unterminated string). In that case we still
return whatever spans were produced for the tokens seen before the
error, so the editor doesn't flicker back to unstyled plain text on
every keystroke.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from compiler.lexer.lexer import tokenize
from compiler.lexer.tokens import TokenType
from compiler.errors.errors import NexError

KEYWORD_TOKENS = {
    TokenType.SET, TokenType.TO, TokenType.SAY, TokenType.IF, TokenType.THEN,
    TokenType.OTHERWISE, TokenType.ELSE, TokenType.END, TokenType.WHILE,
    TokenType.REPEAT, TokenType.TIMES, TokenType.UNTIL, TokenType.FOR,
    TokenType.EACH, TokenType.IN, TokenType.BREAK, TokenType.CONTINUE,
    TokenType.AND, TokenType.OR, TokenType.NOT, TokenType.IS, TokenType.AT,
    TokenType.LEAST, TokenType.MOST, TokenType.ABOVE, TokenType.BELOW,
    TokenType.INCREASE, TokenType.DECREASE, TokenType.BY, TokenType.ASK,
    TokenType.INTO,
    # Phase 2 ("POWER")
    TokenType.FUNCTION, TokenType.RETURN, TokenType.FROM, TokenType.DOWN,
    TokenType.IMPORT, TokenType.TRY, TokenType.CATCH, TokenType.FINALLY,
    TokenType.CONTAINS, TokenType.STARTS, TokenType.ENDS, TokenType.WITH,
    TokenType.EMPTY, TokenType.BETWEEN, TokenType.EXISTS, TokenType.FILE,
    TokenType.WRITE, TokenType.APPEND, TokenType.READ, TokenType.DELETE,
    TokenType.OF, TokenType.SIZE, TokenType.ADD, TokenType.REMOVE,
    # Phase 3b (type annotations)
    TokenType.AS, TokenType.RETURNS,
}
LITERAL_TOKENS = {TokenType.TRUE, TokenType.FALSE, TokenType.NOTHING}
OPERATOR_TOKENS = {
    TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH,
    TokenType.DOUBLE_SLASH, TokenType.PERCENT, TokenType.DOUBLE_STAR,
    TokenType.EQ, TokenType.EQEQ, TokenType.NEQ, TokenType.LT, TokenType.GT,
    TokenType.LE, TokenType.GE, TokenType.PLUS_EQ, TokenType.MINUS_EQ,
    TokenType.STAR_EQ, TokenType.SLASH_EQ, TokenType.DOUBLE_SLASH_EQ,
    TokenType.PERCENT_EQ,
}

TAG_FOR_TOKEN = {}
for _t in KEYWORD_TOKENS:
    TAG_FOR_TOKEN[_t] = "keyword"
for _t in LITERAL_TOKENS:
    TAG_FOR_TOKEN[_t] = "literal"
for _t in OPERATOR_TOKENS:
    TAG_FOR_TOKEN[_t] = "operator"
TAG_FOR_TOKEN[TokenType.STRING] = "string"
TAG_FOR_TOKEN[TokenType.NUMBER] = "number"
TAG_FOR_TOKEN[TokenType.IDENTIFIER] = "identifier"


@dataclass
class Span:
    line: int      # 1-indexed, matches Token.line
    col: int       # 1-indexed, matches Token.column
    length: int
    tag: str


def compute_spans(source: str) -> List[Span]:
    """Best-effort: tokenize `source` and return style spans for every
    token found.

    The buffer being edited is frequently not valid/complete NexLang (the
    user is mid-keystroke, e.g. inside an unterminated string), so a
    whole-source tokenize can fail partway through. Rather than showing
    no highlighting at all until the buffer is valid again, fall back to
    tokenizing line-by-line: any one bad line only loses highlighting for
    that line, not the whole file.
    """
    try:
        tokens = tokenize(source, "<ide>")
        return _spans_from_tokens(tokens)
    except NexError:
        pass

    spans: List[Span] = []
    for line_no, line_text in enumerate(source.splitlines(), start=1):
        if not line_text.strip():
            continue
        try:
            line_tokens = tokenize(line_text, "<ide>")
        except NexError:
            continue
        for tok in line_tokens:
            tok.line = line_no  # re-anchor from the single-line tokenize
        spans.extend(_spans_from_tokens(line_tokens))
    return spans


def _spans_from_tokens(tokens) -> List[Span]:
    spans: List[Span] = []
    for tok in tokens:
        tag = TAG_FOR_TOKEN.get(tok.type)
        if tag is None:
            continue
        text = tok.lexeme or str(tok.value)
        length = len(text) if text else 1
        spans.append(Span(line=tok.line, col=tok.column, length=length, tag=tag))
    return spans
