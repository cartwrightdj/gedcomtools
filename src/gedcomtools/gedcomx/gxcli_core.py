#!/usr/bin/env python3
"""Core Shell class for the GedcomX interactive shell."""
from __future__ import annotations

# ======================================================================
#  Project: gedcomtools
#  File:    gxcli_core.py
#  Purpose: Shell class assembled from mixin components.
#  Created: 2026-03-31 — split from gxcli.py
# ======================================================================
import glob as _glob_mod
import os
import shlex
import sys
import traceback
from typing import Any

from gedcomtools.gedcomx.gxcli_output import (
    ANSI,
    NO_DATA,
    SHELL_VERSION,
    _DEFAULT_SETTINGS,
    _HISTORY_PATH,
    _load_settings,
    list_fields,
)
from gedcomtools.gedcomx.gxcli_commands import (
    _InfoMixin,
    _AhnenMixin,
    _NavMixin,
    _LoadMixin,
    _DataMixin,
)
from gedcomtools.gedcomx.gxcli_schema import _SchemaMixin

# readline is optional
try:
    import readline as _readline
    _READLINE = True
except ImportError:
    _readline = None  # type: ignore[assignment]
    _READLINE = False

import gedcomtools.gedcomx.gxcli_output as _gxcli_output_module


class Shell(_NavMixin, _LoadMixin, _AhnenMixin, _DataMixin, _InfoMixin, _SchemaMixin):
    """Implement the interactive GedcomX shell interface."""

    def __init__(self, root: Any | None = None):
        self.gedcomx: Any | None = None
        self.root = root
        self.cur = root
        self.path: list[str] = []
        self.use_color = sys.stdout.isatty() or ("WT_SESSION" in os.environ)
        self.status = NO_DATA
        self.version = SHELL_VERSION
        # Set by run(); commands can test this to skip interactive-only behaviour.
        self._interactive: bool = True
        # Navigation history (back command)
        self._nav_history: list[tuple[Any, list[str]]] = []
        # Named bookmarks
        self._bookmarks: dict[str, tuple[Any, list[str]]] = {}
        # Persistent settings
        self._settings: dict[str, Any] = _load_settings()
        # Ahnentafel working set: number → entry dict
        self._ahnen: dict[int, dict] = {}

        self.commands = {
            "agentstbl": self._cmd_agenttbl,
            "back": self._cmd_back,
            "bm": self._cmd_bookmark,
            "bookmark": self._cmd_bookmark,
            "call": self._cmd_call,
            "cd": self._cmd_cd,
            "cfg": self._cmd_cfg,
            "del": self._cmd_del,
            "diff": self._cmd_diff,
            "ext": self._cmd_ext,
            "extension": self._cmd_ext,
            "extend": self._cmd_extend,
            "extras": self._cmd_extras,
            "find": self._cmd_find,
            "getattr": self._cmd_getattr,
            "getprop": self._cmd_getprop,
            "go": self._cmd_go,
            "goto": self._cmd_goto,
            "grep": self._cmd_grep,
            "help": self._cmd_help,
            "?": self._cmd_help,
            "history": self._cmd_history,
            "ld": self._cmd_load,
            "load": self._cmd_load,
            "log": self._cmd_log,
            "ls": self._cmd_ls,
            "list": self._cmd_ls,
            "methods": self._cmd_methods,
            "props": self._cmd_props,
            "pwd": self._cmd_pwd,
            "resolve": self._cmd_resolve,
            "schema": self._cmd_schema,
            "set": self._cmd_set,
            "stats": self._cmd_stats,
            "dump": self._cmd_dump,
            "show": self._cmd_show,
            "type": self._cmd_type,
            "ahnen": self._cmd_ahnen,
            "ahnentafel": self._cmd_ahnen,
            "validate": self._cmd_validate,
            "ver": self._cmd_ver,
            "write": self._cmd_write,
        }

    def prompt(self) -> str:
        """Return the current shell prompt string."""
        return "gx:/" + "/".join(self.path) + "> "

    def _make_tab_completer(self):
        """Return a readline-compatible completer function."""
        def completer(text: str, state: int):
            try:
                line = _readline.get_line_buffer()
                before = line[:_readline.get_begidx()]
                try:
                    tokens = shlex.split(before, posix=True) if before.strip() else []
                except ValueError:
                    tokens = before.split()

                if not tokens:
                    matches = sorted(c for c in self.commands if c.startswith(text))
                else:
                    cmd = tokens[0].lower()
                    ntok = len(tokens)
                    if ntok == 1:
                        if cmd in ("go",):
                            matches = sorted(b for b in self._bookmarks if b.startswith(text))
                        elif cmd == "goto":
                            idx = self.gedcomx.id_index if self.gedcomx else {}
                            matches = sorted(str(k) for k in idx if str(k).startswith(text))
                        elif cmd in ("cd", "show", "dump", "type", "grep", "ls"):
                            fields = list_fields(self.cur) if self.cur is not None else []
                            matches = sorted(str(k) for k, _ in fields if str(k).startswith(text))
                        elif cmd in ("load", "extend", "diff"):
                            matches = _glob_mod.glob(text + "*")
                        elif cmd == "write":
                            matches = [f for f in ["gx ", "zip ", "jsonl ", "adbg "] if f.startswith(text)]
                        elif cmd in ("ext", "extension"):
                            matches = [s for s in ["ls", "show", "scan", "authorize", "load", "trust"] if s.startswith(text)]
                        elif cmd == "cfg":
                            matches = sorted(k for k in _DEFAULT_SETTINGS if k.startswith(text))
                        elif cmd == "bookmark":
                            matches = [s for s in ["ls", "rm"] if s.startswith(text)]
                        else:
                            matches = []
                    else:
                        matches = []

                return matches[state] if state < len(matches) else None
            except (AttributeError, TypeError, KeyError):
                return None
        return completer

    def run(self) -> None:
        """Run the interactive shell loop."""
        self._interactive = sys.stdin.isatty()

        # Disable ANSI escape codes when stdout is piped (not a real terminal).
        if not sys.stdout.isatty():
            # Mutate the module-level ANSI dict so all consumers see empty strings.
            _gxcli_output_module.ANSI.update({k: "" for k in _gxcli_output_module.ANSI})
            _gxcli_output_module._RED = ""
            _gxcli_output_module._RESET = ""

        # Set up readline (tab completion + persistent history) for interactive sessions.
        if self._interactive and _READLINE:
            try:
                _readline.set_history_length(self._settings.get("history_size", 200))
                _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
                try:
                    _readline.read_history_file(str(_HISTORY_PATH))
                except FileNotFoundError:
                    pass
                _readline.set_completer(self._make_tab_completer())
                _readline.set_completer_delims(" \t\n")
                _readline.parse_and_bind("tab: complete")
                import atexit as _atexit
                _atexit.register(lambda: _readline.write_history_file(str(_HISTORY_PATH)))
            except (ImportError, OSError, AttributeError):
                pass

        if self._interactive:
            print(f"Entering GEDCOM-X browser ({self.version}) Type 'help' for commands, 'quit' to exit.")

        while True:
            try:
                if self._interactive:
                    line = input(self.prompt()).strip()
                else:
                    raw = sys.stdin.readline()
                    if not raw:          # EOF — pipe closed
                        break
                    line = raw.rstrip("\r\n").strip()
            except (EOFError, KeyboardInterrupt):
                if self._interactive:
                    print()
                return

            if not line:
                continue

            try:
                parts = shlex.split(line, posix=not sys.platform.startswith("win"))
            except ValueError as e:
                tb = e.__traceback__
                last = traceback.extract_tb(tb)[-1]

                print(f"! Parse error ({last.filename}:{last.lineno}): {e}")
                continue

            if not parts:
                continue

            cmd, *args = parts

            if cmd in ("quit", "exit"):
                return

            handler = self.commands.get(cmd)
            if not handler:
                print(f"Unknown command: {cmd}. Try 'help'.")
                if not self._interactive:
                    sys.stdout.flush()
                continue

            try:
                handler(args)
            except Exception as e:
                tb = e.__traceback__
                last = traceback.extract_tb(tb)[-1]

                print(f"! cmd error ({last.filename}:{last.lineno}): {e}")

            if not self._interactive:
                sys.stdout.flush()
