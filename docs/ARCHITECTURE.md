# NexLang Architecture

## Pipeline

```
Source (.nex text)
    |
    v
Lexer            compiler/lexer/lexer.py       source -> List[Token]
    |
    v
Parser           compiler/parser/parser.py     tokens -> AST (Program)
    |
    v
Interpreter      compiler/interpreter/         AST -> executed program
                 interpreter.py

(nex check only)
    |
    v
Semantic         compiler/semantic/analyzer.py  AST -> undefined-name /
Analysis                                        duplicate-decl / arg-count /
                                                 type-mismatch / unreachable-
                                                 code diagnostics (Phase 3b)
```

Static semantic analysis (`compiler/semantic/analyzer.py`) landed in
Phase 3b: undefined variables/functions, duplicate declarations,
argument-count mismatches, type-annotation mismatches (via a small,
deliberately conservative inference), and unreachable code. It runs only
for `nex check` (and anything that calls `compiler.api.check_source`,
such as the IDE's live diagnostics) - never for `nex run` or the REPL,
so it can never change what an already-working program does when
executed, only what static analysis reports about it. NexLang remains
dynamically typed and dynamically checked at runtime; see
docs/USER_GUIDE.md Section 26 for the full reasoning.

An intermediate representation and a bytecode VM are still **planned**
(Phase 8) but do not exist yet - the interpreter still evaluates
directly off the AST.

## Why a tree-walking interpreter first?

The project rule is: **correct, readable, tested - then optimize.** A
hand-written recursive-descent parser plus a tree-walking interpreter is the
simplest robust way to get a real, working language with excellent error
messages. Every AST node also carries `line`/`column`, so every stage can
produce precise diagnostics without extra bookkeeping.

A bytecode VM (Phase 8) will be introduced later as an alternate execution
backend once the language surface is stable enough that redoing execution
semantics twice isn't wasted work.

## Module layout

```
nexlang/
    compiler/
        lexer/          tokens.py, lexer.py
        parser/         parser.py
        ast_nodes/       nodes.py         (dataclasses for every AST node)
        interpreter/     interpreter.py, runtime.py, builtins.py
        semantic/        analyzer.py      (Phase 3b static analysis, nex check only)
        errors/          errors.py        (NexError, SourceLocation, diagnostics)
        indent.py        shared smart-indentation engine (REPL + IDE)
        api.py           high-level parse_source/run_source/check_source
    cli/
        main.py          the `nex` command (run/check/repl/ide/version/help)
    repl/
        repl.py          `nex repl` terminal front end (line editing)
        session.py       END-vs-submit block/session state machine
    ide/
        highlight.py     tokenizer-based syntax-highlight span computation
        runner.py        subprocess-based program execution (Run/Stop/input)
        assets/          nexide.ico / nexide.png (app icon)
        web/
            server.py    local HTTP+SSE backend (file I/O, highlight,
                          indent, check, run/stop/input, all real - see
                          compiler/api.py, ide/highlight.py, ide/runner.py)
            launcher.py  starts the backend, opens an app-mode browser
                          window (or installable PWA) - see docs/IDE_IDENTITY.md
            static/      index.html, style.css, app.js, manifest.json, sw.js
        legacy_tkinter/  the earlier Tkinter GUI (app.py, editor.py, theme.py,
                          identity.py) - archived, not deleted; superseded by
                          ide/web/ (see docs/IDE_IDENTITY.md)
    tests/
        lexer/, parser/, interpreter/, cli/, language/, repl/, script/, ide/
    examples/            runnable .nex programs
    docs/                this documentation
```

`stdlib/`, `formatter/`, `linter/`, `debugger/` directories exist as
placeholders for Phases 4/5/7 and are currently empty except for a note - see
each directory's README stub, if present, or docs/ROADMAP.md.

## Two front ends, one language core

NexLang has exactly one lexer/parser/interpreter. Everything that runs
NexLang code - `nex run`, `nex repl`, and the graphical IDE's Run button -
goes through that same core (`compiler/api.py`), never a second
implementation:

```
                       compiler/api.py
                (tokenize -> parse -> interpret)
                    ^        ^         ^
                    |        |         |
              nex run   nex repl    NexLang IDE
             (cli/main)  (repl/repl)  (ide/app -> ide/runner,
                                       which shells out to
                                       `python -m cli.main run`)
```

The REPL and the script CLI intentionally use **different submission
rules** even though they share the same parser:

- A **script** (`nex run file.nex`) parses until end-of-file; a block's
  own `END` closes it and EOF simply ends the program (see
  `Parser.parse_program` / the `NX203` "Missing END" check for the error
  case where a block is left open).
- The **REPL** (`nex repl`) has no end-of-file to rely on, so
  `repl/session.py` re-tokenizes the buffer after every line typed and
  tracks how many blocks are still open, distinguishing an `END` that
  closes a block from an `END` that submits the whole interactive
  program. This logic is deliberately kept out of `repl/repl.py` (the
  terminal/line-editing layer) so it can be unit tested directly - see
  `tests/repl/test_session.py`.

The IDE (`ide/`) never re-implements the interpreter either: `ide/runner.py`
runs `python -m cli.main run <file>` as a subprocess and streams its
stdout/stdin, so a program behaves identically whether it's run from the
IDE or a terminal.

## The diagnostic system

`compiler/errors/errors.py` defines `NexError`, a single dataclass used by
every stage (lexer, parser, interpreter) to raise rich diagnostics:

- `code` - a stable identifier like `NX204`, so the same failure always
  produces the same code (useful for `nex help NX204`-style lookups later,
  and for the error guide in `docs/USER_GUIDE.md`).
- `title` - one-line human summary.
- `location` - exact file/line/column (+ underline length).
- `explanation` - why it happened.
- `suggestions` - concrete fixes, not vague hints.
- `source_line` - the raw offending line, rendered with a caret underline.
- `help_topic` - links the error to `nex help <topic>`.

This keeps error quality centralized instead of scattering ad hoc
`print()`/`raise Exception(str)` calls throughout the codebase, which is
what would make error quality erode over time as the language grows.

## Error code ranges (current)

| Range     | Stage         | Examples |
|-----------|---------------|----------|
| NX1xx     | Lexer         | NX101 unexpected character, NX102 unterminated string |
| NX2xx     | Parser        | NX201 expected token, NX203 missing END, NX204... |
| NX2xx     | Parser (cont) | *(NX204 in the parser range is reserved but currently only interpreter-side type errors use 204; see note below)* |
| NX3xx     | Runtime       | NX301 unknown variable |
| NX2xx     | Interpreter   | NX204 type mismatch, NX208 unpack error, NX209-212 loop/negation/division errors |
| NX9xx     | Internal      | NX999 internal error (should never surface to a user; if it does, it's a compiler bug) |

Note: error codes were assigned in implementation order rather than a
strict per-stage block; a future pass (tracked in ROADMAP Phase 5, when the
linter/docs generator need a stable machine-readable catalog) will
renumber these into clean non-overlapping ranges and generate
`docs/ERROR_CODES.md` automatically from the source so the two can never
drift apart.

## Testing strategy

- `tests/lexer/` - token-level unit tests
- `tests/parser/` - AST-shape unit tests
- `tests/interpreter/` - end-to-end program behavior (source in, output out)
- `tests/cli/` - the actual `nex` commands, including error paths
- `tests/language/` - runs every file in `examples/` and checks it behaves
  as documented, so examples can never silently rot
- `tests/script/` - script (.nex file) EOF semantics: no trailing `END`
  needed, unclosed blocks raise `NX203` with a location
- `tests/repl/` - the END-vs-submit state machine (`test_session.py`,
  pure logic) and full simulated-terminal sessions (`test_repl_e2e.py`)
- `tests/ide/` - syntax highlighting, the subprocess run controller, and
  `test_web_server.py`: the NexIDE web backend exercised over real HTTP
  requests + Server-Sent Events (file I/O, highlight, indent, check,
  and a full run/output/input/exit lifecycle) - no browser or display
  needed, since the backend is a plain Python HTTP server (see
  docs/IDE_IDENTITY.md)
- `tests/semantic/` - the Phase 3b static analyzer: undefined-name
  scoping (matching the interpreter's real runtime scoping exactly),
  duplicate declarations, argument-count and type-annotation mismatches,
  unreachable-code warnings, and `IMPORT` resolution
