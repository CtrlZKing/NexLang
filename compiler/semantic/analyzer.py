"""
NexLang semantic analysis (Phase 3b "Type Safety")
=====================================================

A static pass over the AST that runs *before* the program executes,
looking for bugs the parser can't see because it only checks grammar, not
meaning. This is what `nex check` runs in addition to parsing (see
`compiler/api.py:check_source`); `nex run` does not run it, so this pass
being new can never change what an already-working program does when run
- only what `nex check` reports about it.

What it catches:

  - Unknown variables/functions (NX401/NX402) - the same mistake the
    interpreter already catches at runtime (NX301), just found before
    the program runs instead of partway through it.
  - Duplicate declarations (NX403) - two parameters with the same name,
    or redeclaring a FUNCTION/variable name that already means something
    else in the same scope. (Ordinary variable *reassignment* - `SET x
    TO 1` followed later by `SET x TO 2` - is completely normal in
    NexLang and is never flagged; only genuine name collisions are.)
  - Argument-count mismatches for calls to FUNCTIONs whose declaration is
    statically visible (NX404) - the same check the interpreter already
    makes at call time (NX214), just found earlier.
  - Type mismatches (NX405) against explicit `AS TYPE` / `RETURNS TYPE`
    annotations (see docs/LANGUAGE.md#types), using a small,
    intentionally conservative type inference (see `infer_type` below):
    if the type of an expression can't be worked out for certain, it is
    never flagged. False negatives (missing a real mismatch) are
    preferred over false positives (flagging correct code).
  - Unreachable code (NX406) - collected as *warnings*, not raised as
    errors, since dead code is a smell rather than necessarily a bug.

Scope tracking mirrors the interpreter's actual runtime scoping exactly
(see `compiler/interpreter/runtime.Environment` and every `_exec_*`
method that constructs a child `Environment(env)`): every IF branch,
loop body, TRY/CATCH/FINALLY body, and function call gets its own child
scope. This analyzer's `Scope` class is the static twin of that, so it
never disagrees with what the interpreter would actually do.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from compiler.ast_nodes import nodes as ast
from compiler.errors.errors import NexError, SourceLocation, closest_match
from compiler.interpreter.builtins import BUILTINS

KNOWN_TYPE_NAMES = {
    "NUMBER", "TEXT", "BOOLEAN", "NOTHING", "LIST", "MAP", "SET",
    "TUPLE", "FUNCTION", "ERROR", "ANY",
}


class SemanticError(NexError):
    pass


@dataclass
class Symbol:
    kind: str  # "variable" | "function" | "parameter"
    node: ast.Node
    type_names: Optional[List[str]] = None   # None = unknown/unconstrained
    params: Optional[List[ast.Param]] = None  # for kind == "function"
    returns: Optional[ast.TypeAnnotation] = None  # for kind == "function"


class Scope:
    def __init__(self, parent: Optional["Scope"] = None):
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def declare(self, name: str, symbol: Symbol) -> None:
        self.symbols[name] = symbol

    def resolve(self, name: str) -> Optional[Symbol]:
        scope: Optional[Scope] = self
        while scope is not None:
            if name in scope.symbols:
                return scope.symbols[name]
            scope = scope.parent
        return None

    def all_names(self) -> List[str]:
        names = []
        scope: Optional[Scope] = self
        while scope is not None:
            names.extend(scope.symbols.keys())
            scope = scope.parent
        return names


def infer_type(node: ast.Node, scope: Scope) -> Optional[str]:
    """Best-effort static type of `node`, or None if it can't be worked
    out for certain (in which case callers must skip type checking for
    it, not guess)."""
    if isinstance(node, ast.Literal):
        v = node.value
        if v is None:
            return "NOTHING"
        if isinstance(v, bool):
            return "BOOLEAN"
        if isinstance(v, (int, float)):
            return "NUMBER"
        if isinstance(v, str):
            return "TEXT"
        return None
    if isinstance(node, ast.InterpolatedString):
        return "TEXT"
    if isinstance(node, ast.ListLiteral):
        return "LIST"
    if isinstance(node, ast.MapLiteral):
        return "MAP"
    if isinstance(node, ast.Grouping):
        return infer_type(node.expression, scope)
    if isinstance(node, ast.LogicalExpression):
        return "BOOLEAN"
    if isinstance(node, ast.BinaryExpression):
        op = node.operator
        if op in ("==", "!=", "<", ">", "<=", ">=", "CONTAINS", "STARTS_WITH", "ENDS_WITH"):
            return "BOOLEAN"
        if op in ("+", "-", "*", "/", "//", "%", "**"):
            lt = infer_type(node.left, scope)
            rt = infer_type(node.right, scope)
            if op == "+" and lt == "TEXT" and rt == "TEXT":
                return "TEXT"
            if lt == "NUMBER" and rt == "NUMBER":
                return "NUMBER"
            return None
        return None
    if isinstance(node, ast.UnaryExpression):
        if node.operator == "-":
            return "NUMBER"
        if node.operator == "SIZE_OF":
            return "NUMBER"
        if node.operator in ("IS_EMPTY", "EXISTS"):
            return "BOOLEAN"
        return None
    if isinstance(node, ast.Identifier):
        sym = scope.resolve(node.name)
        if sym and sym.type_names and len(sym.type_names) == 1:
            return sym.type_names[0]
        return None
    if isinstance(node, ast.Call):
        sym = scope.resolve(node.name)
        if sym and sym.kind == "function" and sym.returns and len(sym.returns.names) == 1:
            return sym.returns.names[0]
        return None
    if isinstance(node, ast.IndexExpression):
        return None  # element type of a collection isn't tracked
    return None


def type_is_compatible(value_type: Optional[str], annotation: ast.TypeAnnotation) -> bool:
    if value_type is None:
        return True  # unknown - conservative: never a false positive
    if "ANY" in annotation.names:
        return True
    return value_type in annotation.names


class SemanticAnalyzer:
    def __init__(self, source_lines: List[str], filename: str, base_dir: Optional[str] = None):
        self.source_lines = source_lines
        self.filename = filename
        self.base_dir = base_dir or (
            os.path.dirname(os.path.abspath(filename)) if not filename.startswith("<") else os.getcwd()
        )
        self.warnings: List[NexError] = []
        self._imported_paths: set = set()
        self._import_unresolved = False
        self._function_return_stack: List[Optional[ast.TypeAnnotation]] = []

    # ---- error helpers ----

    def _line_text(self, line: int) -> str:
        if 1 <= line <= len(self.source_lines):
            return self.source_lines[line - 1]
        return ""

    def _loc(self, node: ast.Node, length: int = 1) -> SourceLocation:
        return SourceLocation(self.filename, node.line, node.column, length)

    def _error(self, code, title, explanation, node: ast.Node, suggestions=None, help_topic=None, length=1):
        return SemanticError(
            code=code, title=title, explanation=explanation,
            location=self._loc(node, length),
            suggestions=suggestions or [],
            source_line=self._line_text(node.line),
            help_topic=help_topic,
        )

    def _warn(self, code, title, explanation, node: ast.Node, help_topic=None):
        self.warnings.append(SemanticError(
            code=code, title=title, explanation=explanation,
            location=self._loc(node),
            source_line=self._line_text(node.line),
            help_topic=help_topic,
        ))

    # ---- public entry point ----

    def analyze(self, program: ast.Program) -> List[NexError]:
        """Analyze `program`. Raises the first hard SemanticError found (a
        NexError - parsing/interpreter code already treats that as the
        uniform way every stage reports a fatal problem). Returns a list
        of non-fatal warnings (currently just unreachable-code) found
        along the way."""
        global_scope = Scope()
        self._global_scope = global_scope
        self._check_block(program.statements, global_scope)
        return self.warnings

    # ---- scope-aware statement walk ----

    def _check_block(self, statements: List[ast.Node], scope: Scope) -> None:
        seen_terminator = False
        warned = False
        for stmt in statements:
            if seen_terminator and not warned:
                self._warn(
                    "NX406", "Unreachable code",
                    "This code can never run - it comes after a RETURN/BREAK/CONTINUE "
                    "that always leaves this block first.",
                    stmt, help_topic="syntax",
                )
                warned = True  # one warning per block is enough
            self._check_stmt(stmt, scope)
            if isinstance(stmt, (ast.ReturnStatement, ast.BreakStatement, ast.ContinueStatement)):
                seen_terminator = True

    def _check_stmt(self, node: ast.Node, scope: Scope) -> None:
        method = getattr(self, f"_check_{type(node).__name__}", None)
        if method is not None:
            method(node, scope)
        else:
            # No specific handler - still walk any expression fields
            # generically so undefined-variable checking doesn't miss
            # newer statement kinds by accident.
            self._check_unknown_stmt(node, scope)

    def _check_unknown_stmt(self, node: ast.Node, scope: Scope) -> None:
        for field_name in getattr(node, "__dataclass_fields__", {}):
            value = getattr(node, field_name)
            if isinstance(value, ast.Node):
                self._check_expr(value, scope)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.Node):
                        self._check_expr(item, scope)

    # ---- individual statement checks ----

    def _check_VariableDeclaration(self, node: ast.VariableDeclaration, scope: Scope):
        for v in node.values:
            self._check_expr(v, scope)
        if node.annotation is not None and len(node.names) == 1 and len(node.values) == 1:
            value_type = infer_type(node.values[0], scope)
            if not type_is_compatible(value_type, node.annotation):
                raise self._error(
                    "NX405", "Type mismatch",
                    f"`{node.names[0]}` is annotated `AS {node.annotation}` but this value is {value_type}.",
                    node.values[0],
                    suggestions=[f"Use a {node.annotation} value, or change the annotation."],
                    help_topic="types",
                )
        for name in node.names:
            existing = scope.symbols.get(name)
            if existing is not None and existing.kind == "function":
                raise self._error(
                    "NX403", "Name already used by a FUNCTION",
                    f"`{name}` is already the name of a FUNCTION in this scope - "
                    f"SET would silently shadow it.",
                    node, help_topic="functions",
                )
            type_names = list(node.annotation.names) if node.annotation else None
            scope.declare(name, Symbol(kind="variable", node=node, type_names=type_names))

    def _check_SayStatement(self, node, scope: Scope):
        self._check_expr(node.expression, scope)

    def _check_AskStatement(self, node, scope: Scope):
        self._check_expr(node.prompt, scope)
        existing = scope.symbols.get(node.target)
        if existing is not None and existing.kind == "function":
            raise self._error(
                "NX403", "Name already used by a FUNCTION",
                f"`{node.target}` is already the name of a FUNCTION in this scope.",
                node, help_topic="functions",
            )
        scope.declare(node.target, Symbol(kind="variable", node=node, type_names=["TEXT"]))

    def _check_IfStatement(self, node, scope: Scope):
        self._check_expr(node.condition, scope)
        self._check_block(node.then_branch, Scope(scope))
        if node.else_branch is not None:
            self._check_block(node.else_branch, Scope(scope))

    def _check_WhileStatement(self, node, scope: Scope):
        self._check_expr(node.condition, scope)
        self._check_block(node.body, Scope(scope))

    def _check_RepeatTimesStatement(self, node, scope: Scope):
        self._check_expr(node.count, scope)
        self._check_block(node.body, Scope(scope))

    def _check_RepeatUntilStatement(self, node, scope: Scope):
        self._check_block(node.body, Scope(scope))
        self._check_expr(node.condition, scope)

    def _check_ForEachStatement(self, node, scope: Scope):
        self._check_expr(node.iterable, scope)
        inner = Scope(scope)
        inner.declare(node.var_name, Symbol(kind="variable", node=node))
        self._check_block(node.body, inner)

    def _check_ForEachPairStatement(self, node, scope: Scope):
        self._check_expr(node.iterable, scope)
        inner = Scope(scope)
        inner.declare(node.key_name, Symbol(kind="variable", node=node))
        inner.declare(node.value_name, Symbol(kind="variable", node=node))
        self._check_block(node.body, inner)

    def _check_ForRangeStatement(self, node, scope: Scope):
        self._check_expr(node.start, scope)
        self._check_expr(node.end, scope)
        inner = Scope(scope)
        inner.declare(node.var_name, Symbol(kind="variable", node=node, type_names=["NUMBER"]))
        self._check_block(node.body, inner)

    def _check_FunctionDeclaration(self, node: ast.FunctionDeclaration, scope: Scope):
        existing = scope.symbols.get(node.name)
        if existing is not None:
            raise self._error(
                "NX403", "Duplicate declaration",
                f"`{node.name}` is already declared in this scope - "
                f"redeclaring a FUNCTION silently replaces the earlier one.",
                node,
                suggestions=[f"Rename this FUNCTION, or remove the earlier `{node.name}`."],
                help_topic="functions",
            )
        scope.declare(node.name, Symbol(
            kind="function", node=node, params=node.params, returns=node.returns,
        ))

        inner = Scope(scope)
        seen_params = set()
        for param in node.params:
            if param.name in seen_params:
                raise self._error(
                    "NX403", "Duplicate parameter name",
                    f"`{param.name}` is used more than once in `{node.name}`'s parameter list.",
                    node, help_topic="functions",
                )
            seen_params.add(param.name)
            if param.default is not None:
                self._check_expr(param.default, inner)
                if param.annotation is not None:
                    default_type = infer_type(param.default, inner)
                    if not type_is_compatible(default_type, param.annotation):
                        raise self._error(
                            "NX405", "Type mismatch",
                            f"Parameter `{param.name}` is annotated `AS {param.annotation}` "
                            f"but its default value is {default_type}.",
                            param.default, help_topic="types",
                        )
            type_names = list(param.annotation.names) if param.annotation else None
            inner.declare(param.name, Symbol(kind="parameter", node=node, type_names=type_names))

        self._function_return_stack.append(node.returns)
        self._check_block(node.body, inner)
        self._function_return_stack.pop()

    def _check_ReturnStatement(self, node: ast.ReturnStatement, scope: Scope):
        if node.value is not None:
            self._check_expr(node.value, scope)
        if self._function_return_stack:
            returns = self._function_return_stack[-1]
            if returns is not None:
                value_type = infer_type(node.value, scope) if node.value is not None else "NOTHING"
                if not type_is_compatible(value_type, returns):
                    raise self._error(
                        "NX405", "Type mismatch",
                        f"This function is declared `RETURNS {returns}` but this RETURN gives {value_type}.",
                        node.value if node.value is not None else node,
                        help_topic="types",
                    )

    def _check_TryStatement(self, node, scope: Scope):
        self._check_block(node.try_body, Scope(scope))
        if node.catch_body is not None:
            catch_scope = Scope(scope)
            if node.catch_var:
                catch_scope.declare(node.catch_var, Symbol(kind="variable", node=node, type_names=["ERROR"]))
            self._check_block(node.catch_body, catch_scope)
        if node.finally_body is not None:
            self._check_block(node.finally_body, Scope(scope))

    def _check_ImportStatement(self, node: ast.ImportStatement, scope: Scope):
        self._check_expr(node.path, scope)
        if not isinstance(node.path, ast.Literal) or not isinstance(node.path.value, str):
            # Dynamic import path - can't resolve statically, so stop
            # trusting undefined-name checks for the rest of the program.
            self._import_unresolved = True
            return
        path_value = node.path.value
        full_path = path_value if os.path.isabs(path_value) else os.path.join(self.base_dir, path_value)
        full_path = os.path.normpath(full_path)
        if full_path in self._imported_paths:
            return
        self._imported_paths.add(full_path)
        try:
            from compiler.lexer.lexer import tokenize
            from compiler.parser.parser import Parser
            with open(full_path, "r", encoding="utf-8") as f:
                module_source = f.read()
            tokens = tokenize(module_source, full_path)
            module_program = Parser(tokens, module_source, full_path).parse_program()
        except Exception:
            # Can't statically see what this import provides - degrade
            # gracefully rather than false-flagging every name it would
            # have defined (see module docstring).
            self._import_unresolved = True
            return
        for stmt in module_program.statements:
            if isinstance(stmt, ast.FunctionDeclaration):
                self._global_scope.declare(stmt.name, Symbol(
                    kind="function", node=stmt, params=stmt.params, returns=stmt.returns,
                ))
            elif isinstance(stmt, ast.VariableDeclaration):
                for name in stmt.names:
                    type_names = list(stmt.annotation.names) if stmt.annotation else None
                    self._global_scope.declare(name, Symbol(kind="variable", node=stmt, type_names=type_names))

    def _check_BreakStatement(self, node, scope: Scope):
        pass

    def _check_ContinueStatement(self, node, scope: Scope):
        pass

    def _check_CompoundAssignment(self, node, scope: Scope):
        self._check_expr(node.value, scope)
        self._resolve_name_use(node.name, node, scope, is_function=False)

    def _check_AddToStatement(self, node, scope: Scope):
        self._check_expr(node.value, scope)
        self._resolve_name_use(node.target, node, scope, is_function=False)

    def _check_RemoveFromStatement(self, node, scope: Scope):
        self._check_expr(node.value, scope)
        self._resolve_name_use(node.target, node, scope, is_function=False)

    def _check_WriteFileStatement(self, node, scope: Scope):
        self._check_expr(node.value, scope)
        self._check_expr(node.path, scope)

    def _check_DeleteFileStatement(self, node, scope: Scope):
        self._check_expr(node.path, scope)

    def _check_ExpressionStatement(self, node, scope: Scope):
        self._check_expr(node.expression, scope)

    # ---- expressions (only need to walk for undefined-name checking) ----

    def _check_expr(self, node: ast.Node, scope: Scope) -> None:
        if node is None:
            return
        if isinstance(node, ast.Identifier):
            self._resolve_name_use(node.name, node, scope, is_function=False)
            return
        if isinstance(node, ast.Call):
            for a in node.args:
                self._check_expr(a, scope)
            self._resolve_call(node, scope)
            return
        if isinstance(node, ast.BinaryExpression):
            self._check_expr(node.left, scope)
            self._check_expr(node.right, scope)
            return
        if isinstance(node, ast.LogicalExpression):
            self._check_expr(node.left, scope)
            self._check_expr(node.right, scope)
            return
        if isinstance(node, ast.UnaryExpression):
            self._check_expr(node.operand, scope)
            return
        if isinstance(node, ast.Grouping):
            self._check_expr(node.expression, scope)
            return
        if isinstance(node, ast.ListLiteral):
            for e in node.elements:
                self._check_expr(e, scope)
            return
        if isinstance(node, ast.MapLiteral):
            for k, v in zip(node.keys, node.values):
                self._check_expr(k, scope)
                self._check_expr(v, scope)
            return
        if isinstance(node, ast.IndexExpression):
            self._check_expr(node.collection, scope)
            self._check_expr(node.index, scope)
            return
        if isinstance(node, ast.SliceExpression):
            self._check_expr(node.collection, scope)
            if node.start is not None:
                self._check_expr(node.start, scope)
            if node.end is not None:
                self._check_expr(node.end, scope)
            return
        if isinstance(node, ast.FileRef):
            self._check_expr(node.path, scope)
            return
        if isinstance(node, ast.ReadFileExpression):
            self._check_expr(node.path, scope)
            return
        if isinstance(node, ast.InterpolatedString):
            # Interpolated `{expr}` segments are re-parsed and evaluated at
            # runtime (see Interpreter._eval_InterpolatedString) rather
            # than pre-parsed into the AST, so there is nothing further
            # for a static pass to walk into here without duplicating
            # that parsing logic - a reasonable, documented limitation
            # (see docs/PROJECT_STATUS.md).
            return
        # Literal and any other leaf/unhandled expression node: nothing to check.

    def _resolve_name_use(self, name: str, node: ast.Node, scope: Scope, is_function: bool) -> None:
        if self._import_unresolved:
            return
        if scope.resolve(name) is not None:
            return
        candidates = scope.all_names()
        suggestion = closest_match(name, candidates)
        suggestions = [f"Did you mean `{suggestion}`?"] if suggestion else []
        raise self._error(
            "NX401", "Unknown variable",
            f"`{name}` has not been defined before this point.",
            node, suggestions=suggestions, help_topic="variables", length=len(name),
        )

    def _resolve_call(self, node: ast.Call, scope: Scope) -> None:
        sym = scope.resolve(node.name)
        if sym is not None:
            if sym.kind != "function":
                raise self._error(
                    "NX402", "This is not a function",
                    f"`{node.name}` is a variable here, not a FUNCTION, so it cannot be called with `(...)`.",
                    node, help_topic="functions",
                )
            self._check_call_arity_and_types(node, sym, scope)
            return
        if node.name.upper() in BUILTINS:
            return  # builtins have their own runtime arity/type checks
        if self._import_unresolved:
            return
        candidates = scope.all_names() + list(BUILTINS.keys())
        suggestion = closest_match(node.name, candidates)
        suggestions = [f"Did you mean `{suggestion}`?"] if suggestion else []
        raise self._error(
            "NX402", "Unknown function",
            f"`{node.name}` has not been defined as a FUNCTION and is not a built-in.",
            node, suggestions=suggestions, help_topic="functions", length=len(node.name),
        )

    def _check_call_arity_and_types(self, node: ast.Call, sym: Symbol, scope: Scope) -> None:
        params = sym.params or []
        if len(node.args) > len(params):
            raise self._error(
                "NX404", "Too many arguments",
                f"`{node.name}(...)` takes {len(params)} argument(s) but this call gives {len(node.args)}.",
                node, help_topic="functions",
            )
        required = sum(1 for p in params if p.default is None)
        if len(node.args) < required:
            raise self._error(
                "NX404", "Missing required argument",
                f"`{node.name}(...)` needs at least {required} argument(s) but this call gives {len(node.args)}.",
                node, help_topic="functions",
            )
        for arg, param in zip(node.args, params):
            if param.annotation is None:
                continue
            arg_type = infer_type(arg, scope)
            if not type_is_compatible(arg_type, param.annotation):
                raise self._error(
                    "NX405", "Type mismatch",
                    f"`{node.name}`'s parameter `{param.name}` is annotated `AS {param.annotation}` "
                    f"but this argument is {arg_type}.",
                    arg, help_topic="types",
                )


def analyze_source(source: str, filename: str, program: Optional[ast.Program] = None,
                    base_dir: Optional[str] = None) -> List[NexError]:
    """Run semantic analysis over already-parsed `program` (or parse
    `source` first if not given). Raises the first SemanticError found;
    returns the list of non-fatal warnings otherwise."""
    if program is None:
        from compiler.lexer.lexer import tokenize
        from compiler.parser.parser import Parser
        tokens = tokenize(source, filename)
        program = Parser(tokens, source, filename).parse_program()
    analyzer = SemanticAnalyzer(source.splitlines(), filename, base_dir=base_dir)
    return analyzer.analyze(program)
