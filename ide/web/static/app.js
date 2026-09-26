// NexIDE frontend. Talks to the Python backend (ide/web/server.py) over
// plain fetch()/EventSource - no build step, no framework, no CDN
// dependency, so this works fully offline on the user's machine.
"use strict";

const DEFAULT_TEMPLATE = 'SAY "Hello, NexLang!"\n';

const state = {
  tabs: [],          // {id, path, label, content, dirty, editorEl, textarea, pre, gutter}
  activeTabId: null,
  nextTabId: 1,
  explorerPath: null,
  runId: null,
  eventSource: null,
  modalMode: null,   // 'open-file' | 'open-folder' | 'save-as'
  modalDir: null,
};

// ---------------------------------------------------------------- utils

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of children) node.appendChild(c);
  return node;
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function debounce(fn, ms) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok && res.status !== 404) {
    const text = await res.text();
    throw new Error(`${path}: ${res.status} ${text}`);
  }
  return res.json();
}

function setStatus(text) {
  document.getElementById("status-text").textContent = text;
}

// ---------------------------------------------------------------- tabs

function activeTab() {
  return state.tabs.find(t => t.id === state.activeTabId) || null;
}

function makeTab(path, content, label) {
  const id = "tab" + state.nextTabId++;

  const gutter = el("div", { class: "gutter" });
  const pre = el("pre", { class: "highlight-layer" }, [el("code")]);
  const textarea = el("textarea", {
    class: "input-layer",
    spellcheck: "false",
    autocapitalize: "off",
    autocomplete: "off",
  });
  textarea.value = content;

  const codeSurface = el("div", { class: "code-surface" }, [pre, textarea]);
  const wrap = el("div", { class: "editor-wrap" }, [gutter, codeSurface]);
  const instance = el("div", { class: "editor-instance" }, [wrap]);
  document.getElementById("editors").appendChild(instance);

  const tab = {
    id, path, label: label || (path ? path.split(/[\\/]/).pop() : "untitled.nex"),
    content, dirty: false, editorEl: instance, textarea, pre, gutter,
  };

  textarea.addEventListener("input", () => onEditorInput(tab));
  textarea.addEventListener("scroll", () => syncScroll(tab));
  textarea.addEventListener("keydown", (e) => onEditorKeydown(tab, e));

  state.tabs.push(tab);
  renderTabBar();
  updateGutter(tab);
  refreshHighlight(tab);
  return tab;
}

function selectTab(id) {
  state.activeTabId = id;
  for (const t of state.tabs) {
    t.editorEl.classList.toggle("active", t.id === id);
  }
  renderTabBar();
  const tab = activeTab();
  if (tab) {
    setStatus(tab.path || "(unsaved)");
    tab.textarea.focus();
  }
}

function closeTab(id) {
  const idx = state.tabs.findIndex(t => t.id === id);
  if (idx === -1) return;
  const tab = state.tabs[idx];
  if (tab.dirty) {
    const ok = confirm(`Save changes to ${tab.label}?`);
    if (ok) { saveTab(tab); }
  }
  tab.editorEl.remove();
  state.tabs.splice(idx, 1);
  if (state.tabs.length === 0) {
    newFile();
  } else if (state.activeTabId === id) {
    selectTab(state.tabs[Math.max(0, idx - 1)].id);
  } else {
    renderTabBar();
  }
}

function renderTabBar() {
  const bar = document.getElementById("tabs");
  bar.innerHTML = "";
  for (const t of state.tabs) {
    const label = el("span", { text: t.label });
    const dot = el("span", { class: "dirty-dot" });
    const closeX = el("span", { class: "close-x", text: "\u00d7", onclick: (e) => { e.stopPropagation(); closeTab(t.id); } });
    const tabEl = el("div", {
      class: "tab" + (t.id === state.activeTabId ? " active" : "") + (t.dirty ? " dirty" : ""),
      onclick: () => selectTab(t.id),
    }, [label, dot, closeX]);
    bar.appendChild(tabEl);
  }
}

function markDirty(tab, dirty) {
  tab.dirty = dirty;
  renderTabBar();
}

// ---------------------------------------------------------------- editor

function updateGutter(tab) {
  const lines = tab.textarea.value.split("\n").length;
  let html = "";
  for (let i = 1; i <= lines; i++) html += i + "\n";
  tab.gutter.textContent = html;
}

