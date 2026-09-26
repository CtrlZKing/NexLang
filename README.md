# NexLang

NexLang is a beginner-friendly, English-like general-purpose programming
language. It aims for Python-level versatility with much more readable
syntax and excellent, teachable error messages.

> **Status: Phase 3b of 11 ("Type Safety"), v0.3.0.** The core language
> (variables, arithmetic, `SAY`, `IF`/`OTHERWISE`, `WHILE`, `REPEAT`,
> `ASK`) plus Phase 2 "POWER" (user-defined functions with closures and
> recursion, list collections, `FOR EACH`/`FOR ... TO ...` loops,
> `TRY`/`CATCH`/`FINALLY`, a local-file `IMPORT` system, file I/O, and
> standard-library builtins) plus Phase 3 collections (maps, sets via
> `SET_OF`, tuples via `TUPLE_OF`, and slicing) plus Phase 3b type
> annotations and static semantic analysis (`nex check` now catches
> undefined names, duplicate declarations, argument-count and type
> mismatches, and unreachable code - see
> [docs/USER_GUIDE.md, Section 26](docs/USER_GUIDE.md#26-type-annotations--semantic-analysis))
> are all implemented, tested, and work today. So do the redesigned
> terminal REPL (`nex repl`) and the graphical **NexLang IDE** (`nex`).
> Classes, pattern matching, the bytecode VM, package manager, formatter,
> linter, and debugger are **not built yet** - see
> [docs/ROADMAP.md](docs/ROADMAP.md) for the honest, phase-by-phase plan
> and [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for the complete
> audit. Nothing in this repository is faked: unimplemented commands say so.

## Install

See [docs/USER_GUIDE.md#installation](docs/USER_GUIDE.md#1-installation-guide) for
the full Windows/macOS/Linux walkthrough. Quick version (any OS with Python
3.9+):

```bash
git clone <this-repo-url> nexlang
cd nexlang
pip install -e .
nex --version
```

Expected output:

```
NexLang 0.3.0
```

## Your first program

Create a file called `hello.nex`:

```
SAY "Hello, World!"
```

Run it:

```bash
nex hello.nex
```

Output:

```
Hello, World!
```

## Two ways to work with NexLang

```bash
nex repl        # terminal interactive mode - multiline, END to run
nex             # graphical NexLang IDE (a separate window)
```

See [docs/USER_GUIDE.md, Section 9](docs/USER_GUIDE.md#9-repl-guide) and
[Section 10](docs/USER_GUIDE.md#10-nexlang-ide-guide) for a full walkthrough
of each.

## Learn more

- [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) - a gentle first tutorial
- [docs/FIRST_30_MINUTES.md](docs/FIRST_30_MINUTES.md) - guided first half hour
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - the complete beginner manual
- [docs/LANGUAGE.md](docs/LANGUAGE.md) - language reference (what's implemented today)
- [docs/CHEATSHEET.md](docs/CHEATSHEET.md) - one-page syntax reference
- [docs/GRAMMAR.md](docs/GRAMMAR.md) - formal grammar
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - how the compiler/interpreter is built
- [docs/ROADMAP.md](docs/ROADMAP.md) - what's done, what's next, phase by phase
- [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) - the honest, current implemented/not-implemented audit
- [docs/CHANGELOG.md](docs/CHANGELOG.md) - what changed in each version

## Example

```
SET age TO 20

IF age IS AT LEAST 18 THEN
    SAY "You are an adult."
OTHERWISE
    SAY "You are a minor."
END

SET count TO 0
WHILE count IS BELOW 5
    SAY count
    count = count + 1
END
```

## Running the test suite

```bash
pip install pytest
pytest
```

The REPL's fancier terminal editing (history, Tab-to-indent) is optional:

```bash
pip install nexlang[repl]   # or: pip install prompt_toolkit
```

`nex repl` works fine without it, just with plainer line editing.

## License

MIT - see [LICENSE](LICENSE).
