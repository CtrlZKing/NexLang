# NexLang Roadmap

This roadmap is a contract with the truth: a feature is only marked "Done"
once it is implemented, tested, and documented against real behavior. Never
"Coming soon" masquerading as done.

## Phase 1 - Bootstrap (DONE)

- [x] Repository structure
- [x] Lexer (numbers, strings w/ escapes, identifiers, keywords, operators, comments)
- [x] Recursive-descent parser -> AST
- [x] Tree-walking interpreter
- [x] Diagnostic system (error codes, source snippets, suggestions, help topics)
- [x] Values: NUMBER (int/float), TEXT, BOOLEAN, NOTHING
- [x] Variables: `SET ... TO ...`, `=` reassignment, multiple assignment/swap
- [x] Operators: arithmetic, comparison (symbolic and `IS`/`IS AT LEAST`/etc.),
      logical (`AND`/`OR`/`NOT`), compound assignment, `INCREASE`/`DECREASE BY`
- [x] `SAY`, `ASK ... INTO ...`
- [x] String interpolation `"Hello {name}"`
- [x] `IF` / `ELSE IF` / `OTHERWISE` / `END`
- [x] `WHILE`, `REPEAT ... TIMES`, `REPEAT UNTIL`, `BREAK`, `CONTINUE`
- [x] CLI: `nex run`, `nex check`, `nex repl`, `nex ide`, `nex version`, `nex help`
- [x] Redesigned REPL: explicit `END`-to-submit interactive model, distinct
      from a script's own EOF-based termination, with persistent state and
      correct nested-block handling (see USER_GUIDE.md Section 9)
- [x] Graphical NexLang IDE (`nex` / `nex ide`): tabbed editor, syntax
      highlighting, smart indentation, file explorer, Output/Input panels,
      Run/Stop - see Phase 10 below, pulled forward and implemented early
- [x] Automated test suite (lexer, parser, interpreter, CLI, example programs,
      REPL session logic + end-to-end, script EOF semantics, IDE highlighting
      and run controller)
- [x] User-facing docs (README, USER_GUIDE, LANGUAGE reference, CHEATSHEET, GETTING_STARTED)

**Not yet included in Phase 1** (by design - these were Phase 2+, and most
are now delivered - see docs/PROJECT_STATUS.md for the current, accurate
state): classes, a bytecode VM, a package manager, formatter, linter,
testing framework, documentation generator, debugger, LSP, native
compilation, self-hosting.

## Phase 2 - Data & Functions (DONE - "POWER", v0.3.0)

Delivered:
- Functions: `FUNCTION name(params, param = default) ... RETURN ... END`,
  default parameters, closures, recursion. **Not yet delivered:** keyword
  arguments, variadic parameters, multiple return values, lambdas - moved
  to Phase 5 alongside pattern matching (see below).
- Collections: `LIST` literals + indexing (incl. negative/nested/string) +
  `ADD`/`REMOVE`/`SIZE OF`/`IS EMPTY`. `MAP`/`SET`/`TUPLE`/slicing were
  delivered next, in Phase 3 (see below); comprehensions are still planned.
