# NexLang Project Status

Last updated: end of the Phase 3b "Type Safety" work (type annotations +
static semantic analysis), on top of Phase 3 "Collections" and v0.3.0
"POWER" (Phase 2). This file is a factual audit, not a marketing page -
if something below says NOT IMPLEMENTED, it does not work, no matter what
older docs might imply elsewhere.

## Implemented and tested

Everything in this section has passing automated tests
(`python3 tools/run_tests.py` -> 368 passed, 0 failed, 0 skipped as of
this writing - see `docs/IDE_IDENTITY.md` for why the old Tkinter GUI's
single skipped test file no longer applies).

| Area | What works |
|---|---|
| Lexer/Parser/AST | Full Phase 1 + 2 + 3 + 3b grammar (see docs/GRAMMAR.md) |
| Interpreter | Tree-walking, NexLang-native diagnostics throughout (no raw Python tracebacks reach the user) |
| Variables | `SET`, reassignment, multiple assignment, `INCREASE`/`DECREASE ... BY`, optional `AS TYPE` annotation |
| Control flow | `IF`/`ELSE IF`/`OTHERWISE`, `WHILE`, `REPEAT ... TIMES`, `REPEAT UNTIL`, `BREAK`, `CONTINUE` |
| Functions | Declarations, default parameters, recursion, local scope, closures, optional `AS TYPE` parameter and `RETURNS TYPE` annotations |
| Collections | List literals, indexing (incl. negative/nested/string), `ADD`/`REMOVE`, `SIZE OF`, `IS EMPTY`, slicing (`list[1:3]`), `MAP` literals + `FOR EACH key, value`, `SET`/`TUPLE` via `SET_OF`/`TUPLE_OF`/`LIST_OF` |
| Loops | `FOR EACH`, `FOR ... FROM ... TO ...` (ascending/descending), both with working `BREAK`/`CONTINUE` |
| Operators | `IS`/`IS NOT`/`IS AT LEAST`/`IS AT MOST`/`IS ABOVE`/`IS BELOW`/`IS BETWEEN`/`IS EMPTY`, `CONTAINS`, `STARTS WITH`, `ENDS WITH`, `AND`/`OR`/`NOT`, symbolic arithmetic and comparison operators |
| Error handling | `TRY`/`CATCH`/`FINALLY`, catch-only and finally-only forms, nested TRY, errors from inside functions catchable at the call site |
| Modules | `IMPORT "file.nex"` (flat global namespace at runtime - see Known Limitations; `nex check` resolves imported names statically for its own analysis) |
| Filesystem | `READ FILE`, `WRITE`/`APPEND ... TO FILE`, `DELETE FILE`, `FILE ... EXISTS` |
| Standard library | `COUNT`, `SUM`, `AVERAGE`, `MAXIMUM`, `MINIMUM`, `SORTED`, `REVERSED`, `UNIQUE` (all accept LIST/SET/TUPLE), `UPPERCASE`, `LOWERCASE`, `TRIM`, `SPLIT`, `JOIN`, `REPLACE`, `ROUND`, `RANDOM_BETWEEN`, `CURRENT_TIME`, `CURRENT_DATE`, `WAIT`, `SET_OF`, `TUPLE_OF`, `LIST_OF`, `KEYS`, `VALUES` |
| Type annotations | `AS TYPE` on `SET`/parameters, `RETURNS TYPE` on functions, union types (`AS NUMBER OR TEXT`, `OR NOTHING` for optional) - checked statically, not enforced at runtime (see Type Safety row below) |
| Type Safety (static) | `compiler/semantic/analyzer.py`, run by `nex check`: undefined variables/functions (`NX401`/`NX402`, real scope-aware resolution matching the interpreter's own scoping), duplicate declarations (`NX403`), argument-count mismatches (`NX404`), type-annotation mismatches (`NX405`, conservative inference - no false positives), unreachable code (`NX406`, a warning). Does **not** run for `nex run`/the REPL - see Known Limitations |
| CLI | `nex run`, `nex check` (now syntax + semantic), `nex repl`, `nex`/`nex ide`, `nex version`/`--version`, `nex help [topic]` |
| REPL | Explicit `END`-to-submit model (distinct from a script's EOF-based termination), correct nested-block and FUNCTION/TRY-block handling, persistent session state |
| IDE | NexIDE: a local HTML/CSS/JS web app (`ide/web/`), served by a Python backend, opened in an app-mode browser window (or installable as a standalone PWA). Tabs, file explorer, real-lexer syntax highlighting incl. every Phase 2/3b keyword, real-indent-engine smart indentation, Output/Input panels, Run/Stop via the real interpreter in a subprocess, live syntax-*and-semantic*-check diagnostics (inherits the new checks automatically via `check_source`). The earlier Tkinter GUI is archived, not deleted, under `ide/legacy_tkinter/` - see `docs/IDE_IDENTITY.md` |

## Partially implemented

- **`stdlib/`, `formatter/`, `linter/`, `debugger/` directories** exist as
  placeholders with no real logic behind them yet. Nothing imports or
  calls into them. Treat any README inside those folders as aspirational,
  not descriptive.
- **`IMPORT`** works for functions and top-level variables, but everything
  lands in one flat global namespace - there is no `module.name` access,
  no re-export control, and no way to import just part of a file.

## Not implemented (despite being requested in the long-term vision docs)

Being explicit here because the project brief specifically warned against
claiming a feature works when it only parses, or documenting something as
done when it isn't:

- A `{1, 2, 3}` set literal (deliberately deferred - it would be ambiguous
  with an empty map `{}`; use `SET_OF([1, 2, 3])` instead), comprehensions, generators/iterators as a language concept
- Type *enforcement* at runtime, type inference beyond a small
  deliberately-conservative set of provably-safe cases, generics - static
  type annotations and checking (`nex check` only) ARE implemented, see
  the Type Safety row above and docs/USER_GUIDE.md Section 26
- Classes, objects, inheritance, interfaces, `NEW`, `self`
- Enums, pattern matching (`MATCH`)
- Lambdas/anonymous functions, higher-order functions as first-class values, keyword arguments, variadic parameters
- Async/concurrency (`ASYNC FUNCTION`, `AWAIT`, tasks)
- A bytecode compiler or VM - the interpreter is tree-walking only
- A real formatter or linter (the directories exist; the logic doesn't)
- A debugger, breakpoints, or LSP/editor intelligence beyond syntax highlighting and inline error markers
- A package manager (`nex.toml`, `nex install`, etc.)
- NexGame, NexWeb, NexGUI - no graphics, HTTP server, or desktop-widget framework of any kind
- Native compilation, self-hosting

None of the CLI commands the project vision lists for these (`nex build`,
`nex test`, `nex format`, `nex lint`, `nex debug`, `nex init`,
`nex install`, `nex remove`, `nex update`, `nex docs`) exist. `nex help`
prints them under "Planned (not yet implemented)" rather than pretending
they work.

## Known limitations of what IS implemented

- Every keyword is a reserved word, case-insensitively. This means you
  cannot name a variable or function `add`, `remove`, `size`, `file`,
  `import`, etc. This is consistent with how `set`, `if`, `to` and every
  other Phase 1 keyword already behaved - it isn't a new kind of
  limitation, just a bigger reserved-word list now.
- Recursion depth is bounded by Python's call stack (effectively ~1000
  levels) since each NexLang call is a real Python call. Deep recursion
  (e.g. naive recursive Fibonacci past n≈30) will be slow and could hit
  that ceiling; there's no tail-call optimization.
- `TRY`/`CATCH` catches any `NexError`, including the internal
  "NX999 - internal error" fallback for interpreter bugs. This means a
  genuine bug in the interpreter could be silently swallowed by a
  program's own `CATCH`. This is a real trade-off, not a fixed
  known-good design, and is worth revisiting later.
- File paths in `READ FILE`/`WRITE ... TO FILE`/etc. are resolved relative
  to the running script's directory (or the current working directory in
  the REPL) - there's no sandboxing or permission model.
- Map keys must be hashable (`NUMBER`, `TEXT`, `BOOLEAN`, `NOTHING`,
  `TUPLE`) - a `LIST` or `MAP` as a key is a clear `NX204` diagnostic, not
  a crash, but it does mean you can't key a map by an arbitrary list.
- There is no `{1, 2, 3}` set literal syntax - it would be ambiguous with
  an empty map literal `{}`. Sets are built with `SET_OF(list)` instead.
  This is a real design trade-off (documented in ROADMAP.md's Phase 3
  entry), not an oversight.
- **Type annotations are checked by `nex check` only - never enforced by
  `nex run` or the REPL.** `SET age AS NUMBER TO "fifteen"` runs exactly
  as it would with no annotation at all; the mismatch is only ever
  reported by the separate `nex check` step (or the IDE, which uses the
  same check). This is a deliberate scope decision (see
  docs/ROADMAP.md's Phase 3b entry), not a bug - NexLang remains
  dynamically typed and dynamically checked at runtime for now.
- The type checker's inference is deliberately narrow: it can work out
  the type of literals, simple arithmetic/comparisons, annotated
  variables/parameters, and calls to functions with a `RETURNS`
  annotation - anything else (an unannotated function's return value, a
  collection element, a builtin's result) is treated as "unknown" and
  never flagged, favoring missed mismatches over false alarms.
- `IMPORT` resolution in the checker is one level deep only - it reads an
  imported file's top-level names, but does not recursively resolve
  *that* file's own imports, so a name that only exists because of a
  nested import could still be falsely flagged as unknown.

## Why this work was prioritized this way

The project has been developed in the order its own roadmap laid out:
Phase 1 (bootstrap), Phase 2 "POWER" (functions/collections/errors/files),
Phase 3 "Collections" (maps/sets/tuples/slicing), and now Phase 3b "Type
Safety" (annotations + static analysis) - each session finished and
thoroughly tested one coherent milestone before starting the next, rather
than starting many half-finished subsystems at once. See docs/ROADMAP.md
for what's recommended next, in order (Phase 4 OOP is next up).

## Test suite breakdown (session-by-session additions)

| File | Tests | Focus |
|---|---|---|
| `tests/lexer/test_lexer_power.py` | 8 | New Phase 2 tokens |
| `tests/lexer/test_lexer_collections3.py` | 4 | Phase 3 tokens (`{`, `}`, `:`) |
| `tests/parser/test_parser_power.py` | 22 | New Phase 2 grammar, including error cases |
| `tests/parser/test_parser_collections3.py` | 12 | Map literals, slicing, `FOR EACH key, value` grammar |
| `tests/interpreter/test_functions.py` | 16 | Params, defaults, recursion, closures, scope |
| `tests/interpreter/test_collections.py` | 33 | Lists, indexing, loops, builtins |
| `tests/interpreter/test_collections3.py` | 29 | Maps, sets, tuples, slicing |
| `tests/interpreter/test_exceptions.py` | 11 | TRY/CATCH/FINALLY, nesting, interaction with functions/loops |
| `tests/interpreter/test_files.py` | 8 | File I/O, including error paths |
| `tests/interpreter/test_imports.py` | 6 | IMPORT, including circular/missing-file cases |
| `tests/interpreter/test_builtins.py` | 13 | Text/random/time builtins |
| `tests/repl/test_session_power.py` | 8 | FUNCTION/TRY in the REPL's block-tracking |
| New example conformance checks | 5 | `functions.nex`, `collections.nex`, `exceptions.nex`, `files.nex`, `maps_and_more.nex` |

Total: 297 passed, 0 failed, 1 skipped (the Tkinter GUI suite - needs a
real display, unavailable in this sandbox).

**Update (later session, IDE rebuild):** the Tkinter GUI referenced
above was replaced with NexIDE, a local HTML/CSS/JS web app - see
`docs/IDE_IDENTITY.md` and the CHANGELOG. Its old test file
(`tests/ide/test_app_gui.py`, the "1 skipped" above) was removed and
replaced with `tests/ide/test_web_server.py` (16 tests, all running
and passing headlessly - no display needed). Current total across the
whole suite: **304 passed, 0 failed, 0 skipped**
(`python3 tools/run_tests.py`).

**Update (this session, Phase 3b "Type Safety"):**

| File | Tests | Focus |
|---|---|---|
| `tests/parser/test_parser_types.py` | 12 | `AS TYPE`/`RETURNS TYPE` grammar, unions, error cases |
| `tests/semantic/test_analyzer.py` | 48 | Undefined names & scoping, duplicates, arg counts, type mismatches, unreachable code, IMPORT resolution |
| New CLI checks in `tests/cli/test_cli.py` | 4 | `nex check` surfacing NX401/NX405 and unreachable-code warnings |
| New example conformance check | 1 | `types.nex` |

Current total across the whole suite: **368 passed, 0 failed, 0 skipped**
(`python3 tools/run_tests.py`).
