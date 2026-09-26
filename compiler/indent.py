"""
NexLang smart-indentation engine
=================================

A small, dependency-free, line-based heuristic for "what indentation
should the next line get" and "does this line close a block", shared by:

  - the interactive REPL (to show sensible indentation while typing, see
    `repl/repl.py`)
  - the graphical IDE's editor widget (see `ide/editor.py`)

This is deliberately NOT a full parse: it looks at one line of text at a
time using simple keyword matching, the same way editors for indentation-
insensitive-but-block-structured languages usually do it. That keeps it
fast, reusable outside a full parser/AST, and tolerant of code that is
still being typed (and therefore not valid NexLang yet).

Recognized openers include constructs implemented as of Phase 2 "POWER"
(IF/WHILE/REPEAT/FOR/FUNCTION/TRY/CATCH/FINALLY) *and* CLASS, reserved for
a later phase, so the indentation engine won't need to change again when
that lands - see docs/ROADMAP.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

INDENT_UNIT = "    "  # 4 spaces

# A line that OPENS a new block (its *own* body should be indented one
# level deeper than it).
_OPENER_RE = re.compile(
    r"""^\s*(
        IF\b.*\bTHEN\s*$          |
        ELSE\s+IF\b.*\bTHEN\s*$   |
        WHILE\b                   |
        REPEAT\b                  |
        FOR\b                      |
        FUNCTION\b                |
        CLASS\b                   |
        TRY\s*$
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# A line that is a "midpoint" of a block: it DEdents back to the same
# level as the opener, then that line itself acts like an opener for the
# next segment (e.g. OTHERWISE, ELSE IF, CATCH, FINALLY).
_MIDPOINT_RE = re.compile(
    r"^\s*(OTHERWISE\b|ELSE\s+IF\b.*\bTHEN\s*$|CATCH\b|FINALLY\s*$)",
    re.IGNORECASE,
)

# A line that CLOSES a block outright.
_CLOSER_RE = re.compile(r"^\s*END\b", re.IGNORECASE)


def is_opener(line: str) -> bool:
    return bool(_OPENER_RE.match(line.strip("\n")))


def is_midpoint(line: str) -> bool:
    return bool(_MIDPOINT_RE.match(line.strip("\n")))


def is_closer(line: str) -> bool:
    return bool(_CLOSER_RE.match(line.strip("\n")))


def indent_of(line: str) -> str:
    """Return the leading whitespace of `line`."""
    return line[: len(line) - len(line.lstrip(" \t"))]


def next_line_indent(previous_line: str) -> str:
    """Given the line the cursor is leaving (because the user just
    pressed Enter), return the indentation the new line should start
    with."""
    base = indent_of(previous_line)
    stripped = previous_line.strip()
    if is_opener(stripped) or is_midpoint(stripped):
        return base + INDENT_UNIT
    return base


def dedent_for_closer(current_indent: str) -> str:
    """When the user types a line that is (or starts with) END/OTHERWISE/
    CATCH/FINALLY, that line itself should be dedented one level relative
    to whatever indent it was given automatically."""
    if current_indent.endswith(INDENT_UNIT):
        return current_indent[: -len(INDENT_UNIT)]
    if current_indent.endswith("\t"):
        return current_indent[:-1]
    return ""


@dataclass
class IndentState:
    """Tracks nesting depth across a whole buffer (REPL session or an open
    IDE file) so indentation stays consistent even when lines are edited
    out of order (e.g. pasted text)."""
    depth: int = 0

    def feed(self, line: str) -> None:
        stripped = line.strip()
        if is_closer(stripped):
            self.depth = max(0, self.depth - 1)
        elif is_midpoint(stripped):
            pass  # stays at same depth as its opener
        if is_opener(stripped):
            self.depth += 1

    def indent_for_next_line(self) -> str:
        return INDENT_UNIT * self.depth

    def indent_for_line(self, line: str) -> str:
        """Indent to use for `line` itself (dedent first for closers/midpoints)."""
        stripped = line.strip()
        depth = self.depth
        if is_closer(stripped) or is_midpoint(stripped):
            depth = max(0, depth - 1)
        return INDENT_UNIT * depth


def reindent_buffer(text: str) -> str:
    """Recompute indentation for an entire buffer from scratch, useful for
    an IDE 'Format' action or for cleaning up pasted code. Blank lines are
    left blank."""
    state = IndentState()
    out_lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            out_lines.append("")
            continue
        indent = state.indent_for_line(stripped)
        out_lines.append(indent + stripped)
        state.feed(stripped)
    return "\n".join(out_lines)
