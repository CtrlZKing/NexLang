"""
NexLang standard-library builtins
====================================

A deliberately small set of standard-library functions, callable with the
same `NAME(args)` syntax as a user-defined `FUNCTION` (see
`ast.Call` / `Interpreter._eval_Call`). Per the language-design rule
"use language keywords for constructs, standard-library APIs for
functionality" (docs/ARCHITECTURE.md), collection aggregates, text
transforms, randomness, and time all live here rather than as new
grammar - only `SIZE OF` (a genuinely idiomatic NexLang phrase used
throughout the language) got its own keyword-level syntax.

Every entry is `name -> callable(args: list, interpreter, node) -> value`.
Each callable is responsible for validating its own arguments and raising
a `NexRuntimeError` (never a raw Python exception) on misuse.
"""

from __future__ import annotations

import random
import time as _time
import datetime as _datetime
from typing import Any, Callable, Dict, List

from compiler.interpreter.runtime import nex_type_name


def _arity_error(interp, node, name: str, expected: str, got: int):
    return interp._runtime_error(
        "NX214", "Wrong number of arguments",
        f"`{name}(...)` expects {expected}, but got {got}.",
        node,
        help_topic="functions",
    )


def _type_error(interp, node, name: str, expected: str, value: Any):
    return interp._runtime_error(
        "NX204", f"Wrong argument type for {name}",
        f"`{name}(...)` expects {expected}, but got {nex_type_name(value)}.",
        node,
        help_topic="types",
    )


def _require_list(interp, node, name, value):
    if not isinstance(value, list):
        raise _type_error(interp, node, name, "a LIST", value)


def _as_list_like(interp, node, name, value):
    """COUNT/SUM/AVERAGE/MAXIMUM/MINIMUM/SORTED/REVERSED/UNIQUE accept any
    of NexLang's collection types, not just LIST - order doesn't matter
    for these aggregate operations."""
    if isinstance(value, list):
        return value
    if isinstance(value, (set, tuple)):
        return list(value)
    raise _type_error(interp, node, name, "a LIST, SET, or TUPLE", value)


