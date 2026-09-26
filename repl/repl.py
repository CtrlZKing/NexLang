"""
NexLang Interactive REPL
=========================

`nex repl` starts an interactive session in the terminal. This is
INTENTIONALLY different from running a `.nex` script (see
`docs/USER_GUIDE.md` -> "Interactive mode vs. script mode"):

    * In a script, a block's own `END` closes it, and reaching the end of
      the file finishes the program - no extra `END` needed.
    * At the interactive prompt there is no "end of file" to fall back
      on, so NexLang uses an explicit signal instead: pressing Enter
      *never* runs anything by itself, it just adds another line to the
      program you're building. Typing a line that is just `END` (and
      isn't needed to close a block you opened) tells the REPL you're
      done, and it runs everything you've typed:

        > SAY "Hello"
        >
        > END
        Hello

        > SET x TO 10
        > IF x IS 10 THEN
        >     SAY "yes"
        > END
        yes

    * Nested blocks work the same way scripts do - each `END` closes the
      innermost still-open block - the *last* one just also happens to
      finish the submission once nothing is left open:

        > IF x IS 10 THEN
        >     IF y IS 20 THEN
        >         SAY "both"
        >     END
        >     END
        both

The actual "is this END closing a block or submitting the program?"
decision lives in `repl/session.py` (`ReplSession`), which is plain,
terminal-independent logic and has its own unit tests
(`tests/repl/test_session.py`). This module is just the terminal front
end: reading keystrokes, editing, history, and calling into that engine.
"""

from __future__ import annotations

import sys

from compiler.lexer.lexer import tokenize
from compiler.parser.parser import Parser
from compiler.interpreter.interpreter import Interpreter
from compiler.errors.errors import NexError
from compiler import indent as indent_engine
from repl.session import ReplSession

def _current_version() -> str:
    # Single source of truth: cli.main.VERSION. Imported lazily (rather
    # than at module load time) to avoid any risk of a circular import,
    # since cli.main itself imports repl.repl to implement `nex repl`.
    from cli.main import VERSION
    return VERSION

BANNER_TEMPLATE = r"""
    ███╗   ██╗███████╗██╗  ██╗██╗       █████╗ ███╗   ██╗ ██████╗
    ████╗  ██║██╔════╝╚██╗██╔╝██║      ██╔══██╗████╗  ██║██╔════╝
    ██╔██╗ ██║█████╗   ╚███╔╝ ██║      ███████║██╔██╗ ██║██║  ███╗
    ██║╚██╗██║██╔══╝   ██╔██╗ ██║      ██╔══██║██║╚██╗██║██║   ██║
    ██║ ╚████║███████╗██╔╝ ██╗███████╗ ██║  ██║██║ ╚████║╚██████╔╝
    ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚══════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝

    NexLang
    Modern. Readable. Powerful.

    NexLang version {version}
    Type HELP for help.
    Type EXIT to leave.
"""


def _make_line_reader():
    """Return (read_line, backend_name).

    `read_line(prompt, default_text) -> str` reads one line of input.

    Preferred backend: prompt_toolkit - real cross-platform (Windows,
    macOS, Linux) line editing with working Backspace/Delete/Left/Right/
    Home/End, a persistent history navigable with Up/Down, Tab-to-indent,
    Shift+Tab-to-dedent, and the ability to pre-fill a line with
    suggested indentation the user can still edit or delete.

    Fallback backend: the standard library `input()`. This still gets
    normal Backspace/arrow-key editing because that's handled by the
    operating system's own line discipline (the Windows console and Unix
    TTYs both do this even without readline) - what's missing without
    prompt_toolkit is cross-line history and pre-filled indentation,
    which the fallback documents via a startup tip rather than faking.
    See docs/USER_GUIDE.md for details.
    """
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.key_binding import KeyBindings

        bindings = KeyBindings()

        @bindings.add("tab")
        def _(event):
            event.current_buffer.insert_text(indent_engine.INDENT_UNIT)

        @bindings.add("s-tab")
        def _(event):
            """Remove up to one indent unit of leading whitespace from the
            current line, without disturbing the cursor's position in the
            text after it."""
            buf = event.current_buffer
            col = buf.document.cursor_position_col
            line = buf.document.current_line
            leading = len(line) - len(line.lstrip(" "))
            to_delete = min(len(indent_engine.INDENT_UNIT), leading, col)
            if to_delete:
                buf.delete_before_cursor(to_delete)

        session = PromptSession(history=InMemoryHistory(), key_bindings=bindings)

        def read_line(prompt: str, default_text: str = "") -> str:
            return session.prompt(prompt, default=default_text)

        return read_line, "prompt_toolkit"

    except ImportError:
        def read_line(prompt: str, default_text: str = "") -> str:
            # Plain input() can't pre-fill a buffer, so the suggested
            # indentation is shown as part of the prompt text itself and
            # prepended to whatever the user types.
            typed = input(prompt + default_text)
            return default_text + typed

        return read_line, "plain"


def run_repl():
    print(BANNER_TEMPLATE.format(version=_current_version()))
    read_line, backend = _make_line_reader()
    if backend == "plain":
        print("(Tip: `pip install prompt_toolkit` for command history, Tab-to-indent, "
              "and automatic indentation while typing.)")

    interpreter = Interpreter(source="", filename="<repl>")
    session = ReplSession()
    indent_state = indent_engine.IndentState()

    while True:
        prompt = "> " if session.is_empty else "... "
        suggested_indent = indent_state.indent_for_next_line() if not session.is_empty else ""

        try:
            line = read_line(prompt, suggested_indent)
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("^C")
            session.reset()
            indent_state = indent_engine.IndentState()
            continue

        if session.is_empty and line.strip().lower() in ("exit", "quit"):
            break

        result = session.feed(line)
        indent_state.feed(line)

        if not result.ready:
            continue

        indent_state = indent_engine.IndentState()
        source = result.source or ""
        if not source.strip():
            # Bare END with nothing buffered - nothing to run.
            continue

        try:
            tokens = tokenize(source, "<repl>")
            program = Parser(tokens, source, "<repl>").parse_program()
        except NexError as e:
            sys.stdout.write(e.render(use_color=sys.stdout.isatty()))
            continue

        interpreter.source_lines = source.splitlines()
        try:
            interpreter.run(program)
        except NexError as e:
            sys.stdout.write(e.render(use_color=sys.stdout.isatty()))
