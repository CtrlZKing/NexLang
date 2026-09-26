"""Token types produced by the NexLang lexer."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()

    # Keywords (case-insensitive in source, normalized to upper here)
    SET = auto()
    TO = auto()
    SAY = auto()
    IF = auto()
    THEN = auto()
    OTHERWISE = auto()
    ELSE = auto()          # used only in "ELSE IF"
    END = auto()
    WHILE = auto()
    REPEAT = auto()
    TIMES = auto()
    UNTIL = auto()
    FOR = auto()
    EACH = auto()
    IN = auto()
    BREAK = auto()
    CONTINUE = auto()
    TRUE = auto()
    FALSE = auto()
    NOTHING = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    IS = auto()
    AT = auto()
    LEAST = auto()
    MOST = auto()
    ABOVE = auto()
    BELOW = auto()
    INCREASE = auto()
    DECREASE = auto()
    BY = auto()
    ASK = auto()
    INTO = auto()

    # Phase 2 ("POWER"): functions, collections, control flow, errors, files
    FUNCTION = auto()
    RETURN = auto()
    FROM = auto()
    DOWN = auto()
    IMPORT = auto()
    TRY = auto()
    CATCH = auto()
    FINALLY = auto()
    CONTAINS = auto()
    STARTS = auto()
    ENDS = auto()
    WITH = auto()
    EMPTY = auto()
    BETWEEN = auto()
    EXISTS = auto()
    FILE = auto()
    WRITE = auto()
    APPEND = auto()
    READ = auto()
    DELETE = auto()
    OF = auto()
    SIZE = auto()
    ADD = auto()
    REMOVE = auto()

    # Phase 3b: type annotations
    AS = auto()
    RETURNS = auto()

    # Symbols / operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    DOUBLE_SLASH = auto()
    PERCENT = auto()
    DOUBLE_STAR = auto()
    EQ = auto()             # =
    EQEQ = auto()           # ==
    NEQ = auto()            # !=
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    PLUS_EQ = auto()
    MINUS_EQ = auto()
    STAR_EQ = auto()
    SLASH_EQ = auto()
    DOUBLE_SLASH_EQ = auto()
    PERCENT_EQ = auto()
    COMMA = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    COLON = auto()

    NEWLINE = auto()
    EOF = auto()


KEYWORDS = {
    "SET": TokenType.SET,
    "TO": TokenType.TO,
    "SAY": TokenType.SAY,
    "IF": TokenType.IF,
    "THEN": TokenType.THEN,
    "OTHERWISE": TokenType.OTHERWISE,
    "ELSE": TokenType.ELSE,
    "END": TokenType.END,
    "WHILE": TokenType.WHILE,
    "REPEAT": TokenType.REPEAT,
    "TIMES": TokenType.TIMES,
    "UNTIL": TokenType.UNTIL,
    "FOR": TokenType.FOR,
    "EACH": TokenType.EACH,
    "IN": TokenType.IN,
    "BREAK": TokenType.BREAK,
    "CONTINUE": TokenType.CONTINUE,
    "TRUE": TokenType.TRUE,
    "FALSE": TokenType.FALSE,
    "NOTHING": TokenType.NOTHING,
    "AND": TokenType.AND,
    "OR": TokenType.OR,
    "NOT": TokenType.NOT,
    "IS": TokenType.IS,
    "AT": TokenType.AT,
    "LEAST": TokenType.LEAST,
    "MOST": TokenType.MOST,
    "ABOVE": TokenType.ABOVE,
    "BELOW": TokenType.BELOW,
    "INCREASE": TokenType.INCREASE,
    "DECREASE": TokenType.DECREASE,
    "BY": TokenType.BY,
    "ASK": TokenType.ASK,
    "INTO": TokenType.INTO,

    # Phase 2 ("POWER")
    "FUNCTION": TokenType.FUNCTION,
    "RETURN": TokenType.RETURN,
    "FROM": TokenType.FROM,
    "DOWN": TokenType.DOWN,
    "IMPORT": TokenType.IMPORT,
    "TRY": TokenType.TRY,
    "CATCH": TokenType.CATCH,
    "FINALLY": TokenType.FINALLY,
    "CONTAINS": TokenType.CONTAINS,
    "STARTS": TokenType.STARTS,
    "ENDS": TokenType.ENDS,
    "WITH": TokenType.WITH,
    "EMPTY": TokenType.EMPTY,
    "NULL": TokenType.NOTHING,   # NULL is a readable alias for NOTHING
    "BETWEEN": TokenType.BETWEEN,
    "EXISTS": TokenType.EXISTS,
    "FILE": TokenType.FILE,
    "WRITE": TokenType.WRITE,
    "APPEND": TokenType.APPEND,
    "READ": TokenType.READ,
    "DELETE": TokenType.DELETE,
    "OF": TokenType.OF,
    "SIZE": TokenType.SIZE,
    "ADD": TokenType.ADD,
    "REMOVE": TokenType.REMOVE,

    # Phase 3b: type annotations
    "AS": TokenType.AS,
    "RETURNS": TokenType.RETURNS,
}


@dataclass
class Token:
    type: TokenType
    value: object
    line: int
    column: int
    lexeme: str = ""

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"
