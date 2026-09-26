"""
NexLang IDE - application window
===================================

This is the actual graphical application `nex` launches (PART 3 of the
project brief): a standalone window, not something that runs inside
CMD. It is a thin shell around:

  - `ide/editor.py`  - the per-file editor widget (syntax highlighting,
                        smart indent, find/replace, undo/redo)
  - `ide/runner.py`  - runs the real NexLang CLI as a subprocess and
                        streams its output/accepts its input
  - `compiler/api.py` (via `ide/runner.check_file`) - syntax checking for
                        inline error highlighting

Layout: a file/project explorer on the left, a tabbed editor in the
center, and an Output/Input panel plus status bar along the bottom -
matching the feature list in PART 3.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from typing import Optional

from ide.editor import Editor
from ide.runner import run_file, check_file, RunHandle
from ide.theme import COLORS, UI_FONT
from ide.identity import apply_identity, ensure_windows_app_identity_set_early

APP_TITLE = "NexIDE"
DEFAULT_TEMPLATE = 'SAY "Hello, NexLang!"\n'


class FileTab:
    """Bookkeeping for one open editor tab."""

    def __init__(self, editor: Editor, path: Optional[str], label: str):
        self.editor = editor
        self.path = path
        self.label = label


class NexIDE(tk.Tk):
    def __init__(self, initial_path: Optional[str] = None):
        super().__init__()
        self.title(APP_TITLE)
        apply_identity(self)
        self.geometry("1200x760")
        self.configure(background=COLORS["app_bg"])
        self._apply_ttk_theme()

        self.tabs: dict[str, FileTab] = {}  # notebook tab id -> FileTab
        self.project_dir: Optional[str] = None
        self.run_handle: Optional[RunHandle] = None

        self._build_menu()
        self._build_layout()
        self.protocol("WM_DELETE_WINDOW", self._on_close_window)

        if initial_path and os.path.isfile(initial_path):
            self.open_file(initial_path)
            self.project_dir = os.path.dirname(os.path.abspath(initial_path))
            self._refresh_explorer()
        else:
            self.new_file()

    # ---- theming ----

    def _apply_ttk_theme(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=COLORS["app_bg"])
        style.configure("TLabel", background=COLORS["app_bg"], foreground=COLORS["panel_fg"], font=UI_FONT)
        style.configure("TButton", background=COLORS["accent"], foreground="white", font=UI_FONT, padding=6)
        style.map("TButton", background=[("active", COLORS["accent_hover"])])
        style.configure("TNotebook", background=COLORS["app_bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["panel_bg"], foreground=COLORS["panel_fg"],
                         padding=(10, 4), font=UI_FONT)
        style.map("TNotebook.Tab", background=[("selected", COLORS["editor_bg"])])
        style.configure("Treeview", background=COLORS["tree_bg"], foreground=COLORS["tree_fg"],
                         fieldbackground=COLORS["tree_bg"], borderwidth=0, font=UI_FONT)
        style.configure("Status.TLabel", background=COLORS["status_bg"], foreground=COLORS["status_fg"], font=UI_FONT)

    # ---- menu ----

    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New File", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open File...", accelerator="Ctrl+O", command=self.open_file_dialog)
        file_menu.add_command(label="Open Folder...", command=self.open_folder_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_current)
        file_menu.add_command(label="Save As...", accelerator="Ctrl+Shift+S", command=self.save_current_as)
        file_menu.add_command(label="Close File", accelerator="Ctrl+W", command=self.close_current_tab)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close_window)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=lambda: self._active_text_cmd("edit_undo"))
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=lambda: self._active_text_cmd("edit_redo"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=lambda: self._active_text_event("<<Cut>>"))
        edit_menu.add_command(label="Copy", command=lambda: self._active_text_event("<<Copy>>"))
        edit_menu.add_command(label="Paste", command=lambda: self._active_text_event("<<Paste>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Find...", accelerator="Ctrl+F", command=self.show_find)
        edit_menu.add_command(label="Replace...", accelerator="Ctrl+H", command=self.show_replace)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Run", accelerator="F5", command=self.run_current)
        run_menu.add_command(label="Stop", accelerator="Shift+F5", command=self.stop_run)
        menubar.add_cascade(label="Run", menu=run_menu)

        self.config(menu=menubar)

        self.bind_all("<Control-n>", lambda e: self.new_file())
        self.bind_all("<Control-o>", lambda e: self.open_file_dialog())
        self.bind_all("<Control-s>", lambda e: self.save_current())
        self.bind_all("<Control-S>", lambda e: self.save_current_as())
        self.bind_all("<Control-w>", lambda e: self.close_current_tab())
        self.bind_all("<Control-f>", lambda e: self.show_find())
        self.bind_all("<Control-h>", lambda e: self.show_replace())
        self.bind_all("<F5>", lambda e: self.run_current())
        self.bind_all("<Shift-F5>", lambda e: self.stop_run())

    # ---- layout ----

    def _build_layout(self):
        main = tk.PanedWindow(self, orient="horizontal", sashwidth=4,
                               background=COLORS["border"], borderwidth=0)
        main.pack(fill="both", expand=True)

        # -- left: file explorer --
        explorer_frame = ttk.Frame(main, width=220)
        ttk.Label(explorer_frame, text="EXPLORER", padding=(8, 6)).pack(anchor="w")
        self.explorer = ttk.Treeview(explorer_frame, show="tree")
        self.explorer.pack(fill="both", expand=True)
        self.explorer.bind("<Double-1>", self._on_explorer_double_click)
        main.add(explorer_frame, minsize=160)

        # -- center/right: editor tabs + output --
        right = tk.PanedWindow(main, orient="vertical", sashwidth=4,
                                background=COLORS["border"], borderwidth=0)

        self.notebook = ttk.Notebook(right)
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._on_tab_changed())
        right.add(self.notebook, minsize=300, stretch="always")

        bottom = ttk.Frame(right)
        self._build_run_panel(bottom)
        right.add(bottom, minsize=160)

        main.add(right, stretch="always")

        # -- status bar --
        self.status = ttk.Label(self, text="Ready", style="Status.TLabel", anchor="w", padding=(8, 2))
        self.status.pack(fill="x", side="bottom")

    def _build_run_panel(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="\u25b6 Run", command=self.run_current).pack(side="left", padx=(4, 2), pady=4)
        ttk.Button(toolbar, text="\u25a0 Stop", command=self.stop_run).pack(side="left", padx=2, pady=4)
        ttk.Label(toolbar, text="Output").pack(side="left", padx=10)

        self.output = tk.Text(parent, height=10, background=COLORS["panel_bg"], foreground=COLORS["output_fg"],
                               insertbackground=COLORS["output_fg"], borderwidth=0, highlightthickness=0,
                               state="disabled", wrap="word")
        self.output.pack(fill="both", expand=True, side="top")

        input_bar = ttk.Frame(parent)
        input_bar.pack(fill="x", side="bottom")
        ttk.Label(input_bar, text="Input:").pack(side="left", padx=(4, 4))
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(input_bar, textvariable=self.input_var,
                                     background=COLORS["panel_bg"], foreground=COLORS["input_fg"],
                                     insertbackground=COLORS["input_fg"], borderwidth=1)
        self.input_entry.pack(fill="x", expand=True, side="left", padx=(0, 4), pady=4)
        self.input_entry.bind("<Return>", self._on_input_submit)
        self.input_entry.configure(state="disabled")

    # ---- tab / editor management ----

    def _active_tab(self) -> Optional[FileTab]:
        tab_id = self.notebook.select()
        return self.tabs.get(tab_id)

    def _active_editor(self) -> Optional[Editor]:
        tab = self._active_tab()
        return tab.editor if tab else None

    def _active_text_cmd(self, method_name: str):
        editor = self._active_editor()
        if editor:
            getattr(editor.text, method_name)()

    def _active_text_event(self, event_name: str):
        editor = self._active_editor()
        if editor:
            editor.text.event_generate(event_name)

    def new_file(self):
        editor = Editor(self.notebook, on_modified=self._refresh_tab_titles)
        editor.set_text(DEFAULT_TEMPLATE)
        tab_id = editor  # ttk.Notebook uses widget itself as the tab id
        self.notebook.add(editor, text="untitled.nex")
        self.tabs[str(editor)] = FileTab(editor, path=None, label="untitled.nex")
        self.notebook.select(editor)
        self._set_status("New file")

    def open_file_dialog(self):
        path = filedialog.askopenfilename(filetypes=[("NexLang files", "*.nex"), ("All files", "*.*")])
        if path:
            self.open_file(path)

    def open_folder_dialog(self):
        folder = filedialog.askdirectory()
        if folder:
            self.project_dir = folder
            self._refresh_explorer()

    def open_file(self, path: str):
        for tab in self.tabs.values():
            if tab.path == os.path.abspath(path):
                self.notebook.select(tab.editor)
                return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Could not open {path}:\n{e}")
            return
        editor = Editor(self.notebook, on_modified=self._refresh_tab_titles)
        editor.set_text(content)
        label = os.path.basename(path)
        self.notebook.add(editor, text=label)
        self.tabs[str(editor)] = FileTab(editor, path=os.path.abspath(path), label=label)
        self.notebook.select(editor)
        self._set_status(f"Opened {path}")

    def save_current(self):
        tab = self._active_tab()
        if not tab:
            return
        if tab.path is None:
            self.save_current_as()
            return
        self._write_file(tab, tab.path)

    def save_current_as(self):
        tab = self._active_tab()
        if not tab:
            return
        path = filedialog.asksaveasfilename(defaultextension=".nex",
                                             filetypes=[("NexLang files", "*.nex")])
        if not path:
            return
        self._write_file(tab, path)

    def _write_file(self, tab: FileTab, path: str):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(tab.editor.get_text())
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Could not save {path}:\n{e}")
            return
        tab.path = os.path.abspath(path)
        tab.label = os.path.basename(path)
        tab.editor.mark_saved()
        self.notebook.tab(tab.editor, text=tab.label)
        self._set_status(f"Saved {path}")
        self._check_and_highlight(tab)
        if self.project_dir is None:
            self.project_dir = os.path.dirname(tab.path)
            self._refresh_explorer()

    def close_current_tab(self):
        tab = self._active_tab()
        if not tab:
            return
        if tab.editor.dirty:
            answer = messagebox.askyesnocancel(APP_TITLE, f"Save changes to {tab.label}?")
            if answer is None:
                return
            if answer:
                self.save_current()
        tab_id = str(tab.editor)
        self.notebook.forget(tab.editor)
        del self.tabs[tab_id]
        if not self.tabs:
            self.new_file()

    def _refresh_tab_titles(self):
        for tab in self.tabs.values():
            suffix = " *" if tab.editor.dirty else ""
            self.notebook.tab(tab.editor, text=tab.label + suffix)

    def _on_tab_changed(self):
        tab = self._active_tab()
        if tab:
            self._set_status(tab.path or "(unsaved)")

    # ---- explorer ----

    def _refresh_explorer(self):
        self.explorer.delete(*self.explorer.get_children())
        if not self.project_dir:
            return
        root_id = self.explorer.insert("", "end", text=os.path.basename(self.project_dir),
                                        values=[self.project_dir], open=True)
        for entry in sorted(os.listdir(self.project_dir)):
            if entry.endswith(".nex"):
                full = os.path.join(self.project_dir, entry)
                self.explorer.insert(root_id, "end", text=entry, values=[full])

    def _on_explorer_double_click(self, _event):
        item = self.explorer.focus()
        values = self.explorer.item(item, "values")
        if values and os.path.isfile(values[0]):
            self.open_file(values[0])

    # ---- find / replace ----

    def show_find(self):
        editor = self._active_editor()
        if not editor:
            return
        needle = simpledialog.askstring(APP_TITLE, "Find:", parent=self)
        if needle:
            found = editor.find(needle)
            self._set_status(f"Found {needle!r}" if found else f"{needle!r} not found")

    def show_replace(self):
        editor = self._active_editor()
        if not editor:
            return
        needle = simpledialog.askstring(APP_TITLE, "Find:", parent=self)
        if not needle:
            return
        replacement = simpledialog.askstring(APP_TITLE, "Replace with:", parent=self) or ""
        count = editor.replace_all(needle, replacement)
        self._set_status(f"Replaced {count} occurrence(s)")

    # ---- run / stop ----

    def run_current(self):
        tab = self._active_tab()
        if not tab:
            return
        if tab.editor.dirty or tab.path is None:
            self.save_current()
            tab = self._active_tab()
            if tab is None or tab.path is None:
                return  # user cancelled Save As

        self._clear_output()
        self._append_output(f"Running {tab.label}...\n\n")
        self.input_entry.configure(state="normal")
        self.input_entry.focus_set()
        self._set_status(f"Running {tab.path}")

        self.run_handle = run_file(
            tab.path,
            on_output=lambda text: self.after(0, self._append_output, text),
            on_finished=lambda code: self.after(0, self._on_run_finished, code),
        )

    def stop_run(self):
        if self.run_handle and self.run_handle.is_running():
            self.run_handle.stop()
            self._append_output("\n[Stopped]\n")
            self._set_status("Stopped")

    def _on_input_submit(self, _event):
        text = self.input_var.get()
        self.input_var.set("")
        self._append_output(text + "\n")
        if self.run_handle:
            self.run_handle.send_input(text)

    def _on_run_finished(self, code: int):
        self._append_output(f"\n[Program exited with code {code}]\n")
        self.input_entry.configure(state="disabled")
        self._set_status("Ready")

    def _clear_output(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def _append_output(self, text: str):
        self.output.configure(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    # ---- syntax error highlighting on save (PART 7) ----

    def _check_and_highlight(self, tab: FileTab):
        error_text = check_file(tab.path)
        tab.editor.clear_error_highlight()
        if error_text is None:
            self._set_status(f"Saved {tab.path} - no syntax errors")
            return
        line_no = self._extract_line_number(error_text) or 1
        tab.editor.highlight_error_line(line_no)
        first_line = error_text.strip().splitlines()[0] if error_text.strip() else "Syntax error"
        self._set_status(first_line)

    @staticmethod
    def _extract_line_number(error_text: str) -> Optional[int]:
        import re
        match = re.search(r":(\d+):\d+\s*$", error_text.strip().splitlines()[-1] if error_text.strip() else "")
        if not match:
            match = re.search(r":(\d+):\d+", error_text)
        return int(match.group(1)) if match else None

    # ---- misc ----

    def _set_status(self, text: str):
        self.status.configure(text=text)

    def _on_close_window(self):
        for tab in list(self.tabs.values()):
            if tab.editor.dirty:
                self.notebook.select(tab.editor)
                answer = messagebox.askyesnocancel(APP_TITLE, f"Save changes to {tab.label}?")
                if answer is None:
                    return
                if answer:
                    self.save_current()
        if self.run_handle:
            self.run_handle.stop()
        self.destroy()


def launch_ide(initial_path: Optional[str] = None) -> None:
    # Must run before the Tk root window is constructed - see
    # ide/identity.py:ensure_windows_app_identity_set_early.
    ensure_windows_app_identity_set_early()
    app = NexIDE(initial_path)
    app.mainloop()
