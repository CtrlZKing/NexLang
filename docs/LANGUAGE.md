# NexLang Language Reference (Phase 1 + Phase 2 "POWER" + Phase 3 "Collections" + Phase 3b "Type Safety")

This document describes only what is **implemented and tested today**. For
what's coming, see [ROADMAP.md](ROADMAP.md) and
[PROJECT_STATUS.md](PROJECT_STATUS.md).

## Comments

```
# This is a comment - everything after # on a line is ignored.
```

## Values / Types

| Type      | Example                | Notes |
|-----------|-------------------------|-------|
| `NUMBER`  | `10`, `3.14`, `-2.5`     | integers and floats share the `NUMBER` type name in errors |
| `TEXT`    | `"hello"`, `'hello'`    | single or double quotes |
| `BOOLEAN` | `TRUE`, `FALSE`          | |
| `NOTHING` | `NOTHING`, `NULL`       | NexLang's null value - `NULL` is a readable alias for `NOTHING` |
| `LIST`    | `[1, 2, 3]`             | ordered, mutable, can hold mixed types, can nest |
| `MAP`     | `{"a": 1, "b": 2}`      | key -> value, keys must be hashable (NUMBER/TEXT/BOOLEAN/NOTHING/TUPLE) |
| `SET`     | `SET_OF([1, 2, 2])`     | unordered, no duplicates - see [Sets](#sets) below |
| `TUPLE`   | `TUPLE_OF([1, 2])`      | ordered, immutable - see [Tuples](#tuples) below |
| `FUNCTION`| a `FUNCTION` value      | see [Functions](#functions) below |
| `ERROR`   | what `CATCH` binds      | see [Errors](#errors) below |

Ranges, bytes, dates, regexes, and user-defined objects are **planned**
(Phase 4+) and not usable yet.

## Variables

```
SET x TO 10
SET name TO "Aditya"
SET active TO TRUE
```

Re-assign an existing variable with `=` (this will error with `NX301` if the
variable was never `SET` first - NexLang does not silently create variables
on assignment, to catch typos early):

```
SET x TO 10
x = 20
```

Multiple assignment and swapping:

```
SET a, b TO 1, 2
SET a, b TO b, a      # swap
```

You can also unpack a list (or any value with more than one item) into
several names at once if the counts match:

```
SET a, b TO [1, 2]
SAY a    # 1
SAY b    # 2
```

**Type annotations** (`SET age AS NUMBER TO 15`) are supported and checked
by `nex check` (static semantic analysis - see USER_GUIDE.md Section 26),
but not enforced at runtime by `nex run`/the REPL - see the "Types" section
below. True immutability/constants are **not yet implemented** at all.

## Types

NexLang variables, parameters, and function returns can optionally be
annotated with a type:

```
SET age AS NUMBER TO 15
SET nickname AS TEXT OR NOTHING TO NULL     # union type = "optional"

FUNCTION average_of(a AS NUMBER, b AS NUMBER) RETURNS NUMBER
    RETURN (a + b) / 2
END
```

Valid type names: `NUMBER`, `TEXT`, `BOOLEAN`, `NOTHING`, `LIST`, `MAP`,
`SET`, `TUPLE`, `FUNCTION`, `ERROR`, `ANY`. A union is written `TYPE1 OR
TYPE2` (any number of types); NexLang has no separate "optional" syntax -
write `AS NUMBER OR NOTHING` instead.

**Important: annotations are checked statically by `nex check`, not
enforced by `nex run`.** Running `SET age AS NUMBER TO "fifteen"` executes
exactly as it would without the annotation - NexLang remains a dynamically
typed, dynamically checked language at runtime. `nex check` (or the
NexLang IDE's inline error highlighting, which uses the same check) is
where an annotation mismatch is caught, before you run the program. See
USER_GUIDE.md Section 26 for the complete reference, including exactly
what else `nex check` looks for (undefined names, duplicate declarations,
argument-count mismatches, unreachable code) and how its type inference
works.

## Operators

**Arithmetic:** `+  -  *  /  //  %  **`

**Comparison (symbolic):** `==  !=  <  >  <=  >=`

**Comparison (English):**

| Phrase              | Equivalent |
|---------------------|------------|
| `a IS b`            | `a == b`   |
| `a IS NOT b`        | `a != b`   |
| `a IS AT LEAST b`   | `a >= b`   |
| `a IS AT MOST b`    | `a <= b`   |
| `a IS ABOVE b`      | `a > b`    |
| `a IS BELOW b`      | `a < b`    |
| `a IS BETWEEN b AND c` | `a >= b AND a <= c` |
| `a IS EMPTY`        | `a` is `NOTHING`, or a LIST/TEXT/MAP/SET of length 0 |
| `a CONTAINS b`      | `b` is an element of list `a`, or a substring of text `a` |
| `a STARTS WITH b`   | text `a` starts with text `b` |
| `a ENDS WITH b`     | text `a` ends with text `b` |

**Logical:** `AND  OR  NOT`

**Assignment:** `=`, and compound forms `+=  -=  *=  /=  //=  %=`, plus the
English forms `INCREASE x BY n` / `DECREASE x BY n`.

**Collections:** `SIZE OF x` (works on LIST/TEXT/MAP/SET).

Bitwise operators (`& | ^ ~ << >>`) are **planned** for a later phase.

## Strings

```
SET name TO "Aditya"
SAY "Hello {name}"          # interpolation
SAY "Double is {5 * 2}"     # any expression works inside { }
```

Escape sequences: `\n \t \r \\ \" \' \{ \}`. Multi-line string literals are
**not yet implemented** (planned).

## Output and Input

```
SAY expression                  # prints a value + newline
ASK "What is your name?" INTO name   # reads a line of text into `name`
```

`ASK` always produces `TEXT` today; numeric parsing helpers arrive with the
standard library in Phase 6.

## Conditionals

```
IF age IS AT LEAST 18 THEN
    SAY "Adult"
OTHERWISE
    SAY "Minor"
END
```

```
IF score IS AT LEAST 90 THEN
    SAY "A"
ELSE IF score IS AT LEAST 80 THEN
    SAY "B"
OTHERWISE
    SAY "F"
END
```

`OTHERWISE` is optional; `END` is always required. `UNLESS`, `WHEN`, and
`MATCH`/`CASE` are **planned**.

## Loops

```
REPEAT 5 TIMES
    SAY "Hi"
END

WHILE x IS BELOW 10
    x = x + 1
END

REPEAT UNTIL x IS 0
    x = x - 1
END
```

`BREAK` exits the nearest loop immediately. `CONTINUE` skips to the next
iteration. Both work in every loop form below.

```
FOR EACH item IN [10, 20, 30]
    SAY item
END

FOR i FROM 1 TO 5
    SAY i
END

FOR i FROM 5 DOWN TO 1
    SAY i
END
```

`FOR EACH` works over `LIST`, `TEXT` (iterates characters), and (once maps
exist) `MAP`/`SET`. `FOR i FROM a TO b` counts up; add `DOWN` before `TO` to
count down. Both are whole-number ranges (inclusive of both ends).

## Collections

```
SET numbers TO [5, 2, 9, 1]

ADD 10 TO numbers          # mutates numbers in place
REMOVE 2 FROM numbers      # errors with NX216 if the value isn't present

SAY numbers[0]              # indexing, 0-based
SAY numbers[-1]              # negative indices count from the end
SAY SIZE OF numbers

IF numbers CONTAINS 9 THEN
    SAY "found it"
END

IF numbers IS EMPTY THEN
    SAY "empty"
END
```

Lists can be nested (`SET m TO [[1, 2], [3, 4]]`, then `m[0][1]`) and can
hold mixed types.

**Slicing** works on `LIST`, `TEXT`, and `TUPLE`:

```
SET numbers TO [10, 20, 30, 40, 50]
SAY numbers[1:3]     # [20, 30]  - up to, not including, index 3
SAY numbers[:2]      # [10, 20]  - from the start
SAY numbers[2:]      # [30, 40, 50] - to the end
SAY numbers[:]       # a full copy
```

**Built-in collection functions** (called like any function - see below):
`COUNT(x)`, `SUM(x)`, `AVERAGE(x)`, `MAXIMUM(x)`, `MINIMUM(x)`, `SORTED(x)`,
`REVERSED(x)`, `UNIQUE(x)` all accept `LIST`, `SET`, or `TUPLE`.

## Maps

```
SET person TO {"name": "Aditya", "age": 15}

SAY person["name"]
SAY SIZE OF person

FOR EACH key, value IN person
    SAY "{key}: {value}"
END

IF person CONTAINS "age" THEN     # CONTAINS checks keys for a MAP
    SAY "has an age"
END

SAY KEYS(person)      # a LIST of the keys
SAY VALUES(person)    # a LIST of the values
```

Map keys must be hashable - `NUMBER`, `TEXT`, `BOOLEAN`, `NOTHING`, or
`TUPLE` - a `LIST` or `MAP` as a key is a clear `NX204` diagnostic, not a
crash. Maps are unordered in principle but, like Python dicts, preserve
insertion order in practice. `FROM ... IMPORT`-style access
(`person.name`) does not exist - use `person["name"]`.

## Sets

There is no `{1, 2, 3}` set-literal syntax (it would be ambiguous with an
empty map literal `{}`, and NexLang chose to keep that unambiguous rather
than guess). Instead, build a set from a list:

```
SET unique_numbers TO SET_OF([1, 2, 2, 3, 3, 3])
SAY unique_numbers          # {1, 2, 3} - duplicates removed automatically

IF unique_numbers CONTAINS 2 THEN
    SAY "yes"
END

ADD 4 TO unique_numbers
REMOVE 1 FROM unique_numbers

FOR EACH n IN unique_numbers
    SAY n
END

SAY LIST_OF(unique_numbers)   # convert back to an ordinary LIST
```

`ADD`/`REMOVE` work on sets exactly as they do on lists. Values must be
hashable, same rule as map keys.

## Tuples

An immutable, ordered sequence - useful when you want to guarantee a
collection of values won't change:

```
SET point TO TUPLE_OF([3, 4])
SAY point[0]                # 3 - indexing works like a LIST
SAY point                    # (3, 4)

ADD 5 TO point               # NX204 - tuples are immutable
```

Convert back to a mutable `LIST` with `LIST_OF(point)` when you need to
change it.

## Not yet implemented (collections)

Comprehensions (`[x * x FOR x IN numbers]`), a `{1, 2, 3}` set literal, map
literal keys that are expressions requiring quoting rules beyond a plain
`TEXT`/`NUMBER` key, and generators/iterators as a language concept are
still **planned** - see [ROADMAP.md](ROADMAP.md) Phase 3/5.

## Functions

```
FUNCTION greet(name = "friend")
    RETURN "Hello, " + name + "!"
END

SAY greet("Aditya")     # Hello, Aditya!
SAY greet()               # Hello, friend!
```

- Parameters can have default values (`name = "friend"`); defaults are
  evaluated fresh on every call, and can reference earlier parameters
  (`FUNCTION f(a, b = a + 1)`).
- `RETURN expr` returns a value; a bare `RETURN` (or falling off the end of
  the function with no `RETURN` at all) returns `NOTHING`.
- Recursion works normally (bounded by Python's call stack under the hood -
  see PROJECT_STATUS.md for the practical depth limit).
- A function declared inside another function is a real closure: it can
  see - and call, later - the enclosing function's local variables.
- Calling with too few/too many arguments, or calling something that isn't
  a function, all produce clear diagnostics (`NX214`, `NX222`) rather than
  a Python `TypeError`.

Not yet implemented: keyword arguments, variadic (`*args`-style)
parameters, multiple return values, and lambdas/anonymous functions - see
ROADMAP.md Phase 5.

## Standard-library functions

Besides the collection functions above, these are called the same way -
`NAME(args)`:

| Function | What it does |
|---|---|
| `UPPERCASE(text)` / `LOWERCASE(text)` | case conversion |
| `TRIM(text)` | strips leading/trailing whitespace |
| `SPLIT(text, separator)` | TEXT -> LIST |
| `JOIN(list, separator)` | LIST of TEXT -> TEXT |
| `REPLACE(text, old, new)` | substring replacement |
| `ROUND(number)` / `ROUND(number, digits)` | rounding |
| `RANDOM_BETWEEN(low, high)` | random NUMBER in range (inclusive) |
| `CURRENT_TIME()` | `"HH:MM:SS"` |
| `CURRENT_DATE()` | `"YYYY-MM-DD"` |
| `WAIT(seconds)` | pauses execution |

Every built-in validates its own arguments and raises a NexLang diagnostic
(never a raw Python exception) on misuse. Names are matched
case-insensitively as a fallback after checking for a user variable/function
of that exact name, so `SUM(x)`, `sum(x)`, and `Sum(x)` are equivalent
unless you've defined your own `sum`.

## Errors

```
TRY
    SAY 1 / 0
CATCH err
    SAY "Something went wrong: {err}"
FINALLY
    SAY "Always runs, error or not"
END
```

- `CATCH <name>` is optional to bind (you can write bare `CATCH` to just
  swallow the error), but the clause itself, or `FINALLY`, or both, is
  required - a `TRY` with neither is a parse error (`NX213`).
- `err` inside `CATCH` is a NexLang `ERROR` value (never a raw Python
  exception) with a human-readable message; `SAY err` or `"{err}"` shows it.
- `FINALLY` always runs, whether or not an error occurred, and whether or
  not `CATCH` handled it.
- `TRY` currently catches every kind of NexLang runtime error, including
  the rare internal-bug fallback (`NX999`) - see PROJECT_STATUS.md's
  "Known limitations" for the trade-off this implies.

`THROW`/`RAISE` (raising your own custom errors) is **planned**.

## Modules

```
IMPORT "helpers.nex"

SAY doubled(21)   # a FUNCTION defined in helpers.nex
```

- The path is relative to the importing file's directory (or the current
  directory in the REPL).
- Every `FUNCTION` and top-level `SET` in the imported file becomes
  available - today this is a **flat global namespace at runtime**, not
  `helpers.doubled(21)` - per-module namespacing is planned (Phase 3+).
  (`nex check`'s static analysis *does* look inside an imported file to
  see what it defines, for the purposes of undefined-name checking - see
  USER_GUIDE.md Section 26 - but that's a compile-time convenience, not
  namespacing at runtime.)
- Importing the same file twice is safe (the second `IMPORT` is a no-op);
  a missing file is a clear `NX217` diagnostic, not a crash.

`FROM ... IMPORT`, `IMPORT ... AS ...`, and importing standard-library
modules by bare name (`IMPORT math`) are **planned**.

## Files

```
WRITE "Hello" TO FILE "notes.txt"
APPEND "\nMore text" TO FILE "notes.txt"

SET text TO READ FILE "notes.txt"

IF FILE "notes.txt" EXISTS THEN
    SAY "found it"
END

DELETE FILE "notes.txt"
```

Paths are resolved relative to the running script's directory (or the
current directory in the REPL). Every failure mode (missing file, can't
write, can't delete) is a specific NexLang diagnostic - see
USER_GUIDE.md's error catalog. `CREATE FOLDER`/`DELETE FOLDER` and
directory listing are **planned**.

## Not yet implemented

Comprehensions, classes/objects, enums, pattern matching,
keyword/variadic function arguments, lambdas, `THROW`/custom error types,
per-module namespacing at runtime, generators, decorators, optional
chaining, pipelines, and concurrency are all **designed but not built** -
see [ROADMAP.md](ROADMAP.md) for exactly which phase adds each one, and
[PROJECT_STATUS.md](PROJECT_STATUS.md) for the complete current audit.
(Type annotations and static semantic analysis - undefined names,
duplicate declarations, argument-count and type mismatches, unreachable
code - *are* implemented; see the "Types" section above and
USER_GUIDE.md Section 26.)
