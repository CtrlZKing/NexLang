"""
NexLang Runtime Support
========================

Holds the pieces of runtime state that don't belong in the tree-walking
interpreter itself: variable environments, the mapping from Python value
types to NexLang type names (used in error messages), and the internal
control-flow signals (break/continue) used to unwind loops.
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from compiler.errors.errors import NexError, SourceLocation, closest_match


class NexRuntimeError(NexError):
    pass


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class ReturnSignal(Exception):
    """Internal control-flow signal carrying a FUNCTION's RETURN value.
    Never seen by NexLang programs - caught at the call site."""

    def __init__(self, value: Any = None):
        super().__init__()
        self.value = value


class FunctionValue:
    """A NexLang FUNCTION, as a runtime value: bindable to a name, callable,
    and closing over the environment it was declared in (which is what
    lets a function defined inside another function see that function's
    local variables - a real, if modest, closure)."""

    def __init__(self, name: str, params, body, closure_env):
        self.name = name
        self.params = params
        self.body = body
        self.closure_env = closure_env

    def __repr__(self) -> str:
        return f"<FUNCTION {self.name}>"


class NexCaughtError:
    """What `CATCH error` binds `error` to: a plain, readable NexLang
    value (never a raw Python exception) carrying the code/title/message
    of whatever NexError was caught."""

    def __init__(self, err: NexError):
        self.code = err.code
        self.title = err.title
        self.message = err.explanation or err.title

    def __str__(self) -> str:
        return self.message

    def __eq__(self, other):
        return isinstance(other, NexCaughtError) and (self.code, self.message) == (other.code, other.message)


def nex_type_name(value: Any) -> str:
    if value is None:
        return "NOTHING"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "NUMBER"
    if isinstance(value, float):
        return "NUMBER"
    if isinstance(value, str):
        return "TEXT"
    if isinstance(value, list):
        return "LIST"
    if isinstance(value, dict):
        return "MAP"
    if isinstance(value, tuple):
        return "TUPLE"
    if isinstance(value, set):
        return "SET"
    if isinstance(value, FunctionValue):
        return "FUNCTION"
    if isinstance(value, NexCaughtError):
        return "ERROR"
    return type(value).__name__.upper()


def nex_repr(value: Any) -> str:
    """How a value is displayed by SAY."""
    if value is None:
        return "nothing"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float) and value.is_integer():
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(nex_repr(v) for v in value) + "]"
    if isinstance(value, tuple):
        return "(" + ", ".join(nex_repr(v) for v in value) + ")"
    if isinstance(value, set):
        if not value:
            return "{}"
        return "{" + ", ".join(nex_repr(v) for v in sorted(value, key=lambda v: (str(type(v)), str(v)))) + "}"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{nex_repr(k)}: {nex_repr(v)}" for k, v in value.items()) + "}"
    if isinstance(value, FunctionValue):
        return f"<function {value.name}>"
    if isinstance(value, NexCaughtError):
        return value.message
    return str(value)


class Environment:
    """A single lexical scope, chained to its parent for variable lookup."""

    def __init__(self, parent: Optional["Environment"] = None):
        self.parent = parent
        self.values: Dict[str, Any] = {}

    def declare(self, name: str, value: Any) -> None:
        self.values[name] = value

    def _find_owner(self, name: str) -> Optional["Environment"]:
        env: Optional[Environment] = self
        while env is not None:
            if name in env.values:
                return env
            env = env.parent
        return None

    def get(self, name: str, filename: str, line: int, column: int) -> Any:
        owner = self._find_owner(name)
        if owner is None:
            candidates = self.all_names()
            suggestion = closest_match(name, candidates)
            suggestions = []
            if suggestion:
                suggestions.append(f"Did you mean `{suggestion}`?")
            raise NexRuntimeError(
                code="NX301",
                title="Unknown variable",
                explanation=f"`{name}` has not been defined before this point.",
                location=SourceLocation(filename, line, column, len(name)),
                suggestions=suggestions or [f"SET {name} TO ...   # define it before use"],
                help_topic="variables",
            )
        return owner.values[name]

    def assign(self, name: str, value: Any, filename: str, line: int, column: int) -> None:
        owner = self._find_owner(name)
        if owner is None:
            raise NexRuntimeError(
                code="NX301",
                title="Unknown variable",
                explanation=(
                    f"`{name}` has not been defined yet, so it cannot be assigned to with `=`. "
                    f"New variables must be introduced with `SET`."
                ),
                location=SourceLocation(filename, line, column, len(name)),
                suggestions=[f"SET {name} TO ..."],
                help_topic="variables",
            )
        owner.values[name] = value

    def all_names(self):
        names = []
        env: Optional[Environment] = self
        while env is not None:
            names.extend(env.values.keys())
            env = env.parent
        return names
