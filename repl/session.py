"""
NexLang interactive session state machine
==========================================

This module contains the *logic* of the interactive REPL, deliberately
separated from any terminal/input-library concerns (see `repl.py` for the
actual line-editing front end). Keeping it separate means the submission
rules can be unit tested directly, without simulating a terminal.

--------------------------------------------------------------------------
THE PROBLEM
--------------------------------------------------------------------------
Interactive mode must NOT behave like script mode. In a `.nex` file, a
block's own `END` is enough to close it, and the file's EOF finishes the
program. But at an interactive prompt there is no "EOF" - the user just
keeps pressing Enter - so NexLang needs an explicit, unambiguous signal
that says "I'm done, run what I've written". That signal is a line that
is *just* `END`.

This creates one wrinkle: `END` is *also* the token that closes an
IF/WHILE/REPEAT/FOR/FUNCTION/TRY block inside the language itself. So the
REPL has
to tell apart two different meanings of the same word:

    - a "closing END"     -> closes the innermost still-open block
    - a "submitting END"  -> there is nothing left open, so this is the
                              user telling the REPL to run the program

--------------------------------------------------------------------------
THE RULE (not a fragile string check)
--------------------------------------------------------------------------
The session tracks the current *block depth* by re-tokenizing the
accumulated buffer after every line (using the real NexLang lexer, so it
understands strings/comments and can't be confused by the word END
appearing inside a string). Depth is simply:

    depth = (number of block-opener tokens)  -  (number of END tokens)

When the user submits a new line that is exactly `END` (case-insensitive):

    * if depth-before-this-line > 0
          there is an open block, so this END closes it.
          Append the line to the buffer.
            - if the new depth is now 0, every block the user opened is
              closed, so this doubles as the submission signal -> RUN.
            - otherwise, keep waiting for more `END`s (nested blocks).

    * if depth-before-this-line == 0
          there is nothing open to close, so this bare `END` carries no
          block-closing meaning at all - it IS the submission signal.
          It is intentionally NOT appended to the buffer (there is no
          matching opener for the parser to pair it with) -> RUN whatever
          was accumulated so far.

This one rule handles every case in the spec:
  - a single `SAY "Hello"` followed by a bare `END` -> runs "SAY Hello"
  - `IF ... THEN / SAY "yes" / END` -> the one END closes the IF *and*
    brings depth to 0, so it submits too
  - nested IFs -> the inner END only closes the inner block (depth still
    > 0 afterwards), the outer END closes the outer block *and* submits
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from compiler.lexer.lexer import tokenize
from compiler.lexer.tokens import TokenType
from compiler.errors.errors import NexError

# Tokens that open a NexLang block and therefore expect a matching END.
# Counting *openers* rather than every keyword is what keeps this correct
# as the language grows new block types (CLASS, when it lands, will just
# be added here too).
BLOCK_OPENERS = {
    TokenType.IF, TokenType.WHILE, TokenType.REPEAT, TokenType.FOR,
    TokenType.FUNCTION, TokenType.TRY,
}


def _count_depth(source: str) -> Optional[int]:
    """Return (openers - ENDs) for `source`, or None if it doesn't even
    tokenize yet (e.g. an unterminated string) - the caller should treat
    that as "still typing, keep buffering"."""
    try:
        tokens = tokenize(source, "<repl>")
    except NexError:
        return None
    depth = 0
    for tok in tokens:
        if tok.type in BLOCK_OPENERS:
            depth += 1
        elif tok.type == TokenType.END:
            depth -= 1
    return depth


@dataclass
class SubmitResult:
    """What the session decided to do with the line that was just entered."""
    ready: bool                      # True => `source` should be executed now
    source: Optional[str] = None     # the accumulated program, if ready
    prompt_depth: int = 0            # current nesting depth (for prompt display)


class ReplSession:
    """Accumulates lines typed at the interactive prompt and decides when
    a complete program has been submitted for execution.

    ENTER always just adds a line to the buffer. Nothing runs until the
    user types a bare `END` line that isn't needed to close a still-open
    block (see module docstring for the exact rule).
    """

    def __init__(self) -> None:
        self.lines: List[str] = []

    @property
    def is_empty(self) -> bool:
        return not self.lines

    def _buffer_source(self) -> str:
        return "\n".join(self.lines)

    def current_depth(self) -> int:
        depth = _count_depth(self._buffer_source())
        return depth if depth is not None else 0

    def feed(self, line: str) -> SubmitResult:
        """Feed one line of user input. Returns a SubmitResult telling the
        caller whether to execute now."""
        is_bare_end = line.strip().upper() == "END"

        if is_bare_end:
            depth_before = self.current_depth()
            if depth_before > 0:
                # Closes an open block.
                self.lines.append(line)
                new_depth = self.current_depth()
                if new_depth <= 0:
                    return self._submit()
                return SubmitResult(ready=False, prompt_depth=new_depth)
            else:
                # Nothing open - this bare END is the submission signal
                # itself, not part of the program.
                return self._submit()

        self.lines.append(line)
        return SubmitResult(ready=False, prompt_depth=self.current_depth())

    def _submit(self) -> SubmitResult:
        source = self._buffer_source()
        self.lines = []
        return SubmitResult(ready=True, source=source, prompt_depth=0)

    def reset(self) -> None:
        self.lines = []