function syncScroll(tab) {
  tab.pre.parentElement.scrollTop = tab.textarea.scrollTop;
  tab.pre.parentElement.scrollLeft = tab.textarea.scrollLeft;
  tab.gutter.scrollTop = tab.textarea.scrollTop;
}

const refreshHighlight = debounce(async (tab) => {
  try {
    const data = await api("/api/highlight", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: tab.textarea.value }),
    });
    applyHighlight(tab, data.spans || []);
  } catch (e) { /* highlighting is best-effort */ }
}, 120);

function applyHighlight(tab, spans) {
  const lines = tab.textarea.value.split("\n");
  const byLine = {};
  for (const s of spans) {
    (byLine[s.line] = byLine[s.line] || []).push(s);
  }
  const out = [];
  lines.forEach((lineText, idx) => {
    const lineNo = idx + 1;
    const lineSpans = (byLine[lineNo] || []).sort((a, b) => a.col - b.col);
    let cursor = 0;
    let html = "";
    for (const s of lineSpans) {
      const start = s.col - 1;
      const end = Math.min(start + s.length, lineText.length);
      if (start > cursor) html += escapeHtml(lineText.slice(cursor, start));
      html += `<span class="tok-${s.tag}">${escapeHtml(lineText.slice(start, end))}</span>`;
      cursor = end;
    }
    html += escapeHtml(lineText.slice(cursor));
    out.push(html || "\n");
  });
  tab.pre.querySelector("code").innerHTML = out.join("\n");
}

const refreshCheck = debounce(async (tab) => {
  try {
    const data = await api("/api/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: tab.textarea.value, filename: tab.label }),
    });
    applyDiagnostic(tab, data);
  } catch (e) { /* ignore */ }
}, 400);

function applyDiagnostic(tab, result) {
  const summary = document.getElementById("diagnostic-summary");
  if (activeTab() !== tab) return;
  if (result.ok) {
    summary.textContent = "";
  } else {
    summary.textContent = `${result.code || "error"}: ${result.title || "syntax error"}` +
      (result.line ? ` (line ${result.line})` : "");
  }
}

function onEditorInput(tab) {
  tab.content = tab.textarea.value;
  markDirty(tab, true);
  updateGutter(tab);
  refreshHighlight(tab);
  refreshCheck(tab);
}

async function onEditorKeydown(tab, e) {
  if (e.key === "Tab") {
    e.preventDefault();
    insertAtCursor(tab.textarea, "    ");
    onEditorInput(tab);
    return;
  }
  if (e.key === "Enter") {
    e.preventDefault();
    const pos = tab.textarea.selectionStart;
    const before = tab.textarea.value.slice(0, pos);
    const after = tab.textarea.value.slice(pos);
    let indent = "";
    try {
      const data = await api("/api/indent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: before }),
      });
      indent = data.indent || "";
    } catch (err) { /* fall back to no auto-indent */ }
    const insertion = "\n" + indent;
    tab.textarea.value = before + insertion + after;
    const newPos = before.length + insertion.length;
    tab.textarea.selectionStart = tab.textarea.selectionEnd = newPos;
    onEditorInput(tab);
  }
}

function insertAtCursor(textarea, text) {
  const start = textarea.selectionStart, end = textarea.selectionEnd;
  textarea.value = textarea.value.slice(0, start) + text + textarea.value.slice(end);
  textarea.selectionStart = textarea.selectionEnd = start + text.length;
}

// ---------------------------------------------------------------- file ops

function newFile() {
  const tab = makeTab(null, DEFAULT_TEMPLATE, "untitled.nex");
  selectTab(tab.id);
  setStatus("New file");
}

async function openFileAtPath(path) {
  const existing = state.tabs.find(t => t.path === path);
  if (existing) { selectTab(existing.id); return; }
  const data = await api(`/api/file?path=${encodeURIComponent(path)}`);
  if (data.error) { alert(data.error); return; }
  const tab = makeTab(data.path, data.content, data.path.split(/[\\/]/).pop());
  selectTab(tab.id);
  setStatus(`Opened ${data.path}`);
}

