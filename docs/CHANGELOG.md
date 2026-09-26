# Changelog

All notable changes to NexLang are recorded here. Dates are when the work
was done, not a formal release schedule (NexLang isn't published anywhere
yet).

## [3.0.0] "POWER" - Phase 3b "Type Safety"

- **Type annotations**: `SET x AS TYPE TO expr`, function parameters
  (`name AS TYPE`, with or without a default), `RETURNS TYPE` on function
  declarations, and union types (`AS NUMBER OR TEXT`) - `OR NOTHING` in a
  union is how "optional" is spelled, no separate syntax needed. New
  tokens: `AS`, `RETURNS`. Type names: `NUMBER`, `TEXT`, `BOOLEAN`,
  `NOTHING`, `LIST`, `MAP`, `SET`, `TUPLE`, `FUNCTION`, `ERROR`, `ANY`.
- **A real static semantic analyzer** (`compiler/semantic/analyzer.py`),
  run by `nex check` (not `nex run`/the REPL, deliberately - see
  docs/ROADMAP.md's Phase 3b entry for the reasoning):
  - Undefined variables/functions (`NX401`/`NX402`) - scope-aware,
    mirroring the interpreter's actual runtime scoping exactly (every IF
    branch, loop body, and function call gets its own child scope).
  - Duplicate declarations (`NX403`) - two parameters with the same name,
    or a name colliding with an existing FUNCTION in the same scope.
    Ordinary variable *reassignment* is never flagged.
  - Argument-count mismatches (`NX404`) - the static twin of the
    interpreter's existing `NX214` runtime check.
  - Type mismatches against annotations (`NX405`), via a small,
    deliberately conservative type inference - it only flags what it's
    certain about; anything it can't work out for sure is never flagged.
  - Unreachable code (`NX406`) - a warning, not a hard error; `nex check`
    still exits 0.
  - `IMPORT` resolution: the checker actually reads an imported file to
    see what it defines, rather than treating every name from an import
    as unknown; falls back to suppressing undefined-name checks
    (never guesses) if the import can't be resolved.
