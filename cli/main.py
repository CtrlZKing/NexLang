"""
NexLang CLI
============

The `nex` command. Phase 1 implements the commands that are actually
backed by working functionality:

    nex run <file.nex>       run a program
    nex <file.nex>           shorthand for `nex run`
    nex check <file.nex>     syntax-check a program without running it
    nex repl                 start the interactive REPL
    nex version / --version  print the version
    nex help [topic]         built-in help system

Commands described in the long-term design (build, install, test, format,
lint, docs, debug, ...) are NOT wired up yet. Rather than faking them,
`nex help` and the top-level parser clearly mark them as planned - see
docs/ROADMAP.md for the phase each one lands in.
"""

from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from compiler.api import run_source, check_source
from compiler.errors.errors import NexError

VERSION = "3.0.0"

PLANNED_COMMANDS = {
    "build": "Phase 6 (bytecode compilation / native output)",
    "install": "Phase 9 (package registry)",
    "remove": "Phase 9 (package registry)",
    "update": "Phase 9 (package registry)",
    "list": "Phase 9 (package registry)",
    "publish": "Phase 9 (package registry)",
    "init": "Phase 5 (project scaffolding)",
    "test": "Phase 5 (testing framework)",
    "format": "Phase 5 (formatter)",
    "lint": "Phase 5 (linter)",
    "docs": "Phase 5 (documentation generator)",
    "debug": "Phase 7 (debugger)",
}

HELP_TOPICS = {
    "syntax": "General NexLang syntax follows: KEYWORD ... END for blocks, one statement per line.",
    "variables": (
        "Variables are created with SET name TO value.\n"
        "  SET x TO 10\n"
        "  SET name TO \"Aditya\"\n"
        "  SET a, b TO 1, 2          # multiple assignment\n"
        "Re-assign an existing variable with `=`:\n"
        "  x = 20\n"
    ),
    "conditionals": (
        "IF condition THEN\n"
        "    ...\n"
        "ELSE IF other_condition THEN\n"
        "    ...\n"
        "OTHERWISE\n"
        "    ...\n"
        "END\n"
    ),
    "loops": (
        "REPEAT 10 TIMES ... END\n"
        "WHILE condition ... END\n"
        "REPEAT UNTIL condition ... END\n"
        "Use BREAK to exit a loop early and CONTINUE to skip to the next iteration.\n"
    ),
    "operators": (
        "Arithmetic: + - * / // % **\n"
        "Comparison: == != < > <= >=  (or IS / IS NOT / IS ABOVE / IS BELOW / IS AT LEAST / IS AT MOST)\n"
        "Logical: AND OR NOT\n"
        "Compound assignment: += -= *= /= //= %=  (or INCREASE x BY n / DECREASE x BY n)\n"
    ),
    "strings": (
        "Strings use double or single quotes: \"hello\" or 'hello'.\n"
        "Interpolate values with { }: SAY \"Hello {name}\"\n"
    ),
    "types": (
        "Built-in Phase 1 types: NUMBER, TEXT, BOOLEAN, NOTHING.\n"
        "Lists, maps, sets, tuples, and user-defined types arrive in Phase 2/3 (see docs/ROADMAP.md).\n"
    ),
    "blocks": "Every IF / WHILE / REPEAT block must be closed with END.",
    "input": "ASK \"question\" INTO variable   reads a line of text input from the user.",
    "say": "SAY expression   prints a value followed by a newline.",
}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    if not argv:
        # `nex` with no arguments launches the graphical NexLang IDE as a
        # separate window/application (see PART 3 of the project brief).
        # `nex repl` remains the terminal interactive mode.
        return cmd_ide()

    cmd = argv[0]

    if cmd in ("--version", "-v", "version"):
        print(f"NexLang {VERSION}")
        return 0

    if cmd in ("help", "--help", "-h"):
        return cmd_help(argv[1:])

    if cmd == "run":
        if len(argv) < 2:
            print("Usage: nex run <file.nex>")
            return 1
        return cmd_run(argv[1])

    if cmd == "check":
        if len(argv) < 2:
            print("Usage: nex check <file.nex>")
            return 1
        return cmd_check(argv[1])

    if cmd == "repl":
        from repl.repl import run_repl
        run_repl()
        return 0

    if cmd == "ide":
        return cmd_ide()

    if cmd in PLANNED_COMMANDS:
        phase = PLANNED_COMMANDS[cmd]
        print(f"`nex {cmd}` is planned but not implemented yet.")
        print(f"It is scheduled for {phase}.")
        print("See docs/ROADMAP.md for the full implementation plan.")
        return 2

    # `nex program.nex` shorthand
    if cmd.endswith(".nex"):
        return cmd_run(cmd)

    print(f"Unknown command: `{cmd}`")
    from compiler.errors.errors import closest_match
    known = ["run", "check", "repl", "ide", "version", "help"] + list(PLANNED_COMMANDS.keys())
    suggestion = closest_match(cmd, known)
    if suggestion:
        print(f"Did you mean: nex {suggestion}")
    print("Run `nex help` for a list of commands.")
    return 1


def cmd_run(path: str) -> int:
    if not os.path.isfile(path):
        print(f"File not found: {path}")
        return 1
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        run_source(source, filename=path)
        return 0
    except NexError as e:
        sys.stderr.write(e.render(use_color=sys.stderr.isatty()))
        return 1


def cmd_ide(path: str = None) -> int:
    """Launch NexIDE: a browser-based IDE (HTML/CSS/JS frontend, served
    by a local Python backend) sharing the exact same lexer/parser/
    interpreter as `nex run` and `nex repl` - see docs/IDE_IDENTITY.md
    for why this replaced the earlier Tkinter GUI, and docs/USER_GUIDE.md
    for usage."""
    from ide.web.launcher import launch_web_ide
    launch_web_ide(path)
    return 0


def cmd_check(path: str) -> int:
    if not os.path.isfile(path):
        print(f"File not found: {path}")
        return 1
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        _program, warnings = check_source(source, filename=path)
        for w in warnings:
            sys.stderr.write(w.render(use_color=sys.stderr.isatty()))
        suffix = f" ({len(warnings)} warning(s))" if warnings else ""
        print(f"No syntax errors found in {path}{suffix}")
        return 0
    except NexError as e:
        sys.stderr.write(e.render(use_color=sys.stderr.isatty()))
        return 1


def cmd_help(args) -> int:
    if not args:
        print_usage()
        return 0
    topic = args[0].lower()
    if topic in HELP_TOPICS:
        print(HELP_TOPICS[topic])
        return 0
    from compiler.errors.errors import closest_match
    suggestion = closest_match(topic, list(HELP_TOPICS.keys()))
    print(f"No help topic named `{args[0]}`.")
    if suggestion:
        print(f"Did you mean: nex help {suggestion}")
    print("Available topics: " + ", ".join(sorted(HELP_TOPICS.keys())))
    return 1


def print_usage():
    print(f"""NexLang {VERSION}

Usage:
    nex                     Launch the graphical NexLang IDE (separate window)
    nex ide                 Same as `nex` with no arguments
    nex run <file.nex>      Run a NexLang program
    nex <file.nex>          Shorthand for `nex run`
    nex check <file.nex>    Check a program for syntax errors without running it
    nex repl                Start the interactive REPL (terminal, multiline, END-to-run)
    nex version             Show the version
    nex help [topic]        Show help (try: nex help variables)

Planned (not yet implemented - see docs/ROADMAP.md):
    nex init, nex install, nex test, nex format, nex lint, nex docs,
    nex build, nex debug
""")


if __name__ == "__main__":
    sys.exit(main())