async function saveTab(tab, forcePathPrompt = false) {
  if (!tab.path || forcePathPrompt) {
    const path = await promptSaveAs(tab.label);
    if (!path) return false;
    tab.path = path;
    tab.label = path.split(/[\\/]/).pop();
  }
  const data = await api("/api/file", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: tab.path, content: tab.textarea.value }),
  });
  if (data.error) { alert(data.error); return false; }
  tab.path = data.path;
  markDirty(tab, false);
  renderTabBar();
  setStatus(`Saved ${tab.path}`);
  refreshExplorer();
  return true;
}

// ---------------------------------------------------------------- explorer

async function refreshExplorer(path) {
  const data = await api(`/api/browse?path=${encodeURIComponent(path || state.explorerPath || "")}`);
  if (data.error) return;
  state.explorerPath = data.path;
  document.getElementById("explorer-path").textContent = data.path;
  document.getElementById("explorer-path").title = data.path;
  const tree = document.getElementById("explorer-tree");
  tree.innerHTML = "";
  if (data.parent) {
    tree.appendChild(el("div", {
      class: "tree-item", onclick: () => refreshExplorer(data.parent),
    }, [el("span", { class: "icon", text: "\u2b06" }), el("span", { text: ".. (up)" })]));
  }
  for (const entry of data.entries) {
    const icon = entry.is_dir ? "\ud83d\udcc1" : "\ud83d\udcc4";
    const full = data.path.replace(/[\\/]+$/, "") + (data.path.includes("\\") ? "\\" : "/") + entry.name;
    tree.appendChild(el("div", {
      class: "tree-item",
      onclick: () => entry.is_dir ? refreshExplorer(full) : openFileAtPath(full),
    }, [el("span", { class: "icon", text: icon }), el("span", { text: entry.name })]));
  }
}

// ---------------------------------------------------------------- modal (open/save-as browser)

function openModal(mode, title, confirmLabel, startPath) {
  state.modalMode = mode;
  state.modalDir = startPath || state.explorerPath;
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-confirm").textContent = confirmLabel;
  document.getElementById("modal-filename").hidden = mode !== "save-as";
  document.getElementById("modal-overlay").hidden = false;
  loadModalDir(state.modalDir);
}

function closeModal() {
  document.getElementById("modal-overlay").hidden = true;
  state._modalResolve && state._modalResolve(null);
  state._modalResolve = null;
}

async function loadModalDir(path) {
  const data = await api(`/api/browse?path=${encodeURIComponent(path || "")}`);
  if (data.error) return;
  state.modalDir = data.path;
  document.getElementById("modal-path").textContent = data.path;
  const list = document.getElementById("modal-list");
  list.innerHTML = "";
  if (data.parent) {
    list.appendChild(el("div", { class: "tree-item dir", text: ".. (up)", onclick: () => loadModalDir(data.parent) }));
  }
  for (const entry of data.entries) {
    const full = data.path.replace(/[\\/]+$/, "") + (data.path.includes("\\") ? "\\" : "/") + entry.name;
    const item = el("div", {
      class: "tree-item " + (entry.is_dir ? "dir" : "file"),
      text: entry.name,
      onclick: () => {
        if (entry.is_dir) { loadModalDir(full); }
        else if (state.modalMode === "open-file") { document.getElementById("modal-filename").value = full; confirmModal(full); }
        else { document.getElementById("modal-filename").value = entry.name; }
      },
    });
    list.appendChild(item);
  }
}

function confirmModal(directPath) {
  const mode = state.modalMode;
  if (mode === "open-folder") {
    closeModal();
    refreshExplorer(state.modalDir);
    return;
  }
  if (mode === "open-file") {
    const path = directPath;
    closeModal();
    if (path) openFileAtPath(path);
    return;
  }
  if (mode === "save-as") {
    const name = document.getElementById("modal-filename").value.trim();
    if (!name) return;
    const full = state.modalDir.replace(/[\\/]+$/, "") + (state.modalDir.includes("\\") ? "\\" : "/") + name;
    const resolve = state._modalResolve;
    document.getElementById("modal-overlay").hidden = true;
    state._modalResolve = null;
    resolve && resolve(full);
  }
}

function promptSaveAs(defaultName) {
  return new Promise((resolve) => {
    state._modalResolve = resolve;
    openModal("save-as", "Save As", "Save", state.explorerPath);
    document.getElementById("modal-filename").value = defaultName || "untitled.nex";
  });
}

// ---------------------------------------------------------------- run / stop

function appendOutput(text, cls) {
  const out = document.getElementById("output");
  const span = document.createElement("span");
  if (cls) span.className = cls;
  span.textContent = text;
  out.appendChild(span);
  out.scrollTop = out.scrollHeight;
}

