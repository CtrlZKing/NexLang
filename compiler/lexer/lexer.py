"""
NexLang Lexer
=============

Converts raw NexLang source text into a stream of `Token` objects.

Design notes:
- NexLang keywords are case-insensitive at the lexical level ("IF", "if",
  "If" all work) but the formatter/style guide recommends UPPERCASE for
  English-like keywords. This keeps the language forgiving for beginners
  without being ambiguous.
- Newlines are significant (they terminate simple statements), so NEWLINE
  is emitted as a real token. Blank lines and comment-only lines do not
  produce empty NEWLINE spam - consecutive newlines are collapsed.
- String interpolation ("Hello {name}") is NOT split apart here; the lexer
  emits it as a single STRING token, and the parser/interpreter later
  detects `{...}` segments. This keeps the lexer simple and the grammar
  for strings uniform.
"""

from __future__ import annotations
from typing import List

from compiler.lexer.tokens import Token, TokenType, KEYWORDS
from compiler.errors.errors import NexError, SourceLocation


class LexError(NexError):
    pass


class Lexer:
    def __init__(self, source: str, filename: str = "<string>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self._paren_depth = 0  # inside (...) newlines are ignored

    # ---- low level character helpers ----

    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx >= len(self.source):
            return ""
        return self.source[idx]

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def _current_source_line(self) -> str:
        start = self.source.rfind("\n", 0, self.pos) + 1
        end = self.source.find("\n", self.pos)
        if end == -1:
            end = len(self.source)
        return self.source[start:end]

    def _error(self, code: str, title: str, explanation: str, suggestions=None,
               line=None, column=None, length=1, help_topic=None) -> LexError:
        line = self.line if line is None else line
        column = self.column if column is None else column
        return LexError(
            code=code,
            title=title,
            explanation=explanation,
            location=SourceLocation(self.filename, line, column, length),
            suggestions=suggestions or [],
            source_line=self._current_source_line(),
            help_topic=help_topic,
        )

    # ---- public API ----

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            self._scan_token()
        self._push(TokenType.NEWLINE, None)  # ensure trailing statement terminated
        self._push(TokenType.EOF, None)
        return self.tokens

    # ---- token production ----

    def _push(self, type_: TokenType, value, line=None, column=None, lexeme=""):
        # collapse repeated NEWLINEs
        if type_ == TokenType.NEWLINE and self.tokens and self.tokens[-1].type == TokenType.NEWLINE:
            return
        self.tokens.append(Token(type_, value, line or self.line, column or self.column, lexeme))

    def _scan_token(self):
        start_line, start_col = self.line, self.column
        ch = self._advance()

        if ch in " \t\r":
            return

        if ch == "\n":
            if self._paren_depth == 0:
                self._push(TokenType.NEWLINE, "\n", start_line, start_col)
            return

        if ch == "#":
            while self._peek() != "\n" and self._peek() != "":
                self._advance()
            return

        if ch == '"' or ch == "'":
            self._scan_string(ch, start_line, start_col)
            return

        if ch.isdigit():
            self._scan_number(ch, start_line, start_col)
            return

        if ch.isalpha() or ch == "_":
            self._scan_identifier(ch, start_line, start_col)
            return

        # symbols / operators
        if ch == "+":
            if self._match("="):
                self._push(TokenType.PLUS_EQ, "+=", start_line, start_col)
            else:
                self._push(TokenType.PLUS, "+", start_line, start_col)
            return
        if ch == "-":
            if self._match("="):
                self._push(TokenType.MINUS_EQ, "-=", start_line, start_col)
            else:
                self._push(TokenType.MINUS, "-", start_line, start_col)
            return
        if ch == "*":
            if self._match("*"):
                self._push(TokenType.DOUBLE_STAR, "**", start_line, start_col)
            elif self._match("="):
                self._push(TokenType.STAR_EQ, "*=", start_line, start_col)
            else:
                self._push(TokenType.STAR, "*", start_line, start_col)
            return
        if ch == "/":
            if self._match("/"):
                if self._match("="):
                    self._push(TokenType.DOUBLE_SLASH_EQ, "//=", start_line, start_col)
                else:
                    self._push(TokenType.DOUBLE_SLASH, "//", start_line, start_col)
            elif self._match("="):
                self._push(TokenType.SLASH_EQ, "/=", start_line, start_col)
            else:
                self._push(TokenType.SLASH, "/", start_line, start_col)
            return
        if ch == "%":
            if self._match("="):
                self._push(TokenType.PERCENT_EQ, "%=", start_line, start_col)
            else:
                self._push(TokenType.PERCENT, "%", start_line, start_col)
            return
        if ch == "=":
            if self._match("="):
                self._push(TokenType.EQEQ, "==", start_line, start_col)
            else:
                self._push(TokenType.EQ, "=", start_line, start_col)
            return
        if ch == "!":
            if self._match("="):
                self._push(TokenType.NEQ, "!=", start_line, start_col)
                return
            raise self._error(
                "NX101", "Unexpected character '!'",
                "NexLang uses `NOT` for logical negation and `!=` for inequality; "
                "a lone `!` is not valid.",
                suggestions=["a NOT b", "a != b"],
                line=start_line, column=start_col,
                help_topic="operators",
            )
        if ch == "<":
            if self._match("="):
                self._push(TokenType.LE, "<=", start_line, start_col)
            else:
                self._push(TokenType.LT, "<", start_line, start_col)
            return
        if ch == ">":
            if self._match("="):
                self._push(TokenType.GE, ">=", start_line, start_col)
            else:
                self._push(TokenType.GT, ">", start_line, start_col)
            return
        if ch == ",":
            self._push(TokenType.COMMA, ",", start_line, start_col)
            return
        if ch == "(":
            self._paren_depth += 1
            self._push(TokenType.LPAREN, "(", start_line, start_col)
            return
        if ch == ")":
            self._paren_depth = max(0, self._paren_depth - 1)
            self._push(TokenType.RPAREN, ")", start_line, start_col)
            return
        if ch == "[":
            self._paren_depth += 1
            self._push(TokenType.LBRACKET, "[", start_line, start_col)
            return
        if ch == "]":
            self._paren_depth = max(0, self._paren_depth - 1)
            self._push(TokenType.RBRACKET, "]", start_line, start_col)
            return
        if ch == "{":
            self._paren_depth += 1
            self._push(TokenType.LBRACE, "{", start_line, start_col)
            return
        if ch == "}":
            self._paren_depth = max(0, self._paren_depth - 1)
            self._push(TokenType.RBRACE, "}", start_line, start_col)
            return
        if ch == ":":
            self._push(TokenType.COLON, ":", start_line, start_col)
            return

        raise self._error(
            "NX101", f"Unexpected character {ch!r}",
            f"The character {ch!r} is not part of any valid NexLang token.",
            line=start_line, column=start_col,
            help_topic="syntax",
        )

    def _scan_string(self, quote: str, start_line: int, start_col: int):
        chars = []
        while True:
            if self._peek() == "":
                raise self._error(
                    "NX102", "Unterminated string literal",
                    "This string was never closed with a matching quote character.",
                    suggestions=[f'{quote}...{quote}'],
                    line=start_line, column=start_col,
                    help_topic="strings",
                )
            if self._peek() == quote:
                self._advance()
                break
            if self._peek() == "\\":
                self._advance()
                esc = self._advance() if self._peek() != "" else ""
                mapping = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "{": "{", "}": "}"}
                chars.append(mapping.get(esc, esc))
                continue
            if self._peek() == "\n":
                raise self._error(
                    "NX102", "Unterminated string literal",
                    "Strings cannot span multiple lines unless you use triple quotes "
                    "(planned) or an escaped \\n.",
                    line=start_line, column=start_col,
                    help_topic="strings",
                )
            chars.append(self._advance())
        value = "".join(chars)
        self._push(TokenType.STRING, value, start_line, start_col, lexeme=f'{quote}{value}{quote}')

    def _scan_number(self, first: str, start_line: int, start_col: int):
        chars = [first]
        is_float = False
        while self._peek().isdigit():
            chars.append(self._advance())
        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            chars.append(self._advance())
            while self._peek().isdigit():
                chars.append(self._advance())
        text = "".join(chars)
        value = float(text) if is_float else int(text)
        self._push(TokenType.NUMBER, value, start_line, start_col, lexeme=text)

    def _scan_identifier(self, first: str, start_line: int, start_col: int):
        chars = [first]
        while self._peek().isalnum() or self._peek() == "_":
            chars.append(self._advance())
        text = "".join(chars)
        upper = text.upper()
        if upper in KEYWORDS:
            self._push(KEYWORDS[upper], upper, start_line, start_col, lexeme=text)
        else:
            self._push(TokenType.IDENTIFIER, text, start_line, start_col, lexeme=text)


def tokenize(source: str, filename: str = "<string>") -> List[Token]:
    return Lexer(source, filename).tokenize()
