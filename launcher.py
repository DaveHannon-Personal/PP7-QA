#!/usr/bin/env python3
"""
PP7-QA Launcher GUI
A graphical interface for installing, starting, and stopping the PP7-QA app.

Requirements: Python 3.9+ with tkinter (bundled with Python on macOS and Windows).
Run:  python3 launcher.py   (macOS/Linux)
      python  launcher.py   (Windows)
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
ENV_FILE = SCRIPT_DIR / ".env"
ENV_EXAMPLE = SCRIPT_DIR / ".env.example"
COMPOSE_FILE = SCRIPT_DIR / "docker-compose.yml"

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

# ── Colour palette (matches the web app) ──────────────────────────────────────
C = {
    "bg":       "#0f1117",
    "surface":  "#1a1d27",
    "surface2": "#242736",
    "border":   "#2e3347",
    "text":     "#e2e8f0",
    "muted":    "#8892a4",
    "accent":   "#6366f1",
    "success":  "#22c55e",
    "warning":  "#f59e0b",
    "error":    "#ef4444",
}

MODELS = [
    ("llama3.2:3b",  "Fast  ~2 GB RAM  [Recommended]"),
    ("llama3.2:1b",  "Very fast  ~1 GB RAM  (limited reasoning)"),
    ("mistral:7b",   "Better reasoning  ~5 GB RAM"),
    ("llama3.1:8b",  "High quality  ~5 GB RAM"),
]
MODEL_NAMES = [m[0] for m in MODELS]


# =============================================================================
# Helpers
# =============================================================================

def read_env() -> dict:
    """Parse .env file into a dict. Falls back to .env.example if .env is missing."""
    path = ENV_FILE if ENV_FILE.exists() else ENV_EXAMPLE
    result = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
    return result


def write_env(values: dict) -> None:
    """Write/update keys in .env. Creates the file from .env.example if absent."""
    if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
        import shutil as _sh
        _sh.copy(ENV_EXAMPLE, ENV_FILE)

    if ENV_FILE.exists():
        content = ENV_FILE.read_text(encoding="utf-8")
    else:
        content = ""

    for key, val in values.items():
        pattern = rf"(?m)^{re.escape(key)}=.*"
        replacement = f"{key}={val}"
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
        else:
            content = content.rstrip() + f"\n{replacement}\n"

    ENV_FILE.write_text(content, encoding="utf-8")


def run_cmd(args: list, cwd=None, env=None) -> subprocess.Popen:
    """Start a subprocess with merged env, returning the Popen object."""
    merged_env = {**os.environ, **(env or {})}
    # On Windows use CREATE_NO_WINDOW to suppress extra console popups
    kwargs = dict(
        args=args,
        cwd=cwd or str(SCRIPT_DIR),
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if IS_WIN:
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(**kwargs)


def quick_check(args: list) -> bool:
    """Return True if command exits with code 0 (silently)."""
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
        return result.returncode == 0
    except Exception:
        return False


def open_browser(url: str) -> None:
    webbrowser.open(url)


# =============================================================================
# Main Application
# =============================================================================

class LauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PP7-QA Launcher")
        self.geometry("740x820")
        self.minsize(640, 700)
        self.configure(bg=C["bg"])
        if IS_MAC:
            self.createcommand("tk::mac::Quit", self.on_quit)

        # ── State variables ────────────────────────────────────────────────
        env = read_env()
        self.model_var      = tk.StringVar(value=env.get("OLLAMA_MODEL", "llama3.2:3b"))
        self.api_mem_var    = tk.StringVar(value=env.get("API_MEMORY", "1g"))
        self.fe_mem_var     = tk.StringVar(value=env.get("FRONTEND_MEMORY", "512m"))
        self.api_port_var   = tk.StringVar(value=env.get("API_PORT", "8000"))
        self.fe_port_var    = tk.StringVar(value=env.get("FRONTEND_PORT", "3000"))
        self.detach_var     = tk.BooleanVar(value=False)
        self.build_var      = tk.BooleanVar(value=False)
        self._running_proc  = None
        self._status_cache  = {}

        self._apply_style()
        self._build_ui()

        # Kick off background status check after window is visible
        self.after(300, self._refresh_status_async)

    # ── ttk Style ─────────────────────────────────────────────────────────────
    def _apply_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".",
            background=C["bg"],
            foreground=C["text"],
            fieldbackground=C["surface2"],
            troughcolor=C["surface"],
            bordercolor=C["border"],
            darkcolor=C["border"],
            lightcolor=C["border"],
            insertcolor=C["text"],
            selectbackground=C["accent"],
            selectforeground="#ffffff",
            font=("Helvetica Neue", 12) if IS_MAC else ("Segoe UI", 10),
        )
        style.configure("TNotebook",
            background=C["surface"],
            borderwidth=0,
            tabmargins=[0, 0, 0, 0],
        )
        style.configure("TNotebook.Tab",
            background=C["surface"],
            foreground=C["muted"],
            padding=[16, 8],
            borderwidth=0,
            font=("Helvetica Neue", 12) if IS_MAC else ("Segoe UI", 10),
        )
        style.map("TNotebook.Tab",
            background=[("selected", C["surface2"])],
            foreground=[("selected", C["text"])],
        )
        style.configure("TFrame", background=C["bg"])
        style.configure("Surface.TFrame", background=C["surface"])
        style.configure("TLabel", background=C["bg"], foreground=C["text"])
        style.configure("Surface.TLabel", background=C["surface"], foreground=C["text"])
        style.configure("Muted.TLabel", background=C["bg"], foreground=C["muted"])
        style.configure("TEntry",
            fieldbackground=C["surface2"],
            foreground=C["text"],
            bordercolor=C["border"],
            insertcolor=C["text"],
            padding=6,
        )
        style.configure("TCombobox",
            fieldbackground=C["surface2"],
            background=C["surface2"],
            foreground=C["text"],
            arrowcolor=C["muted"],
            bordercolor=C["border"],
        )
        style.map("TCombobox",
            fieldbackground=[("readonly", C["surface2"])],
            foreground=[("readonly", C["text"])],
        )
        style.configure("TCheckbutton",
            background=C["bg"],
            foreground=C["text"],
        )
        style.configure("TSeparator", background=C["border"])
        style.configure("TScrollbar",
            background=C["surface2"],
            troughcolor=C["bg"],
            bordercolor=C["border"],
            arrowcolor=C["muted"],
        )

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=C["surface"], pady=16)
        header.pack(fill="x", padx=0)
        tk.Label(header, text="PP7-QA Launcher",
                 bg=C["surface"], fg=C["accent"],
                 font=("Helvetica Neue", 20, "bold") if IS_MAC else ("Segoe UI", 16, "bold")
                 ).pack(side="left", padx=20)
        tk.Label(header, text="ProPresenter 7 · AI Quality Assurance",
                 bg=C["surface"], fg=C["muted"],
                 font=("Helvetica Neue", 12) if IS_MAC else ("Segoe UI", 9)
                 ).pack(side="left", padx=4)

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # Status bar
        self._build_status_bar()

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # Notebook (tabs)
        notebook_frame = tk.Frame(self, bg=C["bg"])
        notebook_frame.pack(fill="both", expand=True, padx=0)

        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_setup_tab()
        self._build_launch_tab()
        self._build_status_tab()

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # Log pane
        self._build_log_pane()

    def _build_status_bar(self):
        bar = tk.Frame(self, bg=C["surface"], pady=10)
        bar.pack(fill="x")

        self._status_indicators = {}
        for key, label in [("docker", "Docker"), ("ollama", "Ollama"), ("app", "App")]:
            f = tk.Frame(bar, bg=C["surface"])
            f.pack(side="left", padx=16)
            dot = tk.Label(f, text="●", bg=C["surface"], fg=C["muted"], font=("Helvetica Neue", 14) if IS_MAC else ("Segoe UI", 12))
            dot.pack(side="left", padx=(0, 4))
            tk.Label(f, text=label, bg=C["surface"], fg=C["muted"],
                     font=("Helvetica Neue", 11) if IS_MAC else ("Segoe UI", 9)).pack(side="left")
            self._status_indicators[key] = dot

        refresh_btn = self._btn(bar, "⟳ Refresh", self._refresh_status_async, small=True)
        refresh_btn.pack(side="right", padx=16)

        open_btn = self._btn(bar, "Open App ↗", self._open_browser, small=True, accent=True)
        open_btn.pack(side="right", padx=4)

    def _build_setup_tab(self):
        frame = tk.Frame(self.notebook, bg=C["bg"])
        self.notebook.add(frame, text="  Setup  ")

        # Scroll canvas for setup tab
        canvas = tk.Canvas(frame, bg=C["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=C["bg"])

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        pad = {"padx": 16, "pady": 6}

        # ── Prerequisites section ──────────────────────────────────────────
        self._section(inner, "Prerequisites")

        self._prereq_checks = {}
        prereqs = [
            ("docker", "Docker Desktop / Engine"),
            ("compose", "Docker Compose v2"),
            ("ollama", "Ollama"),
        ]
        for key, label in prereqs:
            row = tk.Frame(inner, bg=C["bg"])
            row.pack(fill="x", **pad)
            dot = tk.Label(row, text="●", bg=C["bg"], fg=C["muted"],
                           font=("Helvetica Neue", 14) if IS_MAC else ("Segoe UI", 12))
            dot.pack(side="left", padx=(0, 8))
            tk.Label(row, text=label, bg=C["bg"], fg=C["text"],
                     font=("Helvetica Neue", 12) if IS_MAC else ("Segoe UI", 10)).pack(side="left")
            self._prereq_checks[key] = dot

        btn_row = tk.Frame(inner, bg=C["bg"])
        btn_row.pack(fill="x", padx=16, pady=(4, 12))
        self._btn(btn_row, "Check Prerequisites", self._check_prereqs).pack(side="left", padx=(0, 8))
        if IS_MAC:
            self._btn(btn_row, "Install Docker (Homebrew)", lambda: self._install_tool("docker")).pack(side="left", padx=(0, 8))
            self._btn(btn_row, "Install Ollama (Homebrew)", lambda: self._install_tool("ollama")).pack(side="left")
        elif IS_WIN:
            self._btn(btn_row, "Download Docker Desktop", lambda: webbrowser.open("https://www.docker.com/products/docker-desktop/")).pack(side="left", padx=(0, 8))
            self._btn(btn_row, "Download & Install Ollama", self._install_ollama_windows).pack(side="left")

        # ── AI Model section ───────────────────────────────────────────────
        self._section(inner, "AI Model")

        model_row = tk.Frame(inner, bg=C["bg"])
        model_row.pack(fill="x", padx=16, pady=6)
        tk.Label(model_row, text="Select model:", bg=C["bg"], fg=C["muted"],
                 font=("Helvetica Neue", 11) if IS_MAC else ("Segoe UI", 9)).pack(side="left", padx=(0, 8))
        self._setup_model_combo = ttk.Combobox(model_row, textvariable=self.model_var,
                                               values=MODEL_NAMES, state="readonly", width=20)
        self._setup_model_combo.pack(side="left", padx=(0, 8))
        self._setup_model_combo.bind("<<ComboboxSelected>>", self._on_model_selected)

        self._model_desc = tk.Label(model_row, text=self._get_model_desc(self.model_var.get()),
                                    bg=C["bg"], fg=C["muted"],
                                    font=("Helvetica Neue", 10) if IS_MAC else ("Segoe UI", 9))
        self._model_desc.pack(side="left")

        pull_row = tk.Frame(inner, bg=C["bg"])
        pull_row.pack(fill="x", padx=16, pady=(2, 12))
        self._btn(pull_row, "Pull Selected Model", self._pull_model).pack(side="left", padx=(0, 8))
        self._model_status = tk.Label(pull_row, text="", bg=C["bg"], fg=C["muted"],
                                      font=("Helvetica Neue", 11) if IS_MAC else ("Segoe UI", 9))
        self._model_status.pack(side="left")

        # ── Config file section ────────────────────────────────────────────
        self._section(inner, "Configuration File")

        cfg_info = tk.Frame(inner, bg=C["surface"], padx=12, pady=8)
        cfg_info.pack(fill="x", padx=16, pady=(0, 8))
        env_path_str = str(ENV_FILE)
        exists = ENV_FILE.exists()
        tk.Label(cfg_info, text=f"{'✔  .env exists' if exists else '✖  .env not found'}",
                 bg=C["surface"], fg=C["success"] if exists else C["error"],
                 font=("Helvetica Neue", 11) if IS_MAC else ("Segoe UI", 9)).pack(anchor="w")
        tk.Label(cfg_info, text=env_path_str, bg=C["surface"], fg=C["muted"],
                 font=("Courier", 10) if IS_MAC else ("Consolas", 9)).pack(anchor="w")

        cfg_btn_row = tk.Frame(inner, bg=C["bg"])
        cfg_btn_row.pack(fill="x", padx=16, pady=(0, 12))
        self._btn(cfg_btn_row, "Create .env from template", self._create_env).pack(side="left", padx=(0, 8))

        # ── Run full setup button ──────────────────────────────────────────
        sep = tk.Frame(inner, bg=C["border"], height=1)
        sep.pack(fill="x", padx=16, pady=8)

        full_setup_row = tk.Frame(inner, bg=C["bg"])
        full_setup_row.pack(fill="x", padx=16, pady=(0, 16))
        self._btn(full_setup_row, "▶  Run Full Setup", self._run_full_setup, accent=True, big=True).pack(side="left")
        tk.Label(full_setup_row, text="  Checks everything and pulls the selected model",
                 bg=C["bg"], fg=C["muted"],
                 font=("Helvetica Neue", 11) if IS_MAC else ("Segoe UI", 9)).pack(side="left")

    def _build_launch_tab(self):
        frame = tk.Frame(self.notebook, bg=C["bg"])
        self.notebook.add(frame, text="  Launch  ")

        # Config section
        self._section(frame, "Configuration")
        cfg_grid = tk.Frame(frame, bg=C["bg"])
        cfg_grid.pack(fill="x", padx=16, pady=(0, 8))
        cfg_grid.columnconfigure(1, weight=1)
        cfg_grid.columnconfigure(3, weight=1)

        fields = [
            ("AI Model",          self.model_var,    "llama3.2:3b",   0, 0),
            ("API Memory",        self.api_mem_var,  "e.g. 1g, 512m", 1, 0),
            ("Frontend Memory",   self.fe_mem_var,   "e.g. 512m",     2, 0),
            ("API Port",          self.api_port_var, "8000",          1, 2),
            ("Frontend Port",     self.fe_port_var,  "3000",          2, 2),
        ]

        lbl_font = ("Helvetica Neue", 11) if IS_MAC else ("Segoe UI", 9)

        for label, var, placeholder, row, col in fields:
            tk.Label(cfg_grid, text=label + ":", bg=C["bg"], fg=C["muted"],
                     font=lbl_font, anchor="e", width=16
                     ).grid(row=row, column=col, sticky="e", padx=(8, 6), pady=4)
            if label == "AI Model":
                w = ttk.Combobox(cfg_grid, textvariable=var, values=MODEL_NAMES,
                                 state="readonly", width=18)
                w.grid(row=row, column=col + 1, sticky="w", pady=4)
            else:
                e = ttk.Entry(cfg_grid, textvariable=var, width=12)
                e.grid(row=row, column=col + 1, sticky="w", pady=4)

        # Note about memory limits
        note = tk.Label(frame,
            text="ℹ  On macOS, Docker's total VM memory is set in Docker Desktop → Settings → Resources",
            bg=C["bg"], fg=C["muted"],
            font=("Helvetica Neue", 10) if IS_MAC else ("Segoe UI", 8))
        note.pack(anchor="w", padx=24, pady=(0, 8))

        # Options
        opts = tk.Frame(frame, bg=C["bg"])
        opts.pack(fill="x", padx=20, pady=(0, 12))
        ttk.Checkbutton(opts, text="Run in background (detached)", variable=self.detach_var).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(opts, text="Force rebuild images", variable=self.build_var).pack(side="left")

        sep = tk.Frame(frame, bg=C["border"], height=1)
        sep.pack(fill="x", padx=16, pady=8)

        # Action buttons
        self._section(frame, "Actions")
        btn_row = tk.Frame(frame, bg=C["bg"])
        btn_row.pack(fill="x", padx=16, pady=(0, 16))

        self._start_btn = self._btn(btn_row, "▶  Start App", self._do_start, accent=True, big=True)
        self._start_btn.pack(side="left", padx=(0, 10))

        self._stop_btn = self._btn(btn_row, "⏹  Stop", self._do_stop, big=True)
        self._stop_btn.pack(side="left", padx=(0, 10))

        self._btn(btn_row, "⏹  Stop + Reset DB", self._do_stop_clean, big=True).pack(side="left")

        sep2 = tk.Frame(frame, bg=C["border"], height=1)
        sep2.pack(fill="x", padx=16, pady=8)

        # Quick links
        self._section(frame, "Quick Links")
        links = tk.Frame(frame, bg=C["bg"])
        links.pack(fill="x", padx=16, pady=(0, 16))
        fe_port = self.fe_port_var.get() or "3000"
        api_port = self.api_port_var.get() or "8000"
        self._btn(links, f"Open App  http://localhost:{fe_port}",
                  lambda: open_browser(f"http://localhost:{self.fe_port_var.get()}"),
                  small=True).pack(side="left", padx=(0, 10))
        self._btn(links, f"API Docs  http://localhost:{api_port}/docs",
                  lambda: open_browser(f"http://localhost:{self.api_port_var.get()}/docs"),
                  small=True).pack(side="left")

    def _build_status_tab(self):
        frame = tk.Frame(self.notebook, bg=C["bg"])
        self.notebook.add(frame, text="  Status  ")

        self._section(frame, "Container Status")

        # Status table (using a Text widget as a table)
        self._status_text = tk.Text(
            frame,
            bg=C["surface"],
            fg=C["text"],
            font=("Courier", 11) if IS_MAC else ("Consolas", 9),
            relief="flat",
            state="disabled",
            height=8,
            padx=12,
            pady=8,
        )
        self._status_text.pack(fill="x", padx=16, pady=(0, 12))

        btn_row = tk.Frame(frame, bg=C["bg"])
        btn_row.pack(fill="x", padx=16, pady=(0, 8))
        self._btn(btn_row, "⟳ Refresh Status", self._refresh_status_async, small=True).pack(side="left", padx=(0, 8))
        self._btn(btn_row, "View Logs", self._view_logs, small=True).pack(side="left")

    def _build_log_pane(self):
        log_header = tk.Frame(self, bg=C["surface"], pady=6)
        log_header.pack(fill="x")

        tk.Label(log_header, text="Output Log", bg=C["surface"], fg=C["muted"],
                 font=("Helvetica Neue", 11, "bold") if IS_MAC else ("Segoe UI", 9, "bold")
                 ).pack(side="left", padx=16)
        self._btn(log_header, "Clear", self._clear_log, small=True).pack(side="right", padx=12)

        log_frame = tk.Frame(self, bg=C["bg"])
        log_frame.pack(fill="both", expand=False, padx=16, pady=(6, 12))

        self.log = tk.Text(
            log_frame,
            bg=C["bg"],
            fg=C["text"],
            font=("Courier", 11) if IS_MAC else ("Consolas", 9),
            relief="flat",
            state="disabled",
            height=10,
            padx=8,
            pady=4,
            insertbackground=C["text"],
            selectbackground=C["accent"],
        )
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        # Tag colours
        self.log.tag_configure("ok",      foreground=C["success"])
        self.log.tag_configure("warn",    foreground=C["warning"])
        self.log.tag_configure("err",     foreground=C["error"])
        self.log.tag_configure("info",    foreground=C["accent"])
        self.log.tag_configure("muted",   foreground=C["muted"])

    # ── Widget factory helpers ─────────────────────────────────────────────────
    def _btn(self, parent, text, command, small=False, accent=False, big=False, danger=False):
        if accent:
            bg, fg, abg = C["accent"], "#ffffff", "#818cf8"
        elif danger:
            bg, fg, abg = C["error"], "#ffffff", "#f87171"
        else:
            bg, fg, abg = C["surface2"], C["text"], C["border"]

        font_size = 10 if IS_MAC else 9
        if big:
            font_size = 13 if IS_MAC else 10
        if small:
            font_size = 10 if IS_MAC else 8
        pad_x = 8 if small else (16 if big else 12)
        pad_y = 4 if small else (8 if big else 6)

        btn = tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg, activebackground=abg, activeforeground=fg,
            relief="flat", cursor="hand2",
            font=("Helvetica Neue", font_size) if IS_MAC else ("Segoe UI", font_size),
            padx=pad_x, pady=pad_y,
        )
        return btn

    def _section(self, parent, title):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(row, text=title, bg=C["bg"], fg=C["text"],
                 font=("Helvetica Neue", 13, "bold") if IS_MAC else ("Segoe UI", 10, "bold")
                 ).pack(side="left")
        sep = tk.Frame(row, bg=C["border"], height=1)
        sep.pack(side="left", fill="x", expand=True, padx=(8, 0), pady=6)

    # ── Log helpers ───────────────────────────────────────────────────────────
    def log_write(self, text: str, tag: str = ""):
        def _do():
            self.log.configure(state="normal")
            self.log.insert("end", text, tag)
            self.log.see("end")
            self.log.configure(state="disabled")
        self.after(0, _do)

    def log_line(self, text: str, tag: str = ""):
        self.log_write(text.rstrip() + "\n", tag)

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ── Status ────────────────────────────────────────────────────────────────
    def _set_status_dot(self, key: str, state: str):
        """state: 'ok' | 'warn' | 'off'"""
        color = {"ok": C["success"], "warn": C["warning"], "off": C["muted"]}.get(state, C["muted"])
        def _do():
            if key in self._status_indicators:
                self._status_indicators[key].configure(fg=color)
        self.after(0, _do)

    def _refresh_status_async(self):
        threading.Thread(target=self._check_status_thread, daemon=True).start()

    def _check_status_thread(self):
        # Docker
        docker_ok = quick_check(["docker", "info"])
        self._set_status_dot("docker", "ok" if docker_ok else "off")

        # Ollama
        import urllib.request
        ollama_ok = False
        try:
            urllib.request.urlopen("http://localhost:11434/v1/models", timeout=4)
            ollama_ok = True
        except Exception:
            pass
        self._set_status_dot("ollama", "ok" if ollama_ok else "off")

        # Containers
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd=str(SCRIPT_DIR),
                capture_output=True, text=True, timeout=10,
            )
            containers = []
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    try:
                        containers.append(json.loads(line))
                    except Exception:
                        pass
            running = any(c.get("State") == "running" for c in containers)
            self._set_status_dot("app", "ok" if running else "off")
            self._update_status_table(containers)
        except Exception:
            self._set_status_dot("app", "off")
            self._update_status_table([])

    def _update_status_table(self, containers: list):
        lines = []
        if not containers:
            lines.append("  No containers running.\n  Start the app with the Launch tab.")
        else:
            lines.append(f"  {'NAME':<20} {'STATE':<12} {'PORTS'}")
            lines.append("  " + "-" * 60)
            for c in containers:
                name  = c.get("Name", c.get("Service", "?"))
                state = c.get("State", "?")
                ports = c.get("Publishers", [])
                port_str = ", ".join(
                    f"{p.get('PublishedPort')}→{p.get('TargetPort')}"
                    for p in ports if p.get("PublishedPort")
                ) if ports else c.get("Ports", "")
                lines.append(f"  {name:<20} {state:<12} {port_str}")
        text = "\n".join(lines)
        def _do():
            self._status_text.configure(state="normal")
            self._status_text.delete("1.0", "end")
            self._status_text.insert("1.0", text)
            self._status_text.configure(state="disabled")
        self.after(0, _do)

    # ── Command runner ────────────────────────────────────────────────────────
    def _stream_process(self, proc: subprocess.Popen, on_done=None):
        """Read stdout/stderr lines in background, write to log. Call on_done when finished.
        Handles both \\n-terminated lines and \\r-terminated progress lines (e.g. ollama pull)."""
        def _run():
            buf = ""
            while True:
                ch = proc.stdout.read(1)
                if not ch:
                    break
                if ch in ("\n", "\r"):
                    line = buf.strip()
                    buf = ""
                    if not line:
                        continue
                    tag = ""
                    if any(w in line.lower() for w in ("error", "failed", "fatal")):
                        tag = "err"
                    elif any(w in line.lower() for w in ("warning", "warn")):
                        tag = "warn"
                    elif any(w in line.lower() for w in ("done", "successfully", "pulled", "started", "running")):
                        tag = "ok"
                    self.log_write(line + "\n", tag)
                else:
                    buf += ch
            if buf.strip():
                self.log_write(buf.strip() + "\n", "")
            proc.wait()
            if on_done:
                self.after(0, on_done)
        threading.Thread(target=_run, daemon=True).start()

    # ── Setup tab actions ─────────────────────────────────────────────────────
    def _check_prereqs(self):
        def _run():
            checks = {
                "docker":  (["docker", "--version"], "docker"),
                "compose": (["docker", "compose", "version"], "compose"),
                "ollama":  (["ollama", "--version"], "ollama"),
            }
            self.log_line("── Checking prerequisites ──", "info")
            for key, (cmd, dot_key) in checks.items():
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
                    version = r.stdout.strip().splitlines()[0] if r.stdout.strip() else "(ok)"
                    self.log_line(f"  ✔  {version}", "ok")
                    self.after(0, lambda k=dot_key: self._prereq_checks[k].configure(fg=C["success"]))
                except FileNotFoundError:
                    self.log_line(f"  ✖  {key} not found — install it and re-run", "err")
                    self.after(0, lambda k=dot_key: self._prereq_checks[k].configure(fg=C["error"]))
                except Exception as e:
                    self.log_line(f"  ⚠  {key}: {e}", "warn")
                    self.after(0, lambda k=dot_key: self._prereq_checks[k].configure(fg=C["warning"]))
            self.log_line("── Done ──", "info")
        threading.Thread(target=_run, daemon=True).start()

    def _install_tool(self, tool: str):
        cmd_map = {
            "docker": ["brew", "install", "--cask", "docker"],
            "ollama": ["brew", "install", "ollama"],
        }
        cmd = cmd_map.get(tool)
        if not cmd:
            return
        self.log_line(f"── Installing {tool} via Homebrew ──", "info")
        proc = run_cmd(cmd)
        self._stream_process(proc, on_done=self._check_prereqs)

    def _install_ollama_windows(self):
        """Try winget first; fall back to opening the download page."""
        if shutil.which("winget"):
            self.log_line("── Installing Ollama via winget ──", "info")
            self.log_line("   This may take a minute. Check progress in the log below.", "muted")
            proc = run_cmd(["winget", "install", "--id", "Ollama.Ollama", "-e", "--accept-package-agreements", "--accept-source-agreements"])
            def _done():
                self.log_line("✔  Ollama installed — restart this launcher to use it", "ok")
                self._check_prereqs()
            self._stream_process(proc, on_done=_done)
        else:
            self.log_line("winget not available — opening Ollama download page", "warn")
            webbrowser.open("https://ollama.com/download/windows")

    def _model_already_pulled(self, model: str) -> bool:
        """Return True if the model is already present in ollama."""
        try:
            r = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=8
            )
            return model.lower() in r.stdout.lower()
        except Exception:
            return False

    def _pull_model(self):
        model = self.model_var.get().strip()
        if not model:
            return
        if self._model_already_pulled(model):
            self.log_line(f"✔  Model '{model}' is already present — skipping pull", "ok")
            self.after(0, lambda: self._model_status.configure(text="✔ Already present", fg=C["success"]))
            write_env({"OLLAMA_MODEL": model})
            return
        self.log_line(f"── Pulling model: {model} ──", "info")
        self.after(0, lambda: self._model_status.configure(text="Pulling…", fg=C["warning"]))
        def _done():
            self._model_status.configure(text="✔ Done", fg=C["success"])
            write_env({"OLLAMA_MODEL": model})
        proc = run_cmd(["ollama", "pull", model])
        self._stream_process(proc, on_done=_done)

    def _create_env(self):
        if not ENV_EXAMPLE.exists():
            self.log_line("✖  .env.example not found", "err")
            return
        if ENV_FILE.exists():
            if not messagebox.askyesno("Overwrite?", ".env already exists. Overwrite with defaults?"):
                return
        import shutil as _sh
        _sh.copy(ENV_EXAMPLE, ENV_FILE)
        self.log_line(f"✔  .env created at {ENV_FILE}", "ok")

    def _run_full_setup(self):
        """Sequentially: check prereqs → create .env → pull model."""
        def _run():
            self.log_line("══ Full Setup Starting ══", "info")
            self._check_prereqs()
            # Give check_prereqs time to finish (it's threaded internally too)
            import time; time.sleep(2)
            if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
                import shutil as _sh; _sh.copy(ENV_EXAMPLE, ENV_FILE)
                self.log_line("✔  .env created", "ok")
            model = self.model_var.get().strip()
            if model and shutil.which("ollama"):
                if self._model_already_pulled(model):
                    self.log_line(f"✔  Model '{model}' already present — skipping pull", "ok")
                    self.log_line("══ Setup Complete ══", "ok")
                else:
                    self.log_line(f"── Pulling model {model} ──", "info")
                    proc = run_cmd(["ollama", "pull", model])
                    self._stream_process(proc, on_done=lambda: self.log_line("══ Setup Complete ══", "ok"))
            else:
                self.log_line("══ Setup Complete ══", "ok")
        threading.Thread(target=_run, daemon=True).start()

    # ── Launch tab actions ────────────────────────────────────────────────────
    def _save_config(self):
        write_env({
            "OLLAMA_MODEL":    self.model_var.get().strip(),
            "API_MEMORY":      self.api_mem_var.get().strip(),
            "FRONTEND_MEMORY": self.fe_mem_var.get().strip(),
            "API_PORT":        self.api_port_var.get().strip(),
            "FRONTEND_PORT":   self.fe_port_var.get().strip(),
        })

    def _do_start(self):
        self._save_config()
        args = ["docker", "compose", "up"]
        if self.build_var.get():
            args.append("--build")
        if self.detach_var.get():
            args.append("-d")
        self.log_line("── Starting PP7-QA ──", "info")
        self.log_line(f"   {' '.join(args)}", "muted")

        proc = run_cmd(args)
        self._running_proc = proc

        def _done():
            self._running_proc = None
            self._refresh_status_async()
            if self.detach_var.get():
                port = self.fe_port_var.get() or "3000"
                self.log_line(f"✔  App running — http://localhost:{port}", "ok")

        self._stream_process(proc, on_done=_done)

    def _do_stop(self):
        self.log_line("── Stopping PP7-QA ──", "info")
        proc = run_cmd(["docker", "compose", "down"])
        def _done():
            self._refresh_status_async()
            self.log_line("✔  Stopped", "ok")
        self._stream_process(proc, on_done=_done)

    def _do_stop_clean(self):
        if not messagebox.askyesno(
            "Reset Database?",
            "This will remove the data volume — all rules, profiles, and settings will be deleted.\n\nContinue?",
        ):
            return
        self.log_line("── Stopping + removing volumes ──", "warn")
        proc = run_cmd(["docker", "compose", "down", "-v"])
        def _done():
            self._refresh_status_async()
            self.log_line("✔  Stopped and data reset", "ok")
        self._stream_process(proc, on_done=_done)

    # ── Status tab actions ────────────────────────────────────────────────────
    def _view_logs(self):
        self.log_line("── Container logs (last 50 lines) ──", "info")
        proc = run_cmd(["docker", "compose", "logs", "--tail=50"])
        self._stream_process(proc)

    # ── Browser ──────────────────────────────────────────────────────────────
    def _open_browser(self):
        port = self.fe_port_var.get() or "3000"
        open_browser(f"http://localhost:{port}")

    # ── Model helpers ─────────────────────────────────────────────────────────
    def _get_model_desc(self, name: str) -> str:
        for n, d in MODELS:
            if n == name:
                return d
        return ""

    def _on_model_selected(self, _event=None):
        desc = self._get_model_desc(self.model_var.get())
        self._model_desc.configure(text=desc)

    # ── Misc ──────────────────────────────────────────────────────────────────
    def on_quit(self):
        if self._running_proc and self._running_proc.poll() is None:
            if messagebox.askyesno("Quit", "Containers may still be running. Quit anyway?"):
                self.destroy()
        else:
            self.destroy()


# =============================================================================
# Entry point
# =============================================================================

def main():
    # Check tkinter is available
    try:
        import tkinter  # noqa
    except ImportError:
        print("ERROR: tkinter is not available.")
        if platform.system() == "Darwin":
            print("Install it with: brew install python-tk")
        elif platform.system() == "Linux":
            print("Install it with: sudo apt install python3-tk")
        sys.exit(1)

    app = LauncherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
