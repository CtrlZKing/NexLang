"""
NexLang Diagnostic System
==========================

Every error NexLang produces is a `NexError`. Errors are designed to answer
four questions for the person reading them:

    WHAT happened?
    WHERE did it happen?
    WHY did it happen?
    HOW can I fix it?

This module is intentionally standalone (no dependency on the lexer/parser/
interpreter) so that any stage of the compiler can raise rich diagnostics
using the same formatting logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class SourceLocation:
    """A precise location in a NexLang source file."""
    filename: str
    line: int          # 1-indexed
    column: int         # 1-indexed
    length: int = 1      # how many characters to underline


@dataclass
class NexError(Exception):
    """
    A rich, structured NexLang diagnostic.

    code:        short machine-readable code, e.g. "NX204"
    title:       one-line human summary, e.g. "Cannot add NUMBER and TEXT"
    location:    where in the source this happened (optional - some errors,
                 like CLI usage errors, have no source location)
    explanation: 1-3 sentences on WHY this happened
    suggestions: list of concrete fix suggestions (short code snippets or sentences)
    source_line: the raw text of the offending source line, used to draw
                 the caret/underline
    help_topic:  a topic name usable with `nex help <topic>` for more info
    """
    code: str
    title: str
    explanation: str = ""
    location: Optional[SourceLocation] = None
    suggestions: List[str] = field(default_factory=list)
    source_line: Optional[str] = None
    help_topic: Optional[str] = None

    def __str__(self) -> str:
        return self.render()

    def render(self, use_color: bool = True) -> str:
        lines = []

        def c(code, text):
            if not use_color:
                return text
            return f"\033[{code}m{text}\033[0m"

        header = f"ERROR {self.code} \u2014 {self.title}"
        lines.append(c("1;31", header))
        lines.append("")

        if self.location is not None and self.source_line is not None:
            loc = self.location
            gutter = f" {loc.line} | "
            lines.append(f"{gutter}{self.source_line}")
            caret_pad = " " * (len(gutter) + max(loc.column - 1, 0))
            caret = "^" * max(loc.length, 1)
            lines.append(f"{caret_pad}{c('1;31', caret)}")
            lines.append("")

        if self.explanation:
            lines.append(self.explanation)
            lines.append("")

        if self.suggestions:
            lines.append("Possible fixes:")
            lines.append("")
            for s in self.suggestions:
                lines.append(f"    {s}")
            lines.append("")

        if self.location is not None:
            lines.append(f"Location:")
            lines.append(f"    {self.location.filename}:{self.location.line}:{self.location.column}")
            lines.append("")

        if self.help_topic:
            lines.append(f"Learn more:")
            lines.append(f"    nex help {self.help_topic}")

        return "\n".join(lines).rstrip() + "\n"


def levenshtein(a: str, b: str) -> int:
    """Small edit-distance helper used for 'Did you mean ...?' suggestions."""
    if a == b:
        return 0
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)
    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur_row = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            insert_cost = cur_row[j - 1] + 1
            delete_cost = prev_row[j] + 1
            replace_cost = prev_row[j - 1] + (0 if ca == cb else 1)
            cur_row[j] = min(insert_cost, delete_cost, replace_cost)
        prev_row = cur_row
    return prev_row[-1]


def closest_match(name: str, candidates: List[str], max_distance: int = 3) -> Optional[str]:
    """Return the closest candidate to `name` by edit distance, or None."""
    best = None
    best_dist = max_distance + 1
    for cand in candidates:
        d = levenshtein(name.lower(), cand.lower())
        if d < best_dist:
            best = cand
            best_dist = d
    return best if best_dist <= max_distance else None
