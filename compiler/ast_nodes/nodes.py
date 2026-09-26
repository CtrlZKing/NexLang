"""
NexLang AST Node Definitions
=============================

Every node carries `line` and `column` so later stages (semantic analysis,
interpreter, error reporting) can always point back at the exact source
location that produced it.

Phase 1 covers: literals, variables, arithmetic/logical/comparison
expressions, SAY, ASK, IF/OTHERWISE, WHILE, REPEAT..TIMES, BREAK, CONTINUE,
INCREASE/DECREASE, and blocks/programs.

Later phases will add: FunctionDeclaration, ClassDeclaration, ForStatement,
TryStatement, MatchStatement, ImportStatement, etc. (see docs/ROADMAP.md)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Any


class Node:
    line: int
    column: int


# ---------------------------------------------------------------------------
# Program / Blocks
# ---------------------------------------------------------------------------

@dataclass
class Program(Node):
    statements: List[Node]
    line: int = 0
    column: int = 0


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass
class Literal(Node):
    value: Any
    line: int
    column: int


@dataclass
class InterpolatedString(Node):
    """A string containing {expr} segments, e.g. "Hello {name}"."""
    raw: str
    line: int
    column: int


@dataclass
class Identifier(Node):
    name: str
    line: int
    column: int


@dataclass
class BinaryExpression(Node):
    operator: str
    left: Node
    right: Node
    line: int
    column: int


@dataclass
class UnaryExpression(Node):
    operator: str
    operand: Node
    line: int
    column: int


@dataclass
class LogicalExpression(Node):
    operator: str  # AND / OR
    left: Node
    right: Node
    line: int
    column: int


@dataclass
class Grouping(Node):
    expression: Node
    line: int
    column: int


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class TypeAnnotation:
    """AS NUMBER, or a union like AS NUMBER OR TEXT / AS NUMBER OR NOTHING
    (the latter being how NexLang spells "optional NUMBER" - no separate
    optional syntax needed, see docs/LANGUAGE.md#types)."""
    names: List[str]
    line: int
    column: int

    def __str__(self) -> str:
        return " OR ".join(self.names)


@dataclass
class VariableDeclaration(Node):
    """SET name TO expr   (also handles SET a, b TO expr1, expr2)
    and SET name AS TYPE TO expr (Phase 3b type annotation - single-name
    only, see docs/LANGUAGE.md#types)."""
    names: List[str]
    values: List[Node]
    line: int
    column: int
    annotation: Optional["TypeAnnotation"] = None


@dataclass
class Assignment(Node):
    """name = expr  (concise re-assignment of an existing variable)"""
    name: str
    value: Node
    line: int
    column: int


@dataclass
class CompoundAssignment(Node):
    """x += expr, or INCREASE x BY expr / DECREASE x BY expr"""
    name: str
    operator: str  # '+', '-', '*', '/', '//', '%'
    value: Node
    line: int
    column: int


@dataclass
class SayStatement(Node):
    expression: Node
    line: int
    column: int


@dataclass
class AskStatement(Node):
    """ASK "prompt" INTO variable"""
    prompt: Node
    target: str
    line: int
    column: int


@dataclass
class IfStatement(Node):
    condition: Node
    then_branch: List[Node]
    else_branch: Optional[List[Node]]  # may itself contain a single IfStatement (else-if chain)
    line: int
    column: int


@dataclass
class WhileStatement(Node):
    condition: Node
    body: List[Node]
    line: int
    column: int


@dataclass
class RepeatTimesStatement(Node):
    count: Node
    body: List[Node]
    line: int
    column: int


@dataclass
class RepeatUntilStatement(Node):
    condition: Node
    body: List[Node]
    line: int
    column: int


@dataclass
class BreakStatement(Node):
    line: int
    column: int


@dataclass
class ContinueStatement(Node):
    line: int
    column: int


@dataclass
class ExpressionStatement(Node):
    expression: Node
    line: int
    column: int


# ---------------------------------------------------------------------------
# Phase 2 ("POWER"): collections
# ---------------------------------------------------------------------------

@dataclass
class ListLiteral(Node):
    elements: List[Node]
    line: int
    column: int


@dataclass
class MapLiteral(Node):
    """{"key": value, ...}"""
    keys: List[Node]
    values: List[Node]
    line: int
    column: int


@dataclass
class IndexExpression(Node):
    collection: Node
    index: Node
    line: int
    column: int


@dataclass
class SliceExpression(Node):
    """collection[start:end] - either bound may be omitted."""
    collection: Node
    start: Optional[Node]
    end: Optional[Node]
    line: int
    column: int


@dataclass
class ForEachPairStatement(Node):
    """FOR EACH key, value IN some_map ... END"""
    key_name: str
    value_name: str
    iterable: Node
    body: List[Node]
    line: int
    column: int


@dataclass
class AddToStatement(Node):
    """ADD value TO list_name"""
    value: Node
    target: str
    line: int
    column: int


@dataclass
class RemoveFromStatement(Node):
    """REMOVE value FROM list_name"""
    value: Node
    target: str
    line: int
    column: int


# ---------------------------------------------------------------------------
# Phase 2: functions
# ---------------------------------------------------------------------------

@dataclass
class Param:
    name: str
    default: Optional[Node] = None
    annotation: Optional[TypeAnnotation] = None


@dataclass
class FunctionDeclaration(Node):
    name: str
    params: List[Param]
    body: List[Node]
    line: int
    column: int
    returns: Optional[TypeAnnotation] = None


@dataclass
class ReturnStatement(Node):
    value: Optional[Node]
    line: int
    column: int


@dataclass
class Call(Node):
    """name(arg1, arg2, ...) - resolves to a user FUNCTION or a standard-
    library builtin at call time (see compiler/interpreter/builtins.py)."""
    name: str
    args: List[Node]
    line: int
    column: int


# ---------------------------------------------------------------------------
# Phase 2: control flow
# ---------------------------------------------------------------------------

@dataclass
class ForEachStatement(Node):
    """FOR EACH item IN collection ... END"""
    var_name: str
    iterable: Node
    body: List[Node]
    line: int
    column: int


@dataclass
class ForRangeStatement(Node):
    """FOR i FROM start TO end ... END  (or FROM start DOWN TO end)"""
    var_name: str
    start: Node
    end: Node
    descending: bool
    body: List[Node]
    line: int
    column: int


# ---------------------------------------------------------------------------
# Phase 2: error handling
# ---------------------------------------------------------------------------

@dataclass
class TryStatement(Node):
    try_body: List[Node]
    catch_var: Optional[str]
    catch_body: Optional[List[Node]]
    finally_body: Optional[List[Node]]
    line: int
    column: int


# ---------------------------------------------------------------------------
# Phase 2: modules
# ---------------------------------------------------------------------------

@dataclass
class ImportStatement(Node):
    """IMPORT "path/to/file.nex" - see docs/LANGUAGE.md#modules for the
    (currently local-file-only) semantics."""
    path: Node
    line: int
    column: int


# ---------------------------------------------------------------------------
# Phase 2: filesystem
# ---------------------------------------------------------------------------

@dataclass
class FileRef(Node):
    """FILE <path-expr> - a reference to a file on disk, used by EXISTS,
    READ FILE, WRITE ... TO FILE, APPEND ... TO FILE, and DELETE FILE."""
    path: Node
    line: int
    column: int


@dataclass
class ReadFileExpression(Node):
    """READ FILE <path-expr>"""
    path: Node
    line: int
    column: int


@dataclass
class WriteFileStatement(Node):
    """WRITE <value> TO FILE <path>   or   APPEND <value> TO FILE <path>"""
    value: Node
    path: Node
    append: bool
    line: int
    column: int


@dataclass
class DeleteFileStatement(Node):
    path: Node
    line: int
    column: int
