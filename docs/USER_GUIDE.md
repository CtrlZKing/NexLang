# NexLang User Guide

Welcome! This guide assumes you have **never used NexLang before**. It walks
you from "nothing installed" to writing real, working `.nex` programs.

> This guide only documents features that exist right now (Phase 1). Where a
> feature is planned but not built, it's called out explicitly - never
> silently assumed.

---

## 1. Installation Guide

NexLang's bootstrap toolchain is written in Python. You need Python 3.9 or
newer installed. These instructions cover Windows 10/11 with PowerShell and
VS Code, since that's the most common beginner setup - notes for macOS/Linux
follow.

### Windows 10/11 (PowerShell)

**Step 1 - Check if Python is installed.**

Open PowerShell (press `Start`, type `PowerShell`, press Enter) and run:

```powershell
python --version
```

If you see something like `Python 3.11.4`, skip to Step 2. If you see an
error or a version older than 3.9, install Python from
[python.org/downloads](https://www.python.org/downloads/) - **during
installation, check the box "Add python.exe to PATH"** before clicking
Install.

**Step 2 - Get the NexLang source.**

If you have `git`:

```powershell
git clone <this-repo-url> nexlang
cd nexlang
```

If you don't have `git`, download the project as a ZIP, extract it, then in
PowerShell:

```powershell
cd path\to\extracted\nexlang
```

**Step 3 - Install NexLang.**

```powershell
pip install -e .
```

This registers the `nex` command using the project's `pyproject.toml`. The
`-e` (editable) flag means changes to the source take effect immediately
without reinstalling - useful since NexLang itself is still evolving.

**Step 4 - Verify installation.**

```powershell
nex --version
```

Expected output:

```
NexLang 0.3.0
```

If PowerShell says `nex is not recognized`, your Python "Scripts" folder
isn't on PATH. Fix:

1. Find where pip installed the script: run `pip show -f nexlang` and look
   for a path containing `Scripts\nex.exe` (or `nex-script.py`).
2. Add that `Scripts` folder to PATH: Start -> "Edit the system environment
   variables" -> Environment Variables -> under "User variables", select
   `Path` -> Edit -> New -> paste the folder path -> OK on every dialog.
3. Close and reopen PowerShell, then try `nex --version` again.

As a fallback that always works, no PATH setup required, run NexLang through
Python directly from inside the `nexlang` folder:

```powershell
python -m cli.main --version
```

Every `nex ...` command in this guide can be run as `python -m cli.main ...`
if you'd rather skip PATH configuration for now.

**Step 5 - Set up VS Code (optional but recommended).**

1. Install [VS Code](https://code.visualstudio.com/).
2. Open the `nexlang` folder: File -> Open Folder.
3. There is no NexLang syntax-highlighting extension yet (planned - Phase 7).
   `.nex` files will show as plain text for now; that doesn't affect running
   them.

### macOS / Linux

```bash
git clone <this-repo-url> nexlang
cd nexlang
pip3 install -e .
nex --version
```

If `nex` isn't found afterward, add `~/.local/bin` (or wherever `pip show -f
nexlang` says the script went) to your `PATH` in `~/.bashrc` / `~/.zshrc`, or
just use `python3 -m cli.main ...` instead.

---

## 2. Your First NexLang Program

**Step 1.** Create a new folder, e.g. `my_nex_programs`.

**Step 2.** Inside it, create a file named exactly `hello.nex` (the `.nex`
extension matters - it's how `nex` and future editor tooling recognize
NexLang files).

**Step 3.** Open `hello.nex` in any text editor (VS Code, Notepad, etc.) and
type:

```
SAY "Hello, World!"
```

**Step 4.** Save the file.

**Step 5.** Open a terminal in that folder (in VS Code: Terminal -> New
Terminal) and run:

```powershell
nex hello.nex
```

**Expected output:**

```
Hello, World!
```

### What just happened?

- `SAY` is a keyword that prints whatever comes after it.
- `"Hello, World!"` is a **TEXT** value (a string) - text values are always
  wrapped in quotes.
- `nex hello.nex` told the `nex` CLI to run your file. This is shorthand for
  `nex run hello.nex`.

---

## 3. Basic Program Structure

- Every NexLang program is a plain text file ending in `.nex`.
- **One statement per line.** NexLang doesn't use semicolons to separate
  statements - a newline ends a statement.
- **Blocks end with `END`.** Any `IF`, `WHILE`, or `REPEAT` you open must be
  closed with a matching `END` on its own line.
- **Indentation is for humans, not the parser.** NexLang currently doesn't
  enforce indentation (unlike Python) - `END` is what actually closes a
  block. Indenting consistently is still strongly encouraged for
  readability, and the planned formatter (Phase 5) will do this for you
  automatically.
- **Comments** start with `#` and run to the end of the line.
- **Keywords are case-insensitive** (`IF`, `if`, and `If` all work), but the
  convention - and what every example in this repo uses - is UPPERCASE for
  English-like keywords (`SET`, `IF`, `SAY`) so they visually stand out from
  your own variable names.
- **Variable names** are case-sensitive, must start with a letter or `_`,
  and may contain letters, digits, and `_` after that.
- **Blank lines** are allowed anywhere and are ignored.

---

## 4. Complete Language Reference

See [LANGUAGE.md](LANGUAGE.md) for the full reference of every implemented
feature (variables, operators, strings, conditionals, loops, etc.), each
with syntax and examples. This guide focuses on task-oriented "how do I..."
learning; LANGUAGE.md is the lookup reference.

---

## 5. Quick Reference / Cheat Sheet

See [CHEATSHEET.md](CHEATSHEET.md) for a one-page printable summary.

---

## 6. Examples

The [`examples/`](../examples) folder contains complete, runnable programs:

| File | Demonstrates |
|------|--------------|
| `hello.nex` | `SAY`, your first program |
| `variables.nex` | `SET`, reassignment, multiple assignment, swapping |
| `conditions.nex` | `IF` / `ELSE IF` / `OTHERWISE` |
| `loops.nex` | `REPEAT ... TIMES`, `WHILE`, `REPEAT UNTIL`, `BREAK`, `CONTINUE` |
| `calculator.nex` | arithmetic operators |
| `errors.nex` | what a NexLang error looks like (intentionally fails) |

Run any of them with `nex run examples/<name>.nex`. Every file except
`errors.nex` is verified by the automated test suite to run successfully
end-to-end (see `tests/language/test_examples.py`) - `errors.nex` is
verified to *fail with the expected diagnostic*, since that's its purpose.

More examples (functions, lists, dictionaries, classes, files, JSON,
modules) will be added as those features are implemented - see
[ROADMAP.md](ROADMAP.md).

---

## 7. "How Do I...?" Guide

**How do I print something?**
```
SAY "Hello!"
SAY 42
SAY x
```

**How do I get user input?**
```
ASK "What is your name?" INTO name
SAY "Hi {name}!"
```

**How do I create a variable?**
```
SET score TO 0
```

**How do I change a variable?**
```
SET score TO 0
score = score + 10
```

**How do I compare two numbers?**
```
IF score IS ABOVE 100 THEN
    SAY "High score!"
END
```

**How do I loop a fixed number of times?**
```
REPEAT 5 TIMES
    SAY "tick"
END
```

**How do I loop while a condition holds?**
```
SET x TO 0
WHILE x IS BELOW 5
    SAY x
    x = x + 1
END
```

**How do I stop a loop early?**
```
WHILE TRUE
    IF some_condition THEN
        BREAK
    END
END
```

**How do I skip to the next loop iteration?**
```
WHILE x IS BELOW 10
    x = x + 1
    IF x IS 5 THEN
        CONTINUE
    END
    SAY x
END
```

**How do I check a program for syntax errors without running it?**
```powershell
nex check myprogram.nex
```

**How do I use the REPL to experiment?**
```powershell
nex repl
```
See [Section 9](#9-repl-guide) below.

**How do I make a list / a function / a class / read a file / use JSON /
import another file / install a package / write tests / format my code /
debug my program / compile to an executable?**

These are **not implemented yet**. Each has a planned phase in
[ROADMAP.md](ROADMAP.md):

| Task | Planned phase |
|------|----------------|
| Lists, dicts, sets, tuples, `FOR EACH` | Phase 2 |
| Functions | Phase 2 |
| Modules / `IMPORT` | Phase 2 |
| Classes / objects | Phase 3 |
| `TRY`/`CATCH` error handling in code | Phase 3 |
| File IO, JSON, dates, regex, networking | Phase 4 |
| `nex test` testing framework | Phase 5 |
| `nex format` formatter | Phase 5 |
| `nex lint` linter | Phase 5 |
| `nex docs` documentation generator | Phase 5 |
| Package installs (`nex install`) | Phase 5 (local), Phase 9 (registry) |
| `nex debug` debugger | Phase 7 |
| Native executables (`nex build`) | Phase 6 (bytecode) / Phase 9 (native) |

---

## 8. CLI Manual

### `nex run <file.nex>`
Runs a NexLang program.
```powershell
nex run hello.nex
```
Exit code `0` on success, `1` if a NexLang error occurred (parse or runtime),
printed to stderr with full diagnostics.

### `nex <file.nex>`
Shorthand for `nex run <file.nex>`. Any argument ending in `.nex` is treated
this way.

### `nex check <file.nex>`
Parses the file **without running it** and reports syntax errors, if any -
and, since Phase 3b, also runs static semantic analysis (undefined
names, duplicate declarations, argument-count and type-annotation
mismatches, unreachable code). See [Section 26](#26-type-annotations--semantic-analysis)
for the full detail. Useful for quickly validating a file while editing.
```powershell
nex check hello.nex
# No syntax errors found in hello.nex
```

### `nex repl`
Starts the interactive REPL. See [Section 9](#9-repl-guide).

### `nex` (no arguments) / `nex ide`
Launches the graphical NexLang IDE in its own window. See
[Section 10](#10-nexlang-ide-guide).

### `nex version` / `nex --version`
Prints the installed NexLang version (currently `0.3.0`).

### `nex help [topic]`
Prints general usage, or (with a topic) focused help. Try:
```powershell
nex help
nex help variables
nex help loops
nex help operators
```
If you mistype a topic, NexLang suggests the closest match.

### Planned commands (not implemented - will print which phase adds them)
`nex build`, `nex init`, `nex install`, `nex remove`, `nex update`,
`nex list`, `nex publish`, `nex test`, `nex format`, `nex lint`, `nex docs`,
`nex debug`. Running any of these today prints an honest "planned, not
implemented yet" message rather than pretending to work.

---

## 9. REPL Guide

Start it:
```powershell
nex repl
```

### Interactive mode is different from script mode

This is the most important thing to understand about the REPL. In a
`.nex` **script**, a block's own `END` closes it, and reaching the end of
the file finishes the program - no extra `END` is needed (see
[Section 9.1](#91-why-interactive-mode-needs-an-explicit-end)). But the
REPL has no "end of file" to fall back on, so it uses an explicit rule
instead:

> **Pressing Enter never runs anything.** It just adds another line to
> the program you're writing. Typing a line that is *just* `END` tells
> the REPL "I'm done - run it."

```
> SAY "Hello"
>
> END
Hello
```

Nothing printed until that final `END` - not even after the first
`SAY "Hello"` line.

Variables persist across submissions, so you can build a session up
piece by piece:

```
> SET x TO 10
> END
> SAY x
> END
10
> SAY x * 2
> END
20
```

**Blocks work exactly like they do in scripts** - `IF`/`WHILE`/`REPEAT`
each need their own matching `END`. The difference only shows
up when the *last* `END` you type also happens to close the *last* open
block: that one `END` both closes the block and submits the program, so
you don't need to type a second one:

```
> SET x TO 10
> IF x IS AT LEAST 5 THEN
...     SAY "big"
... END
big
```

**Nested blocks** need one `END` per level, same as a script - only the
final one (the one that leaves nothing open) triggers execution:

```
> IF x IS 10 THEN
...     IF x IS AT LEAST 5 THEN
...         SAY "both"
...     END
... END
both
```

The first `END` above just closes the inner `IF`; the REPL keeps
prompting with `...` because the outer `IF` is still open. The second
`END` closes the outer `IF` *and*, since nothing is left open, runs the
program.

**`ASK` behaves exactly as you'd expect**: nothing happens while you're
still typing. Once you submit with `END`, the program runs top to
bottom, and `ASK "..." INTO x` prompts for input at that point, just
like it would in a script:

```
> ASK "WHAT IS YOUR NAME?" INTO name
> SAY "Hi {name}"
> END
WHAT IS YOUR NAME? Aditya
Hi Aditya
```

Type `exit` or `quit` (only while nothing is buffered) or press `Ctrl+D`
(Ctrl+Z then Enter on Windows) to leave the REPL.

### 9.1 Why interactive mode needs an explicit END

A script has a natural "I'm finished" signal that the terminal doesn't:
the end of the file. Requiring an explicit `END` at the prompt keeps the
same "every block closes with `END`" rule you already know from scripts,
while giving the REPL an unambiguous way to tell "close this block" apart
from "run what I've written" - see `repl/session.py` if you're curious
how that decision is actually made (it re-tokenizes what you've typed so
far and tracks how many blocks are still open, rather than a fragile
string check).

### 9.2 Editing at the prompt

By default the REPL uses Python's standard input handling, which already
gives you working Backspace, Delete, and the Left/Right/Home/End arrow
keys on both Windows and Unix terminals.

For a noticeably nicer experience - persistent history you can recall
with Up/Down across the whole session, Tab to indent, Shift+Tab to
dedent, and lines pre-filled with the indentation you probably want -
install the optional `prompt_toolkit` dependency:

```powershell
pip install nexlang[repl]
# or, working from a source checkout:
pip install prompt_toolkit
```

The REPL detects it automatically at startup; without it, you still get
a fully working (if slightly less convenient) session, and NexLang tells
you so with a one-line tip.

---

## 10. NexLang IDE Guide

Running `nex` with no arguments (or `nex ide` explicitly) launches
**NexIDE** - a real application window, not something that runs inside
CMD:

```powershell
nex
```

NexIDE is a local web app: a small Python backend runs on your machine
(only reachable from your machine - it binds to `127.0.0.1`), and the
interface itself is HTML/CSS/JS shown in a browser window. If Chrome or
Edge is installed, `nex` opens it in "app mode" - no address bar or
tabs, so it looks and behaves like a standalone desktop app. If neither
is found, it opens in your default browser instead, with that browser's
normal UI visible; see `docs/IDE_IDENTITY.md` for the full story
(including how to install NexIDE as a fully independent, permanently
iconed app via the in-app "Install NexIDE" button).

### What you get

- A **file explorer** on the left showing `.nex` files in the folder
  you've opened (use the folder icon, or File -> Open Folder, to change it).
- A **tabbed editor** in the center: multiple `.nex` files open at once,
  each with line numbers, NexLang-aware syntax highlighting (powered by
  the real lexer, not a guessed approximation), smart indentation
  (pressing Enter after `THEN`/`TIMES`/etc. indents the next line;
  typing `END`/`OTHERWISE` dedents), Undo/Redo, Find, and Replace.
- An **Output panel** and a separate **Input** field at the bottom.
- A **status bar** showing the current file and the last save/error
  message, plus a live diagnostic summary as you type.

### Your first program in the IDE

1. Run `nex`. A new, empty tab called `untitled.nex` opens - NexIDE
   never depends on the bundled examples; you start from a blank file.
2. Type a program:
   ```
   SET name TO "Aditya"

   SAY "Hello, {name}!"
   ```
3. **File -> Save** (or Ctrl+S), and choose where to save `main.nex`.
   NexIDE syntax-checks the file as you type; if something's wrong, the
   status bar's diagnostic summary explains why.
4. Press **Run** (or F5). The Output panel shows:
   ```
   Hello, Aditya!
   ```
5. Change the code and press **Run** again - no need to re-save first,
   NexIDE saves automatically before running.

### Source code, output, and input are kept separate

This matters especially for `ASK`. Typing `ASK "WHAT IS YOUR NAME?" INTO x`
into the editor does **nothing** by itself - the editor is only editing
text. The program only runs when you press **Run**. Once it does, and
execution reaches the `ASK`, the question appears in the **Output**
panel and the **Input** box becomes active:

```
Output:                          Input:
WHAT IS YOUR NAME?                [ Aditya            ] <- press Enter
Hello, Aditya!
```

Press **Stop** at any time to end a running program immediately (useful
for an infinite `REPEAT UNTIL`/`WHILE` loop while you're debugging one).

### Architecture note

NexIDE is a frontend, not a second implementation of NexLang: pressing
Run saves your file and runs it through the exact same `nex run`
command-line path (lexer -> parser -> AST -> interpreter) that the CLI
uses, in a subprocess, so what runs in NexIDE always matches what
running the file from a terminal would do. Syntax highlighting and
error-checking in the editor also call the real lexer/parser directly
(over a local API) rather than a separate, hand-written approximation.
See `docs/IDE_IDENTITY.md` for the full backend architecture.

---

## 11. Error Guide

Every NexLang error has this shape:

```
ERROR <CODE> - <one-line summary>

 <line> | <the offending source line>
          ^^^^ (underline pointing at the problem)

<why this happened, in plain language>

Possible fixes:

    <concrete suggestion>

Location:
    <file>:<line>:<column>

Learn more:
    nex help <topic>
```

### Current error codes

Numbering isn't strictly by stage (some runtime checks share the `NX2xx`
range with parser errors, for historical reasons) - but `NX1xx` is always
the lexer, `NX3xx`/`NX2xx` are mostly parser/runtime, and `NX4xx` is
always the *static* semantic-analysis pass (`nex check` only - see
[Section 26, "Type Annotations & Semantic Analysis"](#26-type-annotations--semantic-analysis)).

| Code | Meaning | Typical fix |
|------|---------|--------------|
| `NX101` | Unexpected character | Remove/replace the invalid character |
| `NX102` | Unterminated string literal | Add the missing closing quote |
| `NX201` | Expected a specific token (e.g. `TO`, `THEN`) | Add the missing keyword/symbol |
| `NX202` | Unexpected extra input on a line | Put the extra code on its own line |
| `NX203` | Missing `END` | Add `END` to close the block |
| `NX204` | Incompatible types for an operator, or wrong type for a builtin/statement argument (e.g. NUMBER + TEXT, `ADD` to a non-LIST) | Convert types, or use string interpolation instead |
| `NX205` | Mismatched multiple assignment (wrong number of values) | Match the number of names and values |
| `NX206` | Incomplete `IS AT ...` comparison | Use `IS AT LEAST` or `IS AT MOST` |
| `NX207` | Expected an expression | Provide a value, variable, or `(...)` |
| `NX208` | Cannot unpack a value into multiple names | Use a value with the right number of items |
| `NX209` | `REPEAT ... TIMES`/`FOR ... FROM ... TO ...` bound isn't a number | Use a numeric expression |
| `NX210` | Unclosed `{` in an interpolated string | Add the missing `}` |
| `NX211` | Tried to negate a non-number | Only apply unary `-` to NUMBERs |
| `NX212` | Division by zero | Check the divisor before dividing |
| `NX213` | `TRY` with neither `CATCH` nor `FINALLY` | Add at least one |
| `NX214` | Wrong number of arguments to a `FUNCTION` call (runtime) | Match the parameter list, or add defaults |
| `NX215` | `AVERAGE`/`MAXIMUM`/`MINIMUM` on an empty LIST | Check the list isn't empty first |
| `NX216` | `REMOVE`d value isn't in the LIST/SET | Check membership with `CONTAINS` first |
| `NX217` | `IMPORT` couldn't find the file | Check the path, relative to the importing file |
| `NX218` | `IMPORT` couldn't read the file | Check file permissions/encoding |
| `NX219` | `WRITE`/`APPEND ... TO FILE` failed | Check the path and file permissions |
| `NX220` | `DELETE FILE` failed (often: file doesn't exist) | Check with `FILE ... EXISTS` first |
| `NX221` | List/tuple index out of range, or MAP key not found | Check `SIZE OF`/`CONTAINS` first |
| `NX222` | Called something that isn't a `FUNCTION` (runtime) | Check the name isn't shadowed by a variable |
| `NX223` | `READ FILE` couldn't find or read the file | Check the path with `FILE ... EXISTS` first |
| `NX224` | Unknown type name in an `AS`/`RETURNS` annotation | Use one of NUMBER/TEXT/BOOLEAN/NOTHING/LIST/MAP/SET/TUPLE/FUNCTION/ERROR/ANY |
| `NX225` | `AS TYPE` used with multiple assignment (`SET a, b AS ... TO ...`) | Annotate one name at a time |
| `NX301` | Unknown variable (used before `SET`, or misspelled) - runtime | Check spelling / add a `SET` |
| `NX401` | Unknown variable - **static** (`nex check` only) | Same as NX301, found before running |
| `NX402` | Unknown function, or calling a non-function - **static** | Same as NX222/NX301-for-calls, found before running |
| `NX403` | Duplicate declaration (two params with the same name; redeclaring a FUNCTION/variable name already in use in the same scope) - **static** | Rename one of them |
| `NX404` | Argument-count mismatch - **static** version of NX214 | Match the parameter list, or add defaults |
| `NX405` | Type mismatch against an `AS`/`RETURNS` annotation - **static** | Use a compatible value, or adjust the annotation |
| `NX406` | Unreachable code (a **warning**, not a failure - `nex check` still exits 0) | Remove the dead code, or check your control flow |
| `NX999` | Internal error | This is a NexLang bug - please report it |

This table is generated to match `compiler/errors/errors.py` usages as of
Phase 3b. If you find a mismatch, the code is the source of truth.

### Example walkthrough

```
SET total TO 10
SAY total + "hello"
```
produces:
```
ERROR NX204 — Cannot add NUMBER and TEXT

 2 | SAY total + "hello"
               ^

`NUMBER` is not compatible with `TEXT` for the `+` operator.

Possible fixes:

    total + 5             # add two numbers together
    SAY "{total} hello"    # interpolate the number into a string instead

Location:
    errors.nex:2:11

Learn more:
    nex help types
```

The fix: either add two numbers together, or use string interpolation
(`"{total} hello"`) if you meant to combine text and a number into a
message.

*(If you're personally troubleshooting a program and getting stuck on
errors, that's completely normal while learning a new language - work
through them one at a time, starting from the first error in your file.)*

---

## 12. Debugging Guide

A real interactive debugger (`nex debug`, breakpoints, stepping, watches,
call stack inspection) is **planned for Phase 7** and does not exist yet.

Until then, the most effective debugging techniques in NexLang are:

1. **Add `SAY` statements** to print variable values at key points:
   ```
   SAY "DEBUG: x is {x}"
   ```
2. **Use `nex check`** first to catch syntax errors before running.
3. **Read the error's `Location:` line carefully** - it gives you the exact
   file, line, and column.
4. **Narrow the problem**: comment out later code (with `#`) and re-run to
   find which line introduces a bug.

---

## 13. Project Guide

`nex init` (Phase 5) will scaffold a full project layout (`src/`, `tests/`,
`docs/`, `nex.toml`). It is **not implemented yet**. Today, a NexLang
"project" is simply a folder of `.nex` files you organize yourself; there is
no multi-file `IMPORT` system until Phase 2, so for now each `.nex` file
runs independently.

---

## 14. Package Management

`nex install`, `nex remove`, `nex update`, and `nex list` are **not
implemented**. There is no package registry yet, local or remote. This is
intentional rather than an oversight - see ROADMAP.md Phase 5 (local
packages) and Phase 9 (a real registry). Do not expect `nex install
<anything>` to work; it will tell you honestly that it's planned.

---

## 15. Editor / VS Code Guide

The graphical **NexLang IDE** (`nex` or `nex ide` - see
[Section 10](#10-nexlang-ide-guide)) is the recommended editor today: it
already has NexLang-aware syntax highlighting, smart indentation, and
inline syntax-error highlighting, none of which plain-text editors give
you.

If you'd rather work in VS Code:

- Open the `nexlang` project folder in VS Code as normal.
- There is currently **no VS Code syntax highlighting extension** for
  `.nex` files (planned Phase 7, alongside a full Language Server).
  `.nex` files render as plain text there.
- Run programs using the integrated terminal: `` Ctrl+` `` to open it,
  then `nex run yourfile.nex`.
- Autocomplete, inline error highlighting *inside VS Code*, and a
  formatting command are all **planned** alongside the LSP in Phase 7 -
  the NexLang IDE's indentation engine (`compiler/indent.py`) was written
  to be reusable by that future LSP/extension rather than thrown away.

---

## 16. Complete Beginner Course

Each lesson: explanation, example, a small exercise, and the expected
result. Try each exercise in `nex repl` or a scratch `.nex` file before
checking the answer.

### Lesson 1 - Hello World
`SAY "Hello, World!"` prints text.
**Exercise:** Make NexLang print your name.
**Expected result:** your name printed to the screen.

### Lesson 2 - Variables
`SET x TO 10` creates a variable. `x = 20` changes it.
**Exercise:** Create a variable `favorite_number` and print it.
**Expected result:** your chosen number printed.

### Lesson 3 - Input/Output
`ASK "question" INTO variable` reads input; `SAY` prints output.
**Exercise:** Ask the user's name and greet them by name.
**Expected result:** e.g. typing `Sam` prints `Hi Sam!`.

### Lesson 4 - Conditions
`IF ... THEN ... OTHERWISE ... END` branches.
**Exercise:** Print `"even"` or `"odd"` for a number using `% 2`.
**Expected result:** correct parity printed.

### Lesson 5 - Loops
`REPEAT n TIMES`, `WHILE`, `REPEAT UNTIL`.
**Exercise:** Print the numbers 1 through 10 using `WHILE`.
**Expected result:** ten lines, `1` through `10`.

### Lesson 6 - Lists *(planned - Phase 2)*
Not usable yet; this lesson will be filled in once lists exist.

### Lesson 7 - Functions *(planned - Phase 2)*
Not usable yet.

### Lesson 8 - Modules *(planned - Phase 2)*
Not usable yet.

### Lesson 9 - Classes *(planned - Phase 3)*
Not usable yet.

### Lesson 10 - Files *(planned - Phase 4)*
Not usable yet.

### Lesson 11 - Error handling *(`TRY`/`CATCH` planned - Phase 3)*
Today, errors always stop the program; see Section 11 for reading them.

### Lesson 12 - Projects *(planned - Phase 5)*
Not usable yet.

### Lesson 13 - Testing *(planned - Phase 5)*
Not usable yet; NexLang's *own* codebase is tested with `pytest` in the
meantime (see the main README).

### Lesson 14 - Advanced features
Tracked feature-by-feature in [ROADMAP.md](ROADMAP.md).

---

## 17. First Project Tutorial - Number Range Printer

A small complete project using only what Phase 1 supports: a program that
asks for a starting number and counts up five times.

```
ASK "Pick a starting number: " INTO start_text
SET start TO 0
SET counter TO start
SET i TO 0

REPEAT 5 TIMES
    SAY counter
    counter = counter + 1
    i = i + 1
END

SAY "Done counting!"
```

Note: since `ASK` returns TEXT and NexLang doesn't yet have a text-to-number
converter (planned Phase 4), this tutorial program starts counting from a
fixed variable rather than the raw user input. This limitation is called
out here on purpose - see [LANGUAGE.md](LANGUAGE.md) for current `ASK`
behavior, and try `examples/loops.nex` for a version that uses live
variables you set directly in code.

Run it:
```powershell
nex run count.nex
```

---

## 18. Language Cheat Sheet

See [CHEATSHEET.md](CHEATSHEET.md).

---

## 19. Command Discovery

```powershell
nex help
nex help SET
nex help IF
```

`nex help <topic>` currently covers: `syntax`, `variables`, `conditionals`,
`loops`, `operators`, `strings`, `types`, `blocks`, `input`, `say`. Run `nex
help` with no arguments to see the exact list, since it's generated from the
same source the CLI itself uses (`cli/main.py:HELP_TOPICS`), so it can never
drift from what the tool actually says.

---

## 20. Self-Documenting Error Suggestions

When you misspell a variable name, NexLang suggests the closest existing
name:

```
ERROR NX301 — Unknown variable

`usernme` has not been defined before this point.

Possible fixes:

    Did you mean `username`?
```

Command-name typo suggestions work the same way at the CLI level (e.g.
`nex rn` suggests `nex run`).

---

## 21. Documentation Accuracy

Every example in this guide is either directly copied from a file in
`examples/` (checked by the automated test suite) or has been run manually
against the current interpreter while writing this document. If you find
documentation that doesn't match actual behavior, that's a bug - the
project rule is that docs must always describe the real implementation, not
aspirational syntax.

---

## 22-23. Quickstart / First 30 Minutes

See the [README](../README.md) Quickstart and
[FIRST_30_MINUTES.md](FIRST_30_MINUTES.md).

---

## 24. Why English-Like Syntax?

NexLang favors phrases like `SET x TO 10` and `IF age IS AT LEAST 18 THEN`
over `x = 10` and `if age >= 18:` because:

- **Readability for beginners.** `IS AT LEAST` reads the way you'd say it
  out loud; `>=` requires learning an unfamiliar symbol first.
- **Fewer "what does this symbol mean?" moments** early on, when every
  ounce of working memory should go toward learning programming concepts,
  not syntax trivia.
- **Errors can talk back in the same vocabulary** used to write the code,
  which is why NexLang's diagnostics say things like "Cannot add NUMBER and
  TEXT" instead of a raw stack trace.

At the same time, NexLang keeps **conventional symbols where they're
already universally understood and more concise**: `+ - * / == != < >`, `=`
for reassignment, `+=`/`-=` for compound assignment. Forcing "INCREASE x BY
1" as the *only* way to increment would make experienced-programmer code
needlessly verbose, so both forms exist side by side - use whichever reads
better for the moment.

---

## 25. Known Limitations (as of Phase 3b)

Documented honestly, not hidden:

- No classes/objects, enums, or pattern matching (`MATCH`) yet.
- No maps/sets/tuples *literal* syntax beyond `{...}` for maps - sets and
  tuples are built with `SET_OF(...)`/`TUPLE_OF(...)`, not their own
  bracket syntax (see docs/LANGUAGE.md's Sets section for why).
- No comprehensions, generators, lambdas, keyword arguments, or variadic
  parameters.
- `IMPORT` is a flat global namespace - no `module.name` access.
- `ASK` only returns TEXT; there's no built-in string-to-number conversion
  yet.
- The static semantic-analysis pass (Section 26) only runs for `nex
  check`, not `nex run` or the REPL - an already-working program's
  behavior when *run* cannot change based on this pass existing.
- Type checking is deliberately conservative (see Section 26) - it will
  never wrongly flag correct code, but it also can't catch every mistake;
  most expressions without an explicit `AS`/`RETURNS` annotation aren't
  type-checked at all.
- No formatter/linter/tests-runner/docs-generator/debugger/package manager yet.
- No bytecode VM - this is a tree-walking interpreter throughout.
- Windows/macOS/Linux are all expected to work equally well since the
  implementation is pure Python with no OS-specific code, but only manual
  testing has been done so far, not an automated cross-platform CI matrix.

See [docs/PROJECT_STATUS.md](../docs/PROJECT_STATUS.md) for the complete,
up-to-date audit and [docs/ROADMAP.md](../docs/ROADMAP.md) for what's next.

---

## 26. Type Annotations & Semantic Analysis

Phase 3b adds two related things: a way to *say* what type a variable,
parameter, or function return value should be, and a static pass -
`nex check` - that verifies those claims (and a few other classes of
mistake) *before* the program runs at all.

### Writing type annotations

```
SET age AS NUMBER TO 15
SET nickname AS TEXT OR NOTHING TO NULL     # a union type - "optional TEXT"

FUNCTION average_of(a AS NUMBER, b AS NUMBER) RETURNS NUMBER
    RETURN (a + b) / 2
END
```

- `AS TYPE` annotates a single `SET` (not `SET a, b AS ... TO ...` -
  that's ambiguous and a parse error, `NX225`).
- `AS TYPE` also annotates a function parameter, optionally alongside a
  default: `FUNCTION f(x AS NUMBER = 0)`.
- `RETURNS TYPE` annotates a function's return value.
- A union is written `TYPE1 OR TYPE2 OR ...` - and `NOTHING` in a union
  is how you spell "optional": `AS NUMBER OR NOTHING`. There's no
  separate `?` or "optional" keyword.
- Valid type names: `NUMBER`, `TEXT`, `BOOLEAN`, `NOTHING`, `LIST`, `MAP`,
  `SET`, `TUPLE`, `FUNCTION`, `ERROR`, and `ANY` (which accepts anything -
  useful when you want to document a parameter's shape without
  constraining it yet).

**Annotations are optional everywhere.** Nothing about existing,
unannotated NexLang code changes - `SET x TO 5` remains completely valid
with no type checking applied to it at all.

### What `nex check` verifies

Where `nex check` used to only parse the file, it now also runs semantic
analysis by default, checking:

- **Undefined names** (`NX401`/`NX402`) - a variable or function used
  before it's ever declared anywhere it could be seen from that point,
  with the same scoping rules the interpreter actually uses (an `IF`
  branch's `SET` doesn't leak outside the `IF`, a function's parameters
  aren't visible outside it, and so on).
- **Duplicate declarations** (`NX403`) - two parameters with the same
  name, or a `FUNCTION`/`SET` name colliding with an existing `FUNCTION`
  in the same scope. Ordinary reassignment (`SET x TO 1` then later `SET
  x TO 2`) is never flagged - that's completely normal.
- **Argument-count mismatches** (`NX404`) for calls to a `FUNCTION` whose
  declaration is visible - the same check the interpreter makes at call
  time (`NX214`), just found before the program runs.
- **Type mismatches** (`NX405`) against explicit annotations, using a
  small, deliberately conservative type inference: if the type of an
  expression can't be worked out for certain (e.g. it's the result of
  calling a function with no `RETURNS` annotation), it is never flagged.
  Missing a real mismatch is preferred over a false alarm on correct code.
- **Unreachable code** (`NX406`) - collected as a *warning* (`nex check`
  still exits `0`), not a hard error, since dead code is a smell rather
  than necessarily a bug.

`IMPORT "file.nex"` is resolved statically too - the checker actually
reads the imported file to see what names it defines, so `nex check`
doesn't false-flag a function or variable that only exists because of an
import. If the import can't be resolved (missing file, dynamic path
computed at runtime, etc.), the checker falls back to not flagging
undefined names for the rest of the program rather than guessing.

```
$ nex check examples/types.nex
No syntax errors found in examples/types.nex
```

```
$ nex check bad.nex
ERROR NX405 — Type mismatch

 1 | SET age AS NUMBER TO "fifteen"
                          ^^^^^^^^^

`age` is annotated `AS NUMBER` but this value is TEXT.

Possible fixes:

    Use a NUMBER value, or change the annotation.

Location:
    bad.nex:1:15
```

### What `nex run` does NOT do differently

`nex run` and the REPL never run this pass - only `nex check` does. This
is deliberate: a program that worked before Phase 3b keeps working
exactly the same way when run, whether or not it has annotations, and
whether or not it would pass `nex check` cleanly. Type annotations today
are a *linting* tool, not an enforced runtime contract - see
docs/ROADMAP.md for whether/when that might change.

See docs/LANGUAGE.md's "Types" section for the full type-name reference,
and `compiler/semantic/analyzer.py` for the implementation, if you want
to see exactly how the inference and scoping work.