function clearOutput() {
  document.getElementById("output").innerHTML = "";
}

async function runCurrent() {
  const tab = activeTab();
  if (!tab) return;
  if (tab.dirty || !tab.path) {
    const ok = await saveTab(tab);
    if (!ok) return;
  }
  clearOutput();
  appendOutput(`Running ${tab.label}...\n\n`);
  setStatus(`Running ${tab.path}`);
  document.getElementById("run-btn").disabled = true;
  document.getElementById("stop-btn").disabled = false;
  const inputBox = document.getElementById("input-box");
  inputBox.disabled = false;
  inputBox.focus();

  const data = await api("/api/run/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: tab.path }),
  });
  if (data.error) { appendOutput(data.error, "err-text"); resetRunUI(); return; }
  state.runId = data.run_id;

  const es = new EventSource(`/api/run/stream?run_id=${encodeURIComponent(data.run_id)}`);
  state.eventSource = es;
  es.addEventListener("output", (ev) => appendOutput(JSON.parse(ev.data)));
  es.addEventListener("exit", (ev) => {
    appendOutput(`\n[Program exited with code ${ev.data}]\n`);
    resetRunUI();
    es.close();
  });
  es.onerror = () => { resetRunUI(); es.close(); };
}

function resetRunUI() {
  document.getElementById("run-btn").disabled = false;
  document.getElementById("stop-btn").disabled = true;
  document.getElementById("input-box").disabled = true;
  setStatus("Ready");
  state.runId = null;
}

async function stopCurrent() {
  if (!state.runId) return;
  await api("/api/run/stop", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: state.runId }),
  });
  appendOutput("\n[Stopped]\n");
  setStatus("Stopped");
}

document.getElementById("input-box").addEventListener("keydown", async (e) => {
  if (e.key === "Enter" && state.runId) {
    const text = e.target.value;
    e.target.value = "";
    appendOutput(text + "\n");
    await api("/api/run/input", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: state.runId, text }),
    });
  }
});

// ---------------------------------------------------------------- find/replace

function showFindBar(withReplace) {
  const bar = document.getElementById("find-bar");
  bar.hidden = false;
  document.getElementById("replace-input").hidden = !withReplace;
  document.getElementById("replace-one").hidden = !withReplace;
  document.getElementById("replace-all").hidden = !withReplace;
  document.getElementById("find-input").focus();
}

function findNext() {
  const tab = activeTab();
  if (!tab) return;
  const needle = document.getElementById("find-input").value;
  if (!needle) return;
  const ta = tab.textarea;
  const from = ta.selectionEnd || 0;
  let idx = ta.value.indexOf(needle, from);
  if (idx === -1) idx = ta.value.indexOf(needle, 0);
  if (idx === -1) { setStatus(`"${needle}" not found`); return; }
  ta.focus();
  ta.selectionStart = idx;
  ta.selectionEnd = idx + needle.length;
}

function replaceAll() {
  const tab = activeTab();
  if (!tab) return;
  const needle = document.getElementById("find-input").value;
  const replacement = document.getElementById("replace-input").value;
  if (!needle) return;
  const count = tab.textarea.value.split(needle).length - 1;
  tab.textarea.value = tab.textarea.value.split(needle).join(replacement);
  onEditorInput(tab);
  setStatus(`Replaced ${count} occurrence(s)`);
}

function replaceOne() {
  const tab = activeTab();
  if (!tab) return;
  const needle = document.getElementById("find-input").value;
  const replacement = document.getElementById("replace-input").value;
  const ta = tab.textarea;
  if (ta.selectionStart !== ta.selectionEnd &&
      ta.value.slice(ta.selectionStart, ta.selectionEnd) === needle) {
    insertAtCursorRange(ta, replacement);
    onEditorInput(tab);
  }
  findNext();
}

function insertAtCursorRange(textarea, text) {
  const start = textarea.selectionStart, end = textarea.selectionEnd;
  textarea.value = textarea.value.slice(0, start) + text + textarea.value.slice(end);
  textarea.selectionStart = start;
  textarea.selectionEnd = start + text.length;
}

// ---------------------------------------------------------------- menu wiring

function closeAllMenus() {
  document.querySelectorAll(".menu.open").forEach(m => m.classList.remove("open"));
}

