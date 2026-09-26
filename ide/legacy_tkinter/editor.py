"""
NexLang IDE - the code editor widget
======================================

A single-file editor pane: a Tkinter `Text` widget plus a line-number
gutter, wired up to:

  - `ide/highlight.py` for syntax highlighting (re-applied after edits)
  - `compiler/indent.py` for smart auto-indent on Enter/END/OTHERWISE
  - standard editing features Tk gives for free (Undo/Redo via Tk's
    built-in undo stack, Copy/Paste, Find/Replace via a small dialog
    below, text selection, and normal Backspace/arrow-key/Home/End
    behaviour).

Kept separate from `ide/app.py` (the window chrome: menus, tabs, output
panel) so the editor itself has no idea it's inside a multi-tab IDE - it
just edits one buffer, optionally backed by a file on disk.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, Optional

from compiler import indent as indent_engine
from ide import highlight
from ide.theme import COLORS, EDITOR_FONT

BLOCK_OPENER_WORDS = {"IF", "WHILE", "REPEAT", "FOR", "FUNCTION", "CLASS", "TRY"}


class LineNumbers(tk.Canvas):
    """A read-only gutter that mirrors the attached Text widget's
    scrolling and repaints line numbers next to it."""

    def __init__(self, master, text_widget: "tk.Text", **kwargs):
        super().__init__(master, width=48, highlightthickness=0,
                          background=COLORS["gutter_bg"], **kwargs)
        self.text_widget = text_widget

    def redraw(self, *_args) -> None:
        self.delete("all")
        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            line_no = str(i).split(".")[0]
            self.create_text(40, y, anchor="ne", text=line_no,
                              fill=COLORS["gutter_fg"], font=EDITOR_FONT)
            i = self.text_widget.index(f"{i}+1line")


class Editor(tk.Frame):
    """One editable NexLang buffer with line numbers and highlighting."""

    def __init__(self, master, on_modified: Optional[Callable[[], None]] = None, **kwargs):
        super().__init__(master, background=COLORS["editor_bg"], **kwargs)
        self.on_modified_cb = on_modified
        self.file_path: Optional[str] = None
        self.dirty = False

        self.text = tk.Text(
            self, wrap="none", undo=True, autoseparators=True, maxundo=-1,
            background=COLORS["editor_bg"], foreground=COLORS["editor_fg"],
            insertbackground=COLORS["editor_fg"], selectbackground=COLORS["selection_bg"],
            font=EDITOR_FONT, borderwidth=0, highlightthickness=0, padx=6, pady=4,
            tabs=self._tab_stops(),
        )
        self.linenumbers = LineNumbers(self, self.text)

        yscroll = tk.Scrollbar(self, orient="vertical", command=self._on_scroll)
        self.text.configure(yscrollcommand=self._on_textscroll(yscroll))

        self.linenumbers.pack(side="left", fill="y")
        yscroll.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        for tag, color in COLORS["syntax"].items():
            self.text.tag_configure(tag, foreground=color)
        self.text.tag_configure("error_line", background=COLORS["error_bg"])

        self._configure_bindings()
        self._redraw_all()

    # ---- layout helpers ----

    def _tab_stops(self):
        f = tkfont.Font(font=EDITOR_FONT)
        return (f.measure(" " * len(indent_engine.INDENT_UNIT)),)

    def _on_scroll(self, *args):
        self.text.yview(*args)
        self.linenumbers.redraw()

    def _on_textscroll(self, scrollbar):
        def handler(*args):
            scrollbar.set(*args)
            self.linenumbers.redraw()
        return handler

    # ---- key bindings ----

    def _configure_bindings(self):
        self.text.bind("<KeyRelease>", self._on_key_release)
        self.text.bind("<Return>", self._on_return)
        self.text.bind("<Tab>", self._on_tab)
        self.text.bind("<Shift-Tab>", self._on_shift_tab)
        self.text.bind("<MouseWheel>", lambda e: self.after_idle(self.linenumbers.redraw))
        self.text.bind("<Configure>", lambda e: self.linenumbers.redraw())
        self.text.bind("<<Modified>>", self._on_modified_flag)

    def _mark_dirty(self):
        if not self.dirty:
            self.dirty = True
            if self.on_modified_cb:
                self.on_modified_cb()

    def _on_modified_flag(self, _event=None):
        if self.text.edit_modified():
            self._mark_dirty()
            self.text.edit_modified(False)

    def _on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Left", "Right", "Shift_L", "Shift_R",
                             "Control_L", "Control_R"):
            self.linenumbers.redraw()
            return
        self._maybe_autodedent_current_line()
        self._apply_highlighting()
        self.linenumbers.redraw()

    def _on_return(self, event):
        """Smart-indent: pressing Enter inserts a newline plus the
        indentation the new line should have, based on the line the
        cursor is leaving."""
        current_line = self.text.get("insert linestart", "insert")
        next_indent = indent_engine.next_line_indent(current_line)
        self.text.insert("insert", "\n" + next_indent)
        self._maybe_dedent_closer_after_typing()
        self._apply_highlighting()
        return "break"

    def _on_tab(self, event):
        self.text.insert("insert", indent_engine.INDENT_UNIT)
        return "break"

    def _on_shift_tab(self, event):
        line_start = self.text.index("insert linestart")
        line_text = self.text.get(line_start, "insert")
        leading = len(line_text) - len(line_text.lstrip(" "))
        remove = min(len(indent_engine.INDENT_UNIT), leading)
        if remove:
            self.text.delete(line_start, f"{line_start}+{remove}c")
        return "break"

    def _maybe_dedent_closer_after_typing(self):
        """Placeholder kept for readability at the call site in
        `_on_return`; the actual dedent-while-typing correction happens
        continuously in `_on_key_release` -> `_maybe_autodedent_current_line`,
        since Tk has no clean "word just completed" event to hook into."""
        pass

    def _maybe_autodedent_current_line(self):
        """If the line the cursor is on is now exactly END / OTHERWISE /
        CATCH / FINALLY (the user just finished typing one of those
        keywords), snap its indentation back one level so it lines up
        with the block it closes/continues - matching PART 4's example
        of `END` auto-formatting itself under the block it closes."""
        line_start = self.text.index("insert linestart")
        line_end = self.text.index("insert lineend")
        raw_line = self.text.get(line_start, line_end)
        stripped = raw_line.strip()
        if stripped.upper() not in ("END", "OTHERWISE", "CATCH", "FINALLY"):
            return

        state = indent_engine.IndentState()
        line_no = int(str(line_start).split(".")[0])
        for prior_line_no in range(1, line_no):
            prior_text = self.text.get(f"{prior_line_no}.0", f"{prior_line_no}.end")
            state.feed(prior_text)

        correct_indent = state.indent_for_line(stripped)
        current_indent = indent_engine.indent_of(raw_line)
        if current_indent != correct_indent:
            self.text.delete(line_start, line_end)
            self.text.insert(line_start, correct_indent + stripped)

    # ---- highlighting ----

    def _apply_highlighting(self):
        source = self.get_text()
        for tag in COLORS["syntax"]:
            self.text.tag_remove(tag, "1.0", "end")
        for span in highlight.compute_spans(source):
            start = f"{span.line}.{span.col - 1}"
            end = f"{span.line}.{span.col - 1 + span.length}"
            self.text.tag_add(span.tag, start, end)

    def _redraw_all(self):
        self._apply_highlighting()
        self.linenumbers.redraw()

    # ---- error highlighting (PART 7) ----

    def clear_error_highlight(self):
        self.text.tag_remove("error_line", "1.0", "end")

    def highlight_error_line(self, line_no: int):
        self.clear_error_highlight()
        self.text.tag_add("error_line", f"{line_no}.0", f"{line_no}.end+1c")
        self.text.see(f"{line_no}.0")

    # ---- buffer access ----

    def get_text(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_text(self, content: str) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.edit_reset()
        self.dirty = False
        self._redraw_all()

    def mark_saved(self) -> None:
        self.dirty = False

    # ---- find / replace ----

    def find(self, needle: str, start="1.0") -> Optional[str]:
        if not needle:
            return None
        pos = self.text.search(needle, start, stopindex="end")
        if not pos:
            return None
        end = f"{pos}+{len(needle)}c"
        self.text.tag_remove("sel", "1.0", "end")
        self.text.tag_add("sel", pos, end)
        self.text.mark_set("insert", end)
        self.text.see(pos)
        return pos

    def replace_all(self, needle: str, replacement: str) -> int:
        if not needle:
            return 0
        content = self.get_text()
        count = content.count(needle)
        if count:
            self.set_text(content.replace(needle, replacement))
        return count