- `FOR EACH item IN collection ... END` and `FOR i FROM a (DOWN) TO b ... END`.
- `TRY`/`CATCH`/`FINALLY` (pulled forward from Phase 3 - it fit naturally
  alongside functions and was needed for the file-I/O builtins' error paths).
- Modules: `IMPORT "file.nex"` (local-file, flat-namespace foundation only -
  `FROM ... IMPORT`, `IMPORT ... AS ...`, and stdlib-name imports like
  `IMPORT math` are still Phase 3+ work).
- Filesystem I/O and 18 standard-library builtins (text/collection
  aggregates/random/time) - see docs/CHANGELOG.md for the full list.

See docs/PROJECT_STATUS.md for the complete implemented/not-implemented
audit, and docs/CHANGELOG.md's `[0.3.0]` entry for details.

## Phase 3 - Collections & Type Safety (COLLECTIONS DONE, TYPE SAFETY NOT STARTED)

Delivered (collections):
- `MAP` literals (`{"a": 1}`) + indexing + `FOR EACH key, value IN map` +
  `KEYS()`/`VALUES()`.
- `SET` (via `SET_OF(list)` - no `{1,2,3}` literal, deliberately, to avoid
  ambiguity with an empty map `{}`) with `ADD`/`REMOVE`/`CONTAINS`/`FOR EACH`.
- `TUPLE` (via `TUPLE_OF(list)`), immutable, indexable.
- Slicing (`list[1:3]`, `[:3]`, `[3:]`, `[:]`) on LIST/TEXT/TUPLE.
- `SUM`/`AVERAGE`/`MAXIMUM`/`MINIMUM`/`SORTED`/`REVERSED`/`UNIQUE` widened
  to accept SET/TUPLE, not just LIST.

See docs/LANGUAGE.md's Maps/Sets/Tuples sections and
docs/PROJECT_STATUS.md for the full detail, including the exact reasoning
behind the `SET_OF`/`TUPLE_OF` constructor-function design (rather than
dedicated literal syntax) and the map-key-must-be-hashable rule.

**Not yet delivered** (comprehensions/full import syntax/set literal -
these were always separate from the type-safety work below; nothing
has built them yet):
- Comprehensions: `[x * x FOR x IN numbers]`
- `FROM ... IMPORT`, `IMPORT ... AS ...`, per-module namespacing at
  runtime (today's `IMPORT` is a flat global namespace at runtime - see
  docs/PROJECT_STATUS.md; `nex check`'s static analysis does resolve
  imported names for undefined-name checking purposes, which is a
  compile-time convenience, not runtime namespacing)
- A `{1, 2, 3}` set literal (would need a disambiguation rule against `{}`)

## Phase 3b - Type Safety (DONE)

Delivered:
- Type annotations: `SET x AS TYPE TO ...`, `FUNCTION f(x AS TYPE = default)`,
  `RETURNS TYPE`, and union types (`AS NUMBER OR TEXT`, with `OR NOTHING`
  as how "optional" is spelled - no separate optional syntax).
- A real static semantic analysis pass (`compiler/semantic/analyzer.py`),
  run by `nex check` (not `nex run`/the REPL - see below):
  undefined variables/functions (`NX401`/`NX402`, scope-aware, matching
  the interpreter's actual runtime scoping exactly), duplicate
  declarations (`NX403`), argument-count mismatches (`NX404`), type
  mismatches against annotations (`NX405`, via a small, deliberately
  conservative type inference - never a false positive, sometimes a
  missed real mismatch), and unreachable code (`NX406`, a warning, not
  a hard error).
- `IMPORT` resolution for the checker: it actually reads an imported
  file to see what names/signatures it provides, rather than treating
  every name from an import as unknown.

**Important scope decision, made deliberately**: this is *static*
checking only. `nex run` and the REPL never invoke this pass, so an
already-working program's *execution* behavior cannot change because
this phase shipped - only what `nex check` reports about it. NexLang
remains a dynamically-typed, dynamically-checked language at runtime;
annotations today are a linting tool, not an enforced contract. See
docs/USER_GUIDE.md Section 26 for the full reference and the reasoning.

**Not yet delivered:**
- Full type inference beyond the deliberately-small set of provably-safe
  cases (literals, simple arithmetic/comparisons, annotated
  variables/parameters, calls to functions with a `RETURNS` annotation)
- Enforcing annotations at runtime (an explicit, considered non-goal for
  now, not an oversight - see above)
- Generics

## Phase 4 - OOP (NOT STARTED)

- `CLASS`, properties, constructors, methods, inheritance, interfaces
- Enums, simple structs/data classes

## Phase 5 - Advanced Functions & Pattern Matching (NOT STARTED)

- Keyword arguments, variadic parameters, lambdas/anonymous functions,
  higher-order functions as first-class values
- `MATCH`/`CASE` pattern matching
- Generics

## Phase 6 - Standard Library (NOT STARTED)

- `math`, `random`, `statistics`, `text`, `collections`, `files`, `paths`,
  `json`, `csv`, `time`, `dates`, `regex`, `environment`, `system`, `logging`
- File IO with a clean, safe API (explicit read/write/append/delete/exists)
- Networking (`HTTP.GET` etc.) - secure by default (TLS verification on)
- Clear separation between "safe" stdlib calls and OS-level operations

## Phase 7 - Developer Tooling (NOT STARTED)

- `nex init` project scaffolding + `nex.toml` manifest
- `nex test` + `TEST "..." / EXPECT ... TO EQUAL ...` testing framework
- `nex format` formatter
- `nex lint` linter (unused vars, unreachable code, shadowing, unused imports, ...)
- `nex docs` documentation generator from doc-comments
- Local package installs from `nex.toml`; registry protocol *designed* but
  no live registry (see Phase 11)

## Phase 8 - Bytecode VM (NOT STARTED)

- Bytecode instruction set (`LOAD_CONST`, `ADD`, `JUMP_IF_FALSE`, `CALL`, ...)
- Stack-based VM as an alternative execution backend to the tree-walker
- Constant folding, dead-code elimination, basic caching

## Phase 9 - Debugger & LSP (NOT STARTED)

- `nex debug`: breakpoints, step/step-over/step-into, call stack, watches
- Language Server Protocol: diagnostics, autocomplete, go-to-definition,
  hover docs, rename, formatting-on-save
- VS Code extension using the LSP + a TextMate grammar for syntax highlighting

## Phase 10 - NexIDE (PARTIALLY DONE, pulled forward)

- [x] Standalone graphical editor (`nex` / `nex ide` - NexIDE, an
      HTML/CSS/JS app served by a local Python backend, opened in an
      app-mode browser window or installable as a PWA; originally
      Tkinter-based, rebuilt for real application identity - see
      docs/IDE_IDENTITY.md): tabbed `.nex` file editing, file/project
      explorer, line numbers, real-lexer syntax highlighting,
      real-indent-engine smart indentation, Undo/Redo, Find/Replace,
      Output panel, separate Input panel, Run/Stop, status bar, dark
      theme - see USER_GUIDE.md Section 10 and ARCHITECTURE.md's "Two
      front ends, one language core"
- [ ] Integrated debugger panel (depends on Phase 9's debugger existing)
- [ ] Docs panel, project-wide search, multi-root workspaces
- [ ] Editor built directly on the future Language Server (Phase 9) instead
      of its own regex/tokenizer-based highlighting and indentation, once
      that exists

## Phase 11 - Native Compilation, Self-Hosting, Registry (NOT STARTED / RESEARCH)

- Investigate native compilation (LLVM or a custom native backend)
- Rewrite the compiler front-end in NexLang itself (self-hosting) once the
  language has enough features to express it
- Real package registry service (today: local packages only, by design)
- Advanced optimization (JIT if it turns out to be worth the complexity)

---

### Versioning

NexLang follows semantic versioning starting at `0.1.0`. Before `1.0.0`,
breaking syntax changes may still happen between phases; each phase bump
will be called out here. After `1.0.0`, breaking changes require a new
language version marker (design TBD, tracked here when Phase 5+ needs it).