document.querySelectorAll(".menu-btn").forEach(btn => {
  btn.addEventListener("click", (e) => {
    const menu = btn.parentElement;
    const wasOpen = menu.classList.contains("open");
    closeAllMenus();
    if (!wasOpen) menu.classList.add("open");
    e.stopPropagation();
  });
});
document.addEventListener("click", closeAllMenus);

const COMMANDS = {
  "new": newFile,
  "open": () => openModal("open-file", "Open File", "Open", state.explorerPath),
  "open-folder": () => openModal("open-folder", "Open Folder", "Open Folder", state.explorerPath),
  "save": () => { const t = activeTab(); if (t) saveTab(t); },
  "save-as": () => { const t = activeTab(); if (t) saveTab(t, true); },
  "close-tab": () => { const t = activeTab(); if (t) closeTab(t.id); },
  "undo": () => document.execCommand("undo"),
  "redo": () => document.execCommand("redo"),
  "find": () => showFindBar(false),
  "replace": () => showFindBar(true),
  "run": runCurrent,
  "stop": stopCurrent,
  "toggle-theme": toggleTheme,
};

document.querySelectorAll("[data-cmd]").forEach(b => {
  b.addEventListener("click", () => { closeAllMenus(); COMMANDS[b.dataset.cmd](); });
});

document.getElementById("run-btn").addEventListener("click", runCurrent);
document.getElementById("stop-btn").addEventListener("click", stopCurrent);
document.getElementById("explorer-open-folder").addEventListener("click", () => COMMANDS["open-folder"]());

document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("modal-cancel").addEventListener("click", closeModal);
document.getElementById("modal-confirm").addEventListener("click", () => confirmModal());

document.getElementById("find-close").addEventListener("click", () => { document.getElementById("find-bar").hidden = true; });
document.getElementById("find-next").addEventListener("click", findNext);
document.getElementById("replace-one").addEventListener("click", replaceOne);
document.getElementById("replace-all").addEventListener("click", replaceAll);
document.getElementById("find-input").addEventListener("keydown", (e) => { if (e.key === "Enter") findNext(); });

window.addEventListener("keydown", (e) => {
  const ctrl = e.ctrlKey || e.metaKey;
  if (ctrl && e.key.toLowerCase() === "n") { e.preventDefault(); newFile(); }
  else if (ctrl && e.key.toLowerCase() === "o") { e.preventDefault(); COMMANDS["open"](); }
  else if (ctrl && e.shiftKey && e.key.toLowerCase() === "s") { e.preventDefault(); COMMANDS["save-as"](); }
  else if (ctrl && e.key.toLowerCase() === "s") { e.preventDefault(); COMMANDS["save"](); }
  else if (ctrl && e.key.toLowerCase() === "w") { e.preventDefault(); COMMANDS["close-tab"](); }
  else if (ctrl && e.key.toLowerCase() === "f") { e.preventDefault(); showFindBar(false); }
  else if (ctrl && e.key.toLowerCase() === "h") { e.preventDefault(); showFindBar(true); }
  else if (e.key === "F5" && !e.shiftKey) { e.preventDefault(); runCurrent(); }
  else if (e.key === "F5" && e.shiftKey) { e.preventDefault(); stopCurrent(); }
  else if (e.key === "Escape") { document.getElementById("find-bar").hidden = true; closeModal(); }
});

// ---------------------------------------------------------------- theme

function toggleTheme() {
  const root = document.documentElement;
  const current = root.getAttribute("data-theme") === "light" ? "dark" : "light";
  root.setAttribute("data-theme", current);
  localStorage.setItem("nexide-theme", current);
}
(function initTheme() {
  const saved = localStorage.getItem("nexide-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
})();

// ---------------------------------------------------------------- PWA install

let deferredInstallPrompt = null;
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  document.getElementById("install-btn").hidden = false;
});
document.getElementById("install-btn").addEventListener("click", async () => {
  if (!deferredInstallPrompt) return;
  deferredInstallPrompt.prompt();
  await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = null;
  document.getElementById("install-btn").hidden = true;
});
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

// ---------------------------------------------------------------- boot

(async function boot() {
  await refreshExplorer(null);
  const params = new URLSearchParams(location.search);
  const openPath = params.get("open");
  if (openPath) {
    try { await openFileAtPath(openPath); return; } catch (e) { /* fall through */ }
  }
  newFile();
})();