- `check_source()`'s return shape changed from `program` to `(program,
  warnings)`; verified against every real caller (CLI, tests, the web
  IDE's check endpoint) - none of them used the old return value, so this
  is not a breaking change in practice.
- Fixed `examples/exceptions.nex`, which previously demonstrated catching
  a runtime error by referencing a literally-undefined variable - the new
  static checker correctly flags that as a compile-time bug, so the
  example now demonstrates the same TRY/CATCH behavior with a genuinely
  runtime-only error (list index out of range) instead.
- 65 new tests (parser grammar, the analyzer itself, CLI integration).
- New example: `types.nex`.
- Updated `docs/USER_GUIDE.md`'s error-code catalog to be complete through
  `NX406` (it had drifted out of date since Phase 2), and added Section 26
  ("Type Annotations & Semantic Analysis").

**Scope note, stated plainly**: this is static checking only. An
already-working NexLang program's *execution* behavior cannot change
because this phase shipped - only what `nex check` reports about it.
NexLang remains dynamically typed and dynamically checked at runtime.

## [3.0.0] (web IDE) - NexIDE rebuilt as an HTML/CSS/JS app

Replaces the Tkinter identity patch below with a structural fix instead
of a cosmetic one - see `docs/IDE_IDENTITY.md` for the full writeup.
No language/lexer/parser/interpreter changes; all 304 tests pass.

- **Removed** the Tkinter GUI from active use (`ide/app.py`,
  `ide/editor.py`, `ide/theme.py`, `ide/identity.py` moved to
  `ide/legacy_tkinter/`, not deleted, for reference/rollback).
  `ide/highlight.py` was kept in active use - it has no Tkinter
  dependency and is reused by the new web IDE unchanged.
- **Added** `ide/web/`: a local Python backend
  (`ide/web/server.py`, stdlib `http.server` only, no new
  dependencies) serving a plain HTML/CSS/JS frontend
  (`ide/web/static/`). The backend exposes the real lexer (via
  `ide/highlight.py`), the real parser (via `compiler.api.check_source`),
  the real smart-indent engine (`compiler.indent`), and the existing
  subprocess runner (`ide/runner.py`) over a small JSON+SSE API - it
  does not re-implement any part of the language.
- **Added** `ide/web/launcher.py`: starts the backend and opens it in
  a Chromium `--app=` window (no address bar/tabs) when Chrome/Edge is
  found, falling back to the default browser otherwise.
- **Added** a Web App Manifest + minimal service worker
  (`ide/web/static/manifest.json`, `sw.js`) so NexIDE can be installed
  as a standalone PWA with its own icon/Start-Menu entry, fully
  independent of both Python's and the browser's identity - the most
  robust fix available for the original "taskbar shows Python" report.
- **New icon**: `ide/assets/nexide.ico`/`.png` and
  `ide/web/static/icons/icon-*.png` were regenerated from a
  user-provided logo image (an abstract blue "X" mark), replacing the
  earlier placeholder "N" badge icon.
- **Tests**: `tests/ide/test_app_gui.py` (Tkinter-specific) removed;
  `tests/ide/test_web_server.py` added (16 tests covering static
  serving, file I/O, highlighting, indent, syntax checking, and a full
  run/output/input/exit lifecycle over real HTTP + Server-Sent Events).
  `tests/cli/test_ide_command.py::test_ide_without_tkinter_reports_friendly_message`
  (tested a message that no longer applies, since Tkinter is no longer
  a dependency at all) was replaced with a test asserting `cmd_ide`
  calls the new web launcher.
- Added `tools/pytest_shim.py` fixture support (`@pytest.fixture`,
  generator-based setup/teardown) to run the new tests without network
  access to `pip install pytest` in this sandbox.
- **Explicitly NOT done**: the backend is still Python, and
  `ide/runner.py` still spawns a second `python.exe` subprocess to run
  programs (unchanged from before - see docs/IDE_IDENTITY.md, "What
  this does NOT change"). No bytecode/VM/self-hosting work was started.

## [3.0.0] (identity patch, superseded above) - Tkinter window identity

Stage A of the original NexIDE independence plan. Superseded by the
web-IDE rebuild above, but kept here for history; the code from this
patch now lives in `ide/legacy_tkinter/`.

- Added a real NexIDE icon (`ide/assets/nexide.ico`, `ide/assets/nexide.png`).
- Added `ide/identity.py`: sets the window/taskbar icon (`iconbitmap`/
  `iconphoto`) and, on Windows only, the process's Application User
  Model ID, so NexIDE's taskbar button is grouped/labeled as NexIDE
  instead of Python.
- `ide/app.py` now calls `apply_identity()` right after creating the
  root window; window title changed from "NexLang IDE" to "NexIDE"
  (cosmetic).
- `pyproject.toml` ships the new icon assets as package data.
- Added `tools/pytest_shim.py` + `tools/run_tests.py`: a small,
  dependency-free test runner (supporting `pytest.raises`,
  `pytest.mark.parametrize`, `pytest.mark.skipif`, `pytest.importorskip`,
  and the `capsys`/`tmp_path` fixtures this suite uses) because this
  sandbox has no network access to `pip install pytest`. All 288
  existing tests pass unmodified under it; switch back to real pytest
  with `pip install pytest && pytest tests/` whenever that's available
  - nothing in `tests/` needed to change.
- **Explicitly NOT done in this patch**: NexIDE still requires Python
  (it's a Tkinter app; `ide/runner.py` still spawns a second
  `python.exe` subprocess to run programs). No bytecode/VM/self-hosting
  work was started. See `docs/IDE_IDENTITY.md` for exactly what this
  patch does and does not fix, and `docs/PROJECT_STATUS.md` for the
  Stage B/C/D migration plan.

## [3.0.0] "POWER" - Phase 3 "Collections" addendum

Delivered on top of Phase 2 below, in the same 0.3.0 line (no version bump -
this rounds out the "POWER" collections story rather than starting a new one):

- **Maps**: `{"key": value, ...}` literals (multi-line and trailing-comma
  supported), reusing the existing indexing machinery for `person["name"]`,
  `FOR EACH key, value IN map`, `CONTAINS` checking keys, and new `KEYS()`/
  `VALUES()` builtins.
- **Sets**: `SET_OF(list)` (deliberately no `{1,2,3}` literal - it would be
  ambiguous with an empty map `{}`); `ADD`/`REMOVE`/`CONTAINS`/`FOR EACH`
  all extended to work on sets.
- **Tuples**: `TUPLE_OF(list)`, immutable (attempting `ADD`/`REMOVE`
  correctly raises `NX204`), indexable; `LIST_OF()` converts any of
  SET/TUPLE/MAP-keys/TEXT back into a mutable LIST.
- **Slicing**: `list[1:3]`, `[:3]`, `[3:]`, `[:]` on LIST, TEXT, and TUPLE.
- `SUM`/`AVERAGE`/`MAXIMUM`/`MINIMUM`/`SORTED`/`REVERSED`/`UNIQUE` widened
  to accept SET/TUPLE, not just LIST.
- New tokens: `{`, `}`, `:` (`LBRACE`/`RBRACE`/`COLON`).
- Fixed a `nex_repr` consistency bug caught during this work: tuples/sets
  containing TEXT were displayed with Python's quote marks (`('a', 'b')`
  looked right by accident, but `SET_OF(["x"])` showed `{'x'}` with a
  stray quote) instead of NexLang's own display convention. Now
  `TUPLE_OF(["a","b"])` displays as `(a, b)` and sets display consistently
  and deterministically (sorted for stable output).
- 45 new tests across lexer/parser/interpreter.
- New example: `maps_and_more.nex`.

See docs/LANGUAGE.md's Maps/Sets/Tuples sections for the full reference,
and docs/PROJECT_STATUS.md for the updated audit.

## [3.0.0] "POWER" - Phase 2

### Added

**Functions**
- `FUNCTION name(param, param = default) ... RETURN expr ... END` declarations.
- Calls via `name(args)` - the same syntax used for standard-library builtins.
- Default parameter values (re-evaluated fresh on every call - no
  Python-style shared-mutable-default surprises), recursion, local scope,
  and closures (a function defined inside another function captures that
  function's local variables).

**Collections**
- List literals: `[1, 2, 3]` (may span multiple lines).
- Indexing: `list[0]`, negative indices, chained indexing (`matrix[0][1]`),
  and string indexing.
- `ADD value TO list` / `REMOVE value FROM list` statements (mutate in place).
- `SIZE OF` and `IS EMPTY` work on LIST, TEXT, MAP, and SET.

**Loops**
- `FOR EACH item IN collection ... END`
- `FOR i FROM start TO end ... END` and `FOR i FROM start DOWN TO end ... END`
- `BREAK` / `CONTINUE` work in both new loop forms.

**Operators**
- `CONTAINS`, `STARTS WITH`, `ENDS WITH`
- `IS BETWEEN a AND b` (desugars to `>=` and `<=`, no new runtime semantics)
- `NULL` as a readable alias for `NOTHING`

**Error handling**
- `TRY ... CATCH error ... FINALLY ... END`, with a `CATCH`-only or
  `FINALLY`-only form both allowed (at least one is required).
- Caught errors bind to a `NexCaughtError` value - never a raw Python
  exception - with `.code`, `.title`, `.message`.

**Modules**
- `IMPORT "path/to/file.nex"` - a real, if currently flat-namespace, local
  file import system with circular-import protection.

**Filesystem**
- `READ FILE`, `WRITE ... TO FILE`, `APPEND ... TO FILE`, `DELETE FILE`,
  `FILE ... EXISTS`.

**Standard-library builtins** (called as `NAME(args)`, same convention as
user functions - see docs/ARCHITECTURE.md's "keywords for language,
stdlib for functionality" rule):
`COUNT`, `SUM`, `AVERAGE`, `MAXIMUM`, `MINIMUM`, `SORTED`, `REVERSED`,
`UNIQUE`, `UPPERCASE`, `LOWERCASE`, `TRIM`, `SPLIT`, `JOIN`, `REPLACE`,
`ROUND`, `RANDOM_BETWEEN`, `CURRENT_TIME`, `CURRENT_DATE`, `WAIT`.

**Tooling**
- REPL block-depth tracking, the shared indent engine, and IDE syntax
  highlighting all updated to understand every new keyword.
- 129 new tests across lexer, parser, interpreter, and REPL layers
  (see docs/PROJECT_STATUS.md for the full breakdown).
- 4 new example programs: `functions.nex`, `collections.nex`,
  `exceptions.nex`, `files.nex`.

### Fixed
- The REPL's startup banner had a version number hardcoded as a separate
  string literal, independent of `cli.main.VERSION` - it silently went
  stale on the last version bump. It now reads `VERSION` directly so
  there is a single source of truth.

### Known limitations / not yet implemented
See docs/ROADMAP.md and docs/PROJECT_STATUS.md for the full, honest list.
Notably: no maps/sets/tuples yet, no classes/objects, no static type
checking, no bytecode VM, no game/web/GUI frameworks, no keyword arguments
or variadic parameters, `IMPORT` is a flat global namespace (no per-module
scoping), and reserved words (including the new ones - `FUNCTION`, `ADD`,
`REMOVE`, `FILE`, etc.) cannot be used as variable or function names.

## [0.2.0]

Redesigned terminal REPL (explicit `END`-to-submit interactive model,
correctly distinguished from a script's own EOF-based termination) and the
graphical NexLang IDE (`nex` / `nex ide`): tabbed editor, syntax
highlighting, smart indentation, file explorer, Output/Input panels,
Run/Stop via the real interpreter (never a second implementation).

## [0.1.0]

Initial Phase 1 release: lexer, parser, AST, tree-walking interpreter,
CLI (`nex run`, `nex check`, `nex repl`, `nex version`, `nex help`),
variables, arithmetic, `SAY`, `ASK ... INTO`, `IF`/`OTHERWISE`, `WHILE`,
`REPEAT`, `BREAK`/`CONTINUE`, string interpolation, and NexLang-native
diagnostics (no raw Python tracebacks).
