"""
NexLang Tree-Walking Interpreter
==================================

Phase 1 executes the AST directly (no bytecode yet - see docs/ROADMAP.md
for when the bytecode VM arrives). This keeps the implementation simple,
correct, and easy to give great error messages from, which matters more
than raw speed at this stage (see PROJECT rule: "correct, readable, tested
... then optimize").
"""

from __future__ import annotations
from typing import Any, List, Optional

from compiler.ast_nodes import nodes as ast
from compiler.errors.errors import SourceLocation, NexError
from compiler.interpreter.runtime import (
    Environment, NexRuntimeError, BreakSignal, ContinueSignal, ReturnSignal,
    FunctionValue, NexCaughtError, nex_type_name, nex_repr,
)
from compiler.interpreter.builtins import BUILTINS


class Interpreter:
    def __init__(self, source: str, filename: str = "<string>", output=None, input_fn=None):
        self.source_lines = source.splitlines()
        self.filename = filename
        self.globals = Environment()
        self.output = output if output is not None else _StdoutWriter()
        self.input_fn = input_fn if input_fn is not None else input
        # Directory used to resolve relative IMPORT paths - real files run
        # via the CLI pass their actual path as `filename`; the REPL and
        # in-memory test sources fall back to the current directory.
        import os
        self.base_dir = os.path.dirname(os.path.abspath(filename)) if not filename.startswith("<") else os.getcwd()
        self._imported_paths = set()

    # ---- helpers ----

    def _line_text(self, line: int) -> str:
        if 1 <= line <= len(self.source_lines):
            return self.source_lines[line - 1]
        return ""

    def _loc(self, node: ast.Node, length: int = 1) -> SourceLocation:
        return SourceLocation(self.filename, node.line, node.column, length)

    def _runtime_error(self, code, title, explanation, node: ast.Node, suggestions=None, help_topic=None, length=1):
        return NexRuntimeError(
            code=code, title=title, explanation=explanation,
            location=self._loc(node, length),
            suggestions=suggestions or [],
            source_line=self._line_text(node.line),
            help_topic=help_topic,
        )

    # ---- public API ----

    def run(self, program: ast.Program) -> None:
        self._exec_block(program.statements, self.globals)

    # ---- statement execution ----

    def _exec_block(self, statements: List[ast.Node], env: Environment) -> None:
        for stmt in statements:
            self._exec(stmt, env)

    def _exec(self, node: ast.Node, env: Environment) -> None:
        method = getattr(self, f"_exec_{type(node).__name__}", None)
        if method is None:
            raise self._runtime_error(
                "NX999", "Internal error",
                f"No executor implemented for AST node {type(node).__name__}.",
                node,
            )
        method(node, env)

    def _exec_VariableDeclaration(self, node: ast.VariableDeclaration, env: Environment):
        values = [self._eval(v, env) for v in node.values]
        if len(node.names) > 1 and len(values) == 1:
            source_val = values[0]
            if not isinstance(source_val, (list, tuple)):
                raise self._runtime_error(
                    "NX208", "Cannot unpack value",
                    f"Tried to unpack {len(node.names)} names from a single {nex_type_name(source_val)} value, "
                    f"but only lists and tuples can be unpacked.",
                    node,
                    suggestions=[f"SET {', '.join(node.names)} TO <a list or tuple with {len(node.names)} items>"],
                    help_topic="variables",
                )
            if len(source_val) != len(node.names):
                raise self._runtime_error(
                    "NX208", "Cannot unpack value",
                    f"Tried to unpack {len(node.names)} names but the value has {len(source_val)} items.",
                    node,
                    help_topic="variables",
                )
            values = list(source_val)
        for name, value in zip(node.names, values):
            env.declare(name, value)

    def _exec_Assignment(self, node: ast.Assignment, env: Environment):
        value = self._eval(node.value, env)
        env.assign(node.name, value, self.filename, node.line, node.column)

    def _exec_CompoundAssignment(self, node: ast.CompoundAssignment, env: Environment):
        current = env.get(node.name, self.filename, node.line, node.column)
        rhs = self._eval(node.value, env)
        new_value = self._apply_binary(node.operator, current, rhs, node)
        env.assign(node.name, new_value, self.filename, node.line, node.column)

    def _exec_SayStatement(self, node: ast.SayStatement, env: Environment):
        value = self._eval(node.expression, env)
        self.output.write(nex_repr(value) + "\n")

    def _exec_AskStatement(self, node: ast.AskStatement, env: Environment):
        prompt = self._eval(node.prompt, env)
        text = self.input_fn(nex_repr(prompt) if not isinstance(prompt, str) else prompt)
        env.declare(node.target, text)

    def _exec_IfStatement(self, node: ast.IfStatement, env: Environment):
        if self._truthy(self._eval(node.condition, env)):
            self._exec_block(node.then_branch, Environment(env))
        elif node.else_branch is not None:
            self._exec_block(node.else_branch, Environment(env))

    def _exec_WhileStatement(self, node: ast.WhileStatement, env: Environment):
        while self._truthy(self._eval(node.condition, env)):
            try:
                self._exec_block(node.body, Environment(env))
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _exec_RepeatTimesStatement(self, node: ast.RepeatTimesStatement, env: Environment):
        count = self._eval(node.count, env)
        if not isinstance(count, (int, float)) or isinstance(count, bool):
            raise self._runtime_error(
                "NX209", "REPEAT count must be a number",
                f"`REPEAT ... TIMES` expects a NUMBER but got {nex_type_name(count)}.",
                node,
                help_topic="loops",
            )
        for _ in range(int(count)):
            try:
                self._exec_block(node.body, Environment(env))
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _exec_RepeatUntilStatement(self, node: ast.RepeatUntilStatement, env: Environment):
        while True:
            try:
                self._exec_block(node.body, Environment(env))
            except BreakSignal:
                break
            except ContinueSignal:
                pass
            if self._truthy(self._eval(node.condition, env)):
                break

    def _exec_BreakStatement(self, node: ast.BreakStatement, env: Environment):
        raise BreakSignal()

    def _exec_ContinueStatement(self, node: ast.ContinueStatement, env: Environment):
        raise ContinueSignal()

    def _exec_ExpressionStatement(self, node: ast.ExpressionStatement, env: Environment):
        self._eval(node.expression, env)

    # ---- Phase 2 ("POWER"): functions ----

    def _exec_FunctionDeclaration(self, node: ast.FunctionDeclaration, env: Environment):
        env.declare(node.name, FunctionValue(node.name, node.params, node.body, closure_env=env))

    def _exec_ReturnStatement(self, node: ast.ReturnStatement, env: Environment):
        value = self._eval(node.value, env) if node.value is not None else None
        raise ReturnSignal(value)

    def _call_function(self, func: FunctionValue, args: List[Any], node: ast.Node) -> Any:
        call_env = Environment(func.closure_env)
        if len(args) > len(func.params):
            raise self._runtime_error(
                "NX214", "Too many arguments",
                f"`{func.name}(...)` takes {len(func.params)} argument(s) but got {len(args)}.",
                node, help_topic="functions",
            )
        for i, param in enumerate(func.params):
            if i < len(args):
                call_env.declare(param.name, args[i])
            elif param.default is not None:
                call_env.declare(param.name, self._eval(param.default, call_env))
            else:
                raise self._runtime_error(
                    "NX214", "Missing required argument",
                    f"`{func.name}(...)` is missing a value for `{param.name}`.",
                    node,
                    suggestions=[f"{func.name}(..., {param.name}=...)"],
                    help_topic="functions",
                )
        try:
            self._exec_block(func.body, call_env)
        except ReturnSignal as ret:
            return ret.value
        return None

    # ---- Phase 2: collections ----

    def _exec_AddToStatement(self, node: ast.AddToStatement, env: Environment):
        target = env.get(node.target, self.filename, node.line, node.column)
        value = self._eval(node.value, env)
        if isinstance(target, list):
            target.append(value)
            return
        if isinstance(target, set):
            try:
                hash(value)
            except TypeError:
                raise self._runtime_error(
                    "NX204", "Cannot add this value to a SET",
                    f"A {nex_type_name(value)} cannot be a member of a SET.",
                    node, help_topic="collections",
                )
            target.add(value)
            return
        raise self._runtime_error(
            "NX204", "Cannot ADD to this value",
            f"`ADD ... TO {node.target}` requires {node.target} to be a LIST or SET, "
            f"but it is {nex_type_name(target)}.",
            node, help_topic="collections",
        )

    def _exec_RemoveFromStatement(self, node: ast.RemoveFromStatement, env: Environment):
        target = env.get(node.target, self.filename, node.line, node.column)
        value = self._eval(node.value, env)
        if isinstance(target, list):
            try:
                target.remove(value)
            except ValueError:
                raise self._runtime_error(
                    "NX216", "Value not found",
                    f"{nex_repr(value)} is not in `{node.target}`, so it cannot be removed.",
                    node, help_topic="collections",
                )
            return
        if isinstance(target, set):
            if value not in target:
                raise self._runtime_error(
                    "NX216", "Value not found",
                    f"{nex_repr(value)} is not in `{node.target}`, so it cannot be removed.",
                    node, help_topic="collections",
                )
            target.discard(value)
            return
        raise self._runtime_error(
            "NX204", "Cannot REMOVE from this value",
            f"`REMOVE ... FROM {node.target}` requires {node.target} to be a LIST or SET, "
            f"but it is {nex_type_name(target)}.",
            node, help_topic="collections",
        )

    # ---- Phase 2: control flow ----

    def _exec_ForEachStatement(self, node: ast.ForEachStatement, env: Environment):
        iterable = self._eval(node.iterable, env)
        if isinstance(iterable, dict):
            items = list(iterable.keys())
        elif isinstance(iterable, (list, tuple, set, str)):
            items = list(iterable)
        else:
            raise self._runtime_error(
                "NX204", "Cannot iterate this value",
                f"`FOR EACH` needs a LIST, MAP, SET, or TEXT, but got {nex_type_name(iterable)}.",
                node, help_topic="loops",
            )
        for item in items:
            loop_env = Environment(env)
            loop_env.declare(node.var_name, item)
            try:
                self._exec_block(node.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _exec_ForEachPairStatement(self, node: ast.ForEachPairStatement, env: Environment):
        iterable = self._eval(node.iterable, env)
        if not isinstance(iterable, dict):
            raise self._runtime_error(
                "NX204", "Cannot iterate key/value pairs of this value",
                f"`FOR EACH key, value IN ...` needs a MAP, but got {nex_type_name(iterable)}.",
                node, help_topic="loops",
            )
        for key, value in list(iterable.items()):
            loop_env = Environment(env)
            loop_env.declare(node.key_name, key)
            loop_env.declare(node.value_name, value)
            try:
                self._exec_block(node.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _exec_ForRangeStatement(self, node: ast.ForRangeStatement, env: Environment):
        start = self._eval(node.start, env)
        end = self._eval(node.end, env)
        for bound, label in ((start, "start"), (end, "end")):
            if not isinstance(bound, (int, float)) or isinstance(bound, bool):
                raise self._runtime_error(
                    "NX209", f"FOR range {label} must be a number",
                    f"`FOR {node.var_name} FROM ... TO ...` expects NUMBERs, "
                    f"but the {label} value is {nex_type_name(bound)}.",
                    node, help_topic="loops",
                )
        step = -1 if node.descending else 1
        current = int(start)
        stop = int(end)
        while (current >= stop) if node.descending else (current <= stop):
            loop_env = Environment(env)
            loop_env.declare(node.var_name, current)
            try:
                self._exec_block(node.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                pass
            current += step

    # ---- Phase 2: error handling ----

    def _exec_TryStatement(self, node: ast.TryStatement, env: Environment):
        try:
            try:
                self._exec_block(node.try_body, Environment(env))
            except NexError as e:
                if node.catch_body is not None:
                    catch_env = Environment(env)
                    if node.catch_var:
                        catch_env.declare(node.catch_var, NexCaughtError(e))
                    self._exec_block(node.catch_body, catch_env)
                else:
                    raise
        finally:
            if node.finally_body is not None:
                self._exec_block(node.finally_body, Environment(env))

    # ---- Phase 2: modules ----

    def _exec_ImportStatement(self, node: ast.ImportStatement, env: Environment):
        import os
        path_value = self._eval(node.path, env)
        if not isinstance(path_value, str):
            raise self._runtime_error(
                "NX204", "IMPORT needs a file path",
                f"`IMPORT ...` expects TEXT (a file path), but got {nex_type_name(path_value)}.",
                node, help_topic="modules",
            )
        full_path = path_value if os.path.isabs(path_value) else os.path.join(self.base_dir, path_value)
        full_path = os.path.normpath(full_path)

        if full_path in self._imported_paths:
            return  # already imported - avoid re-running/circular imports
        if not os.path.isfile(full_path):
            raise self._runtime_error(
                "NX217", "Cannot find imported file",
                f"IMPORT could not find `{path_value}` (looked for `{full_path}`).",
                node,
                suggestions=["Check the file path is correct and relative to the importing file."],
                help_topic="modules",
            )
        self._imported_paths.add(full_path)

        from compiler.lexer.lexer import tokenize
        from compiler.parser.parser import Parser
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                module_source = f.read()
        except OSError as e:
            raise self._runtime_error(
                "NX218", "Could not read imported file",
                f"IMPORT failed to read `{full_path}`: {e.strerror or e}.",
                node, help_topic="modules",
            )
        tokens = tokenize(module_source, full_path)
        module_program = Parser(tokens, module_source, full_path).parse_program()
        # Module-level declarations (FUNCTIONs and top-level SETs) land in
        # the *global* scope - NexLang's module system is currently a flat
        # namespace (see docs/LANGUAGE.md#modules); per-module namespacing
        # is planned for a later phase.
        self._exec_block(module_program.statements, self.globals)

    # ---- Phase 2: filesystem ----

    def _exec_WriteFileStatement(self, node: ast.WriteFileStatement, env: Environment):
        import os
        value = self._eval(node.value, env)
        path_value = self._eval(node.path, env)
        self._require_file_path(path_value, node)
        full_path = path_value if os.path.isabs(path_value) else os.path.join(self.base_dir, path_value)
        mode = "a" if node.append else "w"
        try:
            with open(full_path, mode, encoding="utf-8") as f:
                f.write(nex_repr(value) if not isinstance(value, str) else value)
        except OSError as e:
            raise self._runtime_error(
                "NX219", "File write failed",
                f"Could not {'append to' if node.append else 'write'} `{path_value}`: {e.strerror or e}.",
                node, help_topic="files",
            )

    def _exec_DeleteFileStatement(self, node: ast.DeleteFileStatement, env: Environment):
        import os
        path_value = self._eval(node.path, env)
        self._require_file_path(path_value, node)
        full_path = path_value if os.path.isabs(path_value) else os.path.join(self.base_dir, path_value)
        try:
            os.remove(full_path)
        except FileNotFoundError:
            raise self._runtime_error(
                "NX220", "Cannot delete file",
                f"`{path_value}` does not exist, so it cannot be deleted.",
                node, help_topic="files",
            )
        except OSError as e:
            raise self._runtime_error(
                "NX220", "Cannot delete file",
                f"Could not delete `{path_value}`: {e.strerror or e}.",
                node, help_topic="files",
            )

    def _require_file_path(self, value: Any, node: ast.Node):
        if not isinstance(value, str):
            raise self._runtime_error(
                "NX204", "File path must be TEXT",
                f"Expected a TEXT file path but got {nex_type_name(value)}.",
                node, help_topic="files",
            )

    # ---- expression evaluation ----

    def _eval(self, node: ast.Node, env: Environment) -> Any:
        method = getattr(self, f"_eval_{type(node).__name__}", None)
        if method is None:
            raise self._runtime_error(
                "NX999", "Internal error",
                f"No evaluator implemented for AST node {type(node).__name__}.",
                node,
            )
        return method(node, env)

    def _eval_Literal(self, node: ast.Literal, env: Environment):
        return node.value

    def _eval_InterpolatedString(self, node: ast.InterpolatedString, env: Environment):
        from compiler.lexer.lexer import tokenize
        from compiler.parser.parser import Parser

        result = []
        raw = node.raw
        i = 0
        while i < len(raw):
            ch = raw[i]
            if ch == "{":
                end = raw.find("}", i + 1)
                if end == -1:
                    raise self._runtime_error(
                        "NX210", "Unclosed interpolation",
                        "Found `{` in a string without a matching `}`.",
                        node,
                        help_topic="strings",
                    )
                expr_src = raw[i + 1:end]
                tokens = tokenize(expr_src, self.filename)
                expr_ast = Parser(tokens, expr_src, self.filename)._expression()
                value = self._eval(expr_ast, env)
                result.append(nex_repr(value))
                i = end + 1
            else:
                result.append(ch)
                i += 1
        return "".join(result)

    def _eval_Identifier(self, node: ast.Identifier, env: Environment):
        return env.get(node.name, self.filename, node.line, node.column)

    def _eval_Grouping(self, node: ast.Grouping, env: Environment):
        return self._eval(node.expression, env)

    def _eval_ListLiteral(self, node: ast.ListLiteral, env: Environment):
        return [self._eval(e, env) for e in node.elements]

    def _eval_MapLiteral(self, node: ast.MapLiteral, env: Environment):
        result = {}
        for k_node, v_node in zip(node.keys, node.values):
            key = self._eval(k_node, env)
            try:
                hash(key)
            except TypeError:
                raise self._runtime_error(
                    "NX204", "Map keys must be a simple value",
                    f"A {nex_type_name(key)} cannot be used as a map key.",
                    node, help_topic="collections",
                )
            result[key] = self._eval(v_node, env)
        return result

    def _eval_SliceExpression(self, node: ast.SliceExpression, env: Environment):
        collection = self._eval(node.collection, env)
        if not isinstance(collection, (list, str, tuple)):
            raise self._runtime_error(
                "NX204", "Cannot slice this value",
                f"`[start:end]` slicing works on LIST, TEXT, and TUPLE, but got {nex_type_name(collection)}.",
                node, help_topic="collections",
            )
        start = self._eval(node.start, env) if node.start is not None else None
        end = self._eval(node.end, env) if node.end is not None else None
        for bound, label in ((start, "start"), (end, "end")):
            if bound is not None and (not isinstance(bound, int) or isinstance(bound, bool)):
                raise self._runtime_error(
                    "NX204", "Slice bounds must be whole numbers",
                    f"The slice {label} must be a NUMBER, but got {nex_type_name(bound)}.",
                    node, help_topic="collections",
                )
        return collection[start:end]

    def _eval_IndexExpression(self, node: ast.IndexExpression, env: Environment):
        collection = self._eval(node.collection, env)
        index = self._eval(node.index, env)
        if isinstance(collection, (list, str, tuple)):
            if not isinstance(index, int) or isinstance(index, bool):
                raise self._runtime_error(
                    "NX204", "List/text index must be a whole number",
                    f"Expected a NUMBER index but got {nex_type_name(index)}.",
                    node, help_topic="collections",
                )
            length = len(collection)
            if index < -length or index >= length:
                raise self._runtime_error(
                    "NX221", "Index out of range",
                    f"Index {index} is out of range for a {nex_type_name(collection)} of length {length}.",
                    node,
                    suggestions=[f"Valid indexes here are 0 to {length - 1} (or negative to count from the end)."],
                    help_topic="collections",
                )
            return collection[index]
        if isinstance(collection, dict):
            if index not in collection:
                raise self._runtime_error(
                    "NX221", "Key not found",
                    f"{nex_repr(index)} is not a key in this MAP.",
                    node, help_topic="collections",
                )
            return collection[index]
        raise self._runtime_error(
            "NX204", "Cannot index this value",
            f"`[...]` indexing works on LIST, TEXT, TUPLE, and MAP, but got {nex_type_name(collection)}.",
            node, help_topic="collections",
        )

    def _eval_Call(self, node: ast.Call, env: Environment):
        args = [self._eval(a, env) for a in node.args]

        target = env._find_owner(node.name)
        if target is not None:
            callee = target.values[node.name]
            if isinstance(callee, FunctionValue):
                return self._call_function(callee, args, node)
            raise self._runtime_error(
                "NX222", "This is not a function",
                f"`{node.name}` is a {nex_type_name(callee)}, so it cannot be called with `(...)`.",
                node, help_topic="functions",
            )

        builtin = BUILTINS.get(node.name.upper())
        if builtin is not None:
            return builtin(args, self, node)

        from compiler.errors.errors import closest_match
        candidates = env.all_names() + list(BUILTINS.keys())
        suggestion = closest_match(node.name, candidates)
        suggestions = [f"Did you mean `{suggestion}`?"] if suggestion else \
            [f"FUNCTION {node.name}(...)\n    ...\nEND   # define it before calling it"]
        raise self._runtime_error(
            "NX301", "Unknown function",
            f"`{node.name}` has not been defined as a FUNCTION and is not a built-in.",
            node, suggestions=suggestions, help_topic="functions",
        )

    def _eval_FileRef(self, node: ast.FileRef, env: Environment):
        path = self._eval(node.path, env)
        self._require_file_path(path, node)
        return path

    def _eval_ReadFileExpression(self, node: ast.ReadFileExpression, env: Environment):
        import os
        path_value = self._eval(node.path, env)
        self._require_file_path(path_value, node)
        full_path = path_value if os.path.isabs(path_value) else os.path.join(self.base_dir, path_value)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise self._runtime_error(
                "NX223", "File not found",
                f"`{path_value}` does not exist, so it cannot be read.",
                node, help_topic="files",
            )
        except OSError as e:
            raise self._runtime_error(
                "NX223", "Could not read file",
                f"Could not read `{path_value}`: {e.strerror or e}.",
                node, help_topic="files",
            )

    def _eval_UnaryExpression(self, node: ast.UnaryExpression, env: Environment):
        if node.operator == "SIZE_OF":
            value = self._eval(node.operand, env)
            if isinstance(value, (list, str, dict, set, tuple)):
                return len(value)
            raise self._runtime_error(
                "NX204", "Cannot take SIZE OF this value",
                f"`SIZE OF` works on LIST, TEXT, MAP, and SET, but got {nex_type_name(value)}.",
                node, help_topic="collections",
            )
        if node.operator == "IS_EMPTY":
            value = self._eval(node.operand, env)
            if value is None:
                return True
            if isinstance(value, (list, str, dict, set, tuple)):
                return len(value) == 0
            raise self._runtime_error(
                "NX204", "Cannot check IS EMPTY on this value",
                f"`IS EMPTY` works on LIST, TEXT, MAP, SET, and NOTHING, but got {nex_type_name(value)}.",
                node, help_topic="collections",
            )
        if node.operator == "EXISTS":
            import os
            path = self._eval(node.operand, env)
            self._require_file_path(path, node)
            full_path = path if os.path.isabs(path) else os.path.join(self.base_dir, path)
            return os.path.isfile(full_path)

        value = self._eval(node.operand, env)
        if node.operator == "-":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise self._runtime_error(
                    "NX211", "Cannot negate this value",
                    f"Unary `-` expects a NUMBER but got {nex_type_name(value)}.",
                    node,
                    help_topic="operators",
                )
            return -value
        if node.operator == "NOT":
            return not self._truthy(value)
        raise self._runtime_error("NX999", "Internal error", f"Unknown unary operator {node.operator}", node)

    def _eval_LogicalExpression(self, node: ast.LogicalExpression, env: Environment):
        left = self._eval(node.left, env)
        if node.operator == "AND":
            if not self._truthy(left):
                return left
            return self._eval(node.right, env)
        if node.operator == "OR":
            if self._truthy(left):
                return left
            return self._eval(node.right, env)
        raise self._runtime_error("NX999", "Internal error", f"Unknown logical operator {node.operator}", node)

    def _eval_BinaryExpression(self, node: ast.BinaryExpression, env: Environment):
        left = self._eval(node.left, env)
        right = self._eval(node.right, env)
        return self._apply_binary(node.operator, left, right, node)

    # ---- shared binary-operator semantics ----

    def _truthy(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, (list, dict, set, tuple)):
            return len(value) > 0
        return True

    def _apply_binary(self, operator: str, left: Any, right: Any, node: ast.Node) -> Any:
        numeric_ops = {"+", "-", "*", "/", "//", "%", "**"}
        comparison_ops = {"<", ">", "<=", ">="}

        if operator == "+":
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if isinstance(left, (int, float)) and isinstance(right, (int, float)) \
                    and not isinstance(left, bool) and not isinstance(right, bool):
                return left + right
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            raise self._type_error("+", left, right, node,
                                    fixes=self._add_fixes(left, right))

        if operator in numeric_ops:
            if not self._is_number(left) or not self._is_number(right):
                raise self._type_error(operator, left, right, node)
            if operator == "-":
                return left - right
            if operator == "*":
                return left * right
            if operator == "/":
                if right == 0:
                    raise self._division_by_zero(node)
                return left / right
            if operator == "//":
                if right == 0:
                    raise self._division_by_zero(node)
                return left // right
            if operator == "%":
                if right == 0:
                    raise self._division_by_zero(node)
                return left % right
            if operator == "**":
                return left ** right

        if operator == "==":
            return self._nex_equals(left, right)
        if operator == "!=":
            return not self._nex_equals(left, right)

        if operator == "CONTAINS":
            if isinstance(left, str):
                if not isinstance(right, str):
                    raise self._type_error(operator, left, right, node)
                return right in left
            if isinstance(left, (list, dict, set, tuple)):
                return right in left
            raise self._type_error(operator, left, right, node)

        if operator in ("STARTS_WITH", "ENDS_WITH"):
            if not isinstance(left, str) or not isinstance(right, str):
                raise self._type_error(operator, left, right, node)
            return left.startswith(right) if operator == "STARTS_WITH" else left.endswith(right)

        if operator in comparison_ops:
            if not self._is_number(left) or not self._is_number(right):
                if isinstance(left, str) and isinstance(right, str):
                    py_op = {"<": "<", ">": ">", "<=": "<=", ">=": ">="}[operator]
                    return eval(f"left {py_op} right", {}, {"left": left, "right": right})
                raise self._type_error(operator, left, right, node)
            py_op = operator
            return eval(f"left {py_op} right", {}, {"left": left, "right": right})

        raise self._runtime_error("NX999", "Internal error", f"Unknown operator {operator}", node)

    def _is_number(self, value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _nex_equals(self, left: Any, right: Any) -> bool:
        if self._is_number(left) and self._is_number(right):
            return left == right
        if type(left) != type(right):
            return False
        return left == right

    def _add_fixes(self, left, right):
        lt, rt = nex_type_name(left), nex_type_name(right)
        if {lt, rt} == {"NUMBER", "TEXT"}:
            return [
                "total + 5             # add two numbers together",
                'SAY "{total} hello"    # interpolate the number into a string instead',
            ]
        return []

    def _type_error(self, operator: str, left: Any, right: Any, node: ast.Node, fixes=None):
        lt, rt = nex_type_name(left), nex_type_name(right)
        verb = {
            "+": "add", "-": "subtract", "*": "multiply", "/": "divide",
            "//": "divide", "%": "take the remainder of", "**": "raise",
            "<": "compare", ">": "compare", "<=": "compare", ">=": "compare",
            "CONTAINS": "check CONTAINS on", "STARTS_WITH": "check STARTS WITH on",
            "ENDS_WITH": "check ENDS WITH on",
        }.get(operator, "combine")
        return self._runtime_error(
            "NX204",
            f"Cannot {verb} {lt} and {rt}",
            f"`{lt}` is not compatible with `{rt}` for the `{operator}` operator.",
            node,
            suggestions=fixes or [],
            help_topic="types",
        )

    def _division_by_zero(self, node: ast.Node):
        return self._runtime_error(
            "NX212",
            "Division by zero",
            "Cannot divide by zero.",
            node,
            suggestions=["Check that the divisor is not zero before dividing."],
            help_topic="operators",
        )


class _StdoutWriter:
    def write(self, text: str) -> None:
        import sys
        sys.stdout.write(text)