def _require_number(interp, node, name, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise _type_error(interp, node, name, "a NUMBER", value)


def _require_text(interp, node, name, value):
    if not isinstance(value, str):
        raise _type_error(interp, node, name, "TEXT", value)


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

def _count(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "COUNT", "1 argument", len(args))
    value = args[0]
    if isinstance(value, (list, str, dict, set, tuple)):
        return len(value)
    raise _type_error(interp, node, "COUNT", "a LIST, TEXT, MAP, or SET", value)


def _sum(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "SUM", "1 argument", len(args))
    values = _as_list_like(interp, node, "SUM", args[0])
    for v in values:
        _require_number(interp, node, "SUM", v)
    return sum(values)


def _average(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "AVERAGE", "1 argument", len(args))
    values = _as_list_like(interp, node, "AVERAGE", args[0])
    if not values:
        raise interp._runtime_error(
            "NX215", "Cannot average an empty list",
            "`AVERAGE(...)` needs at least one item.", node, help_topic="collections",
        )
    for v in values:
        _require_number(interp, node, "AVERAGE", v)
    return sum(values) / len(values)


def _maximum(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "MAXIMUM", "1 argument", len(args))
    values = _as_list_like(interp, node, "MAXIMUM", args[0])
    if not values:
        raise interp._runtime_error(
            "NX215", "Cannot find the maximum of an empty list",
            "`MAXIMUM(...)` needs at least one item.", node, help_topic="collections",
        )
    return max(values)


def _minimum(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "MINIMUM", "1 argument", len(args))
    values = _as_list_like(interp, node, "MINIMUM", args[0])
    if not values:
        raise interp._runtime_error(
            "NX215", "Cannot find the minimum of an empty list",
            "`MINIMUM(...)` needs at least one item.", node, help_topic="collections",
        )
    return min(values)


def _sorted_(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "SORTED", "1 argument", len(args))
    values = _as_list_like(interp, node, "SORTED", args[0])
    return sorted(values)


def _reversed_(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "REVERSED", "1 argument", len(args))
    values = _as_list_like(interp, node, "REVERSED", args[0])
    return list(reversed(values))


def _unique(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "UNIQUE", "1 argument", len(args))
    values = _as_list_like(interp, node, "UNIQUE", args[0])
    seen = []
    for v in values:
        if v not in seen:
            seen.append(v)
    return seen


# ---------------------------------------------------------------------------
# Maps, sets, tuples (Phase 3 "Collections & Type Safety" - see ROADMAP.md)
# ---------------------------------------------------------------------------

def _set_of(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "SET_OF", "1 argument", len(args))
    _require_list(interp, node, "SET_OF", args[0])
    try:
        return set(args[0])
    except TypeError:
        raise _type_error(interp, node, "SET_OF", "a LIST of hashable values", args[0])


def _tuple_of(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "TUPLE_OF", "1 argument", len(args))
    _require_list(interp, node, "TUPLE_OF", args[0])
    return tuple(args[0])


def _list_of(args, interp, node):
    """Converts a SET, TUPLE, or MAP's keys back into an ordinary,
    mutable LIST - the inverse of SET_OF/TUPLE_OF, and how a MAP's keys
    become something ADD/REMOVE/indexing can work with."""
    if len(args) != 1:
        raise _arity_error(interp, node, "LIST_OF", "1 argument", len(args))
    value = args[0]
    if isinstance(value, (set, tuple)):
        return list(value)
    if isinstance(value, dict):
        return list(value.keys())
    if isinstance(value, str):
        return list(value)
    raise _type_error(interp, node, "LIST_OF", "a SET, TUPLE, MAP, or TEXT", value)


def _keys(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "KEYS", "1 argument", len(args))
    if not isinstance(args[0], dict):
        raise _type_error(interp, node, "KEYS", "a MAP", args[0])
    return list(args[0].keys())


def _values(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "VALUES", "1 argument", len(args))
    if not isinstance(args[0], dict):
        raise _type_error(interp, node, "VALUES", "a MAP", args[0])
    return list(args[0].values())


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------

def _uppercase(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "UPPERCASE", "1 argument", len(args))
    _require_text(interp, node, "UPPERCASE", args[0])
    return args[0].upper()


def _lowercase(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "LOWERCASE", "1 argument", len(args))
    _require_text(interp, node, "LOWERCASE", args[0])
    return args[0].lower()


def _trim(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "TRIM", "1 argument", len(args))
    _require_text(interp, node, "TRIM", args[0])
    return args[0].strip()


def _split(args, interp, node):
    if len(args) != 2:
        raise _arity_error(interp, node, "SPLIT", "2 arguments (text, separator)", len(args))
    _require_text(interp, node, "SPLIT", args[0])
    _require_text(interp, node, "SPLIT", args[1])
    return args[0].split(args[1])


def _join(args, interp, node):
    if len(args) != 2:
        raise _arity_error(interp, node, "JOIN", "2 arguments (list, separator)", len(args))
    _require_list(interp, node, "JOIN", args[0])
    _require_text(interp, node, "JOIN", args[1])
    for v in args[0]:
        if not isinstance(v, str):
            raise _type_error(interp, node, "JOIN", "a LIST of TEXT", v)
    return args[1].join(args[0])


def _replace(args, interp, node):
    if len(args) != 3:
        raise _arity_error(interp, node, "REPLACE", "3 arguments (text, old, new)", len(args))
    _require_text(interp, node, "REPLACE", args[0])
    _require_text(interp, node, "REPLACE", args[1])
    _require_text(interp, node, "REPLACE", args[2])
    return args[0].replace(args[1], args[2])


def _round(args, interp, node):
    if len(args) not in (1, 2):
        raise _arity_error(interp, node, "ROUND", "1 or 2 arguments", len(args))
    _require_number(interp, node, "ROUND", args[0])
    digits = 0
    if len(args) == 2:
        _require_number(interp, node, "ROUND", args[1])
        digits = int(args[1])
    result = round(args[0], digits) if digits else round(args[0])
    return float(result) if digits else int(result)


# ---------------------------------------------------------------------------
# Randomness and time
# ---------------------------------------------------------------------------

def _random_between(args, interp, node):
    if len(args) != 2:
        raise _arity_error(interp, node, "RANDOM_BETWEEN", "2 arguments (low, high)", len(args))
    _require_number(interp, node, "RANDOM_BETWEEN", args[0])
    _require_number(interp, node, "RANDOM_BETWEEN", args[1])
    low, high = args[0], args[1]
    if isinstance(low, int) and isinstance(high, int):
        return random.randint(low, high)
    return random.uniform(low, high)


def _current_time(args, interp, node):
    if len(args) != 0:
        raise _arity_error(interp, node, "CURRENT_TIME", "no arguments", len(args))
    return _datetime.datetime.now().strftime("%H:%M:%S")


def _current_date(args, interp, node):
    if len(args) != 0:
        raise _arity_error(interp, node, "CURRENT_DATE", "no arguments", len(args))
    return _datetime.date.today().isoformat()


def _wait(args, interp, node):
    if len(args) != 1:
        raise _arity_error(interp, node, "WAIT", "1 argument (seconds)", len(args))
    _require_number(interp, node, "WAIT", args[0])
    if args[0] < 0:
        raise interp._runtime_error(
            "NX204", "Cannot wait a negative amount of time",
            "`WAIT(...)` needs a NUMBER that is zero or greater.", node, help_topic="operators",
        )
    _time.sleep(args[0])
    return None


BUILTINS: Dict[str, Callable[[List[Any], Any, Any], Any]] = {
    "COUNT": _count,
    "SUM": _sum,
    "AVERAGE": _average,
    "MAXIMUM": _maximum,
    "MINIMUM": _minimum,
    "SORTED": _sorted_,
    "REVERSED": _reversed_,
    "UNIQUE": _unique,
    "SET_OF": _set_of,
    "TUPLE_OF": _tuple_of,
    "LIST_OF": _list_of,
    "KEYS": _keys,
    "VALUES": _values,
    "UPPERCASE": _uppercase,
    "LOWERCASE": _lowercase,
    "TRIM": _trim,
    "SPLIT": _split,
    "JOIN": _join,
    "REPLACE": _replace,
    "ROUND": _round,
    "RANDOM_BETWEEN": _random_between,
    "CURRENT_TIME": _current_time,
    "CURRENT_DATE": _current_date,
    "WAIT": _wait,
}
