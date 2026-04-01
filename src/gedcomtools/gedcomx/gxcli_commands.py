#!/usr/bin/env python3
"""Command mixin classes for the GedcomX interactive shell."""
from __future__ import annotations

# ======================================================================
#  Project: gedcomtools
#  File:    gxcli_commands.py
#  Purpose: All _cmd_* Shell methods as mixin classes.
#           Import order: gxcli_core assembles Shell from these mixins.
#  Created: 2026-03-31 — split from gxcli.py
# ======================================================================
import inspect
import json
import logging
import io
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, get_args, get_origin

import orjson

from gedcomtools.gedcomx import GedcomConverter, GedcomX
from gedcomtools.gedcomx.serialization import ResolveStats, Serialization
from gedcomtools.gedcomx.schemas import SCHEMA, type_repr
from gedcomtools.gedcomx.cli import write_jsonl
from gedcomtools.gedcomx.arango import make_arango_graph_files
from gedcomtools.glog import get_logger, LoggerSpec

from gedcomtools.gedcomx.gxcli_output import (
    ANSI,
    _RED, _RESET,
    NO_DATA,
    _level_from_str,
    _set_all_handler_levels,
    _is_private,
    _coerce_token,
    _split_args_kwargs,
    _declaring_class,
    _format_signature,
    is_primitive,
    to_plain,
    short_preview,
    list_fields,
    as_indexable_list,
    _get_item_id,
    _seg_to_key,
    get_child,
    resolve_path,
    _typename,
    _print_table,
    _schema_fields_for_object,
    _expected_element_type_from_parent,
    _names_match,
    smart_getattr,
    _json_loads,
    _json_dumps,
    _save_settings,
    _DEFAULT_SETTINGS,
    _grep_node,
    _sans_ansi,
    _clip,
    _red,
    objects_to_schema_table,
)

# readline is optional
try:
    import readline as _readline
    _READLINE = True
except ImportError:
    _readline = None  # type: ignore[assignment]
    _READLINE = False


class _InfoMixin:
    """Mixin for informational and shell-management commands."""

    def _cmd_ver(self, _args: list[str]) -> None:
        print(self.version)  # type: ignore[attr-defined]

    def _cmd_help(self, args: list[str]) -> None:
        """
        help [COMMAND]
        Show general help or help for a specific command.
        """
        if args:
            name = args[0]
            handler = self.commands.get(name)  # type: ignore[attr-defined]
            if handler and handler.__doc__:
                print(handler.__doc__.strip())
                return
            print(f"No help for command {name!r}")
            return

        print(
            "Load / Save:\n"
            "  load PATH                load .ged / .json / .zip\n"
            "  extend PATH              load and merge into current root\n"
            "  write gx|zip|jsonl PATH  write current root to a file\n"
            "\nNavigation:\n"
            "  cd PATH                  change node (.., /, indices, id strings)\n"
            "  back                     return to previous location\n"
            "  pwd                      print current path\n"
            "  goto ID                  jump to any object by id\n"
            "  find PATTERN [--type T]  search persons/agents/places/events/sources\n"
            "  bookmark [NAME]          save current location; 'bookmark ls/rm NAME'\n"
            "  go NAME                  navigate to a saved bookmark\n"
            "\nInspection:\n"
            "  ls [PATH] [--full]       list fields/items (schema-aware)\n"
            "  show [PATH|toplevel]     pretty-print node or top-level items\n"
            "  dump [PATH]              same as show but always JSON\n"
            "  stats                    count all top-level collections\n"
            "  grep PATTERN [--all]     search field values by regex\n"
            "  validate                 run GedcomX validation\n"
            "  diff PATH                compare current root against another file\n"
            "  type [opts] [PATH|ATTR]  runtime & schema type info\n"
            "  schema ...               inspect schema/classes (see: schema help)\n"
            "  extras [opts]            list dynamic extras across classes\n"
            "\nEditing:\n"
            "  set NAME VALUE           set a field on the current node\n"
            "  set --n NAME [NAME2...]  create and append new instance(s)\n"
            "  del NAME [NAME2...]      delete attributes/keys/indices\n"
            "  call NAME [args] [k=v]   call a method on the current node\n"
            "\nShell:\n"
            "  cfg [NAME [VALUE]]       show/set persistent shell settings\n"
            "  history [N]              show last N commands\n"
            "  log ...                  logging controls\n"
            "  ext ...                  extension/plugin management\n"
            "  ver                      print version\n"
            "  quit | exit              leave\n"
            "\nType 'help COMMAND' for detailed help on any command.\n"
        )

    def _cmd_agenttbl(self, _args: list[str]) -> None:
        """
        agentstbl
        Show a schema table for agents (paged).
        """
        if self.gedcomx is None or not hasattr(self.gedcomx, "agents"):  # type: ignore[attr-defined]
            print("No GEDCOM-X data loaded.")
            return

        def page_table(text: str, rows_per_page: int = 25):
            lines = text.split("\n")
            total = len(lines)
            idx = 0
            while idx < total:
                end = idx + rows_per_page
                for line in lines[idx:end]:
                    print(line)
                idx = end
                if idx < total:
                    if self._interactive:  # type: ignore[attr-defined]
                        input("\n[Press Enter to continue…]\n")

        page_table(objects_to_schema_table(self.gedcomx.agents))  # type: ignore[attr-defined]

    def _cmd_cfg(self, args: list[str]) -> None:
        """
        cfg              Show all settings.
        cfg NAME         Show one setting.
        cfg NAME VALUE   Set and save a setting.
        cfg reset        Reset all settings to defaults.

        Settings:
          page_size    int   Rows per page in paginated output (default 20)
          color        str   ANSI color: auto | on | off
          history_size int   Max readline history entries (default 200)
        """
        if not args or args[0] == "ls":
            for k, v in self._settings.items():  # type: ignore[attr-defined]
                print(f"  {k} = {v!r}  (default: {_DEFAULT_SETTINGS[k]!r})")
            return
        if args[0] == "reset":
            self._settings = dict(_DEFAULT_SETTINGS)  # type: ignore[attr-defined]
            _save_settings(self._settings)  # type: ignore[attr-defined]
            print("Settings reset to defaults.")
            return
        key = args[0]
        if key not in _DEFAULT_SETTINGS:
            print(f"Unknown setting {key!r}. Known: {', '.join(_DEFAULT_SETTINGS)}")
            return
        if len(args) == 1:
            print(f"{key} = {self._settings[key]!r}")  # type: ignore[attr-defined]
            return
        raw_val = args[1]
        default_type = type(_DEFAULT_SETTINGS[key])
        try:
            if default_type is bool:
                val: Any = raw_val.lower() in ("true", "1", "yes", "on")
            elif default_type is int:
                val = int(raw_val)
            else:
                val = raw_val
        except ValueError:
            print(f"Invalid value {raw_val!r} for {key} (expected {default_type.__name__})")
            return
        self._settings[key] = val  # type: ignore[attr-defined]
        _save_settings(self._settings)  # type: ignore[attr-defined]
        print(f"{key} = {val!r}  (saved)")

    def _cmd_history(self, args: list[str]) -> None:
        """
        history [N]   Show last N commands (default 20). Requires readline.
        """
        if not _READLINE:
            print("Command history not available (readline not installed).")
            return
        try:
            n = int(args[0]) if args else 20
        except ValueError:
            n = 20
        total = _readline.get_current_history_length()
        start = max(1, total - n + 1)
        for i in range(start, total + 1):
            item = _readline.get_history_item(i)
            if item:
                print(f"  {i:4}  {item}")

    def _cmd_log(self, args: list[str]) -> None:
        """
        gxcli log command

        Usage:
        log
            - show configured loggers

        log list
            - alias of `log`

        log show <channel>
            - show details for one logger (level + handlers)

        log enable <channel> [LEVEL]
            - ensure a channel is configured (console by default); optionally set its logger level

        log level <channel> <LEVEL>
            - set logger level for channel

        log console <LEVEL>
            - set console handler level for ALL configured loggers (common + sublogs)

        log files on [DIR]
        log files off
            - toggles file logging *for future runs* (runtime enabling is tricky; see note below)

        Notes:
        - Changing levels takes effect immediately.
        - Turning files on/off at runtime is not fully supported in the base kit because it requires
        rebuilding handlers/run_dir safely. This command will set env vars for convenience and
        explain what to do. (If you want true runtime switching, I can extend LoggingManager.)
        """
        mgr = getattr(self, "mgr", None)
        if mgr is None:
            print("Logging is not configured (no manager).")
            return

        if len(args) == 0 or args[0] in ("list", "ls"):
            mgr.dump_loggers()
            return

        cmd = args[0].lower()

        if cmd == "show":
            if len(args) < 2:
                print("Usage: log show <channel>")
                return
            channel = args[1]
            logger = get_logger(channel)
            print(f"Logger: {logger.name}")
            print(f"  level: {logging.getLevelName(logger.level)}")
            print(f"  propagate: {logger.propagate}")
            if not logger.handlers:
                print("  handlers: (none)")
            else:
                for h in logger.handlers:
                    fmt = getattr(getattr(h, "formatter", None), "_fmt", None)
                    print(f"  handler: {type(h).__name__} level={logging.getLevelName(h.level)} fmt={fmt}")
            return

        if cmd == "enable":
            if len(args) < 2:
                print("Usage: log enable <channel> [LEVEL]")
                return
            channel = args[1]
            level = None
            if len(args) >= 3:
                level = _level_from_str(args[2])

            spec = LoggerSpec(name=channel, filename="", level=level or logging.INFO, also_to_console=True)
            logger = mgr.get_sublogger(spec)

            if level is not None:
                logger.setLevel(level)

            print(f"Enabled logger '{channel}' at level {logging.getLevelName(logger.level)}")
            return

        if cmd == "level":
            if len(args) < 3:
                print("Usage: log level <channel> <LEVEL>")
                return
            channel = args[1]
            level = _level_from_str(args[2])

            if channel == "common":
                logger = mgr.get_common()
            else:
                if not mgr.log_exists(channel):
                    mgr.get_sublogger(LoggerSpec(name=channel, filename="", level=level, also_to_console=True))
                logger = get_logger(channel)

            logger.setLevel(level)
            print(f"Set logger '{channel}' to {logging.getLevelName(level)}")
            return

        if cmd == "console":
            if len(args) < 2:
                print("Usage: log console <LEVEL>")
                return
            level = _level_from_str(args[1])

            _set_all_handler_levels(mgr.get_common(), level)
            for _, lg in mgr._sub_loggers.items():
                _set_all_handler_levels(lg, level)

            print(f"Set console handler level to {logging.getLevelName(level)} for configured loggers.")
            return

        if cmd == "files":
            if len(args) < 2:
                print("Usage: log files on [DIR] | log files off")
                return
            onoff = args[1].lower()
            if onoff in ("on", "enable", "1", "true", "yes"):
                os.environ["LOG_FILES"] = "1"
                if len(args) >= 3:
                    raw_dir = args[2]
                    if len(raw_dir) > 512:
                        print("! Invalid LOG_DIR: path too long (max 512 chars).")
                        return
                    log_dir = Path(raw_dir).resolve()
                    if not log_dir.parent.exists():
                        print(f"! Invalid LOG_DIR: parent directory does not exist: {log_dir.parent}")
                        return
                    os.environ["LOG_DIR"] = str(log_dir)
                    print(f"LOG_FILES=1, LOG_DIR={log_dir}")
                else:
                    print("LOG_FILES=1")
                print("Note: file logging will take effect next run (or after re-calling setup_logging).")
                return
            if onoff in ("off", "disable", "0", "false", "no"):
                os.environ["LOG_FILES"] = "0"
                print("LOG_FILES=0")
                print("Note: file logging will be off next run (or after re-calling setup_logging).")
                return
            print("Usage: log files on [DIR] | log files off")
            return

        print("Unknown log command. Try: log, log show <ch>, log enable <ch> [LEVEL], log level <ch> <LEVEL>, log console <LEVEL>, log files on|off")

    def _cmd_ext(self, args: list[str]) -> None:
        """
        ext ls [all|NAME]
            List registered extensions: name, location, status.

        ext show [all|NAME]
            Show full details for extension(s).

        ext scan [PACKAGE]
            Discover and register bundled extensions.
            PACKAGE defaults to gedcomtools.gedcomx.extensions.
            Run this before 'ext load' to populate the registry.

        ext authorize SOURCE [NAME] [sha256=HASH]
            Add SOURCE to the allow-list (must be done before ext load).
            NAME is optional human label; sha256 is required for URLs.

        ext load [NAME]
            Load all allowed extensions, or just NAME (substring match).

        ext trust [DISABLED|BUILTIN|LOCAL|ALL]
            Show or set the plugin trust level.
        """
        import importlib.util
        import pkgutil
        from gedcomtools.gedcomx.extensible import (
            plugin_registry, TrustLevel, PluginStatus, RegistryLockedError
        )

        sub = args[0].lower() if args else "ls"
        rest = args[1:]

        _STATUS_COLOR = {
            PluginStatus.LOADED:  ANSI.get("green", ""),
            PluginStatus.FAILED:  ANSI.get("red", ""),
            PluginStatus.BLOCKED: ANSI.get("red", ""),
            PluginStatus.ALLOWED: ANSI.get("yellow", ""),
            PluginStatus.PENDING: ANSI.get("dim", ""),
        }
        _RST = ANSI.get("reset", "")

        def _colored_status(s: PluginStatus) -> str:
            c = _STATUS_COLOR.get(s, "")
            return f"{c}{s.value}{_RST}" if c else s.value

        def _resolve_module_path(modname: str) -> str:
            mod = sys.modules.get(modname)
            if mod:
                f = getattr(mod, "__file__", None)
                if f:
                    return f
                locs = getattr(mod, "__path__", None)
                if locs:
                    return list(locs)[0]
            try:
                spec = importlib.util.find_spec(modname)
                if spec:
                    if spec.origin and spec.origin != "namespace":
                        return spec.origin
                    locs = list(spec.submodule_search_locations or [])
                    if locs:
                        return locs[0]
            except (ModuleNotFoundError, ValueError):
                pass
            return modname

        def _source_location(entry) -> str:
            src = entry.source
            if entry.status == PluginStatus.LOADED:
                mod = sys.modules.get(entry.name) or sys.modules.get(src)
                if mod and getattr(mod, "__file__", None):
                    return mod.__file__
            if src and not src.startswith(("http://", "https://", "/", ".", os.sep)):
                return _resolve_module_path(src)
            return src

        def _match(entry, selector: str) -> bool:
            if not selector or selector == "all":
                return True
            s = selector.lower()
            return s in entry.name.lower() or s in entry.source.lower()

        def _entries_for(selector: str):
            entries = plugin_registry.list()
            sel = selector.lower() if selector else "all"
            return [e for e in entries if _match(e, sel)]

        if sub == "ls":
            selector = rest[0] if rest else "all"
            entries = _entries_for(selector)
            if not entries:
                print("No extensions registered." if selector == "all"
                      else f"No extension matching {selector!r}.")
                if selector == "all":
                    print("Tip: run 'ext scan' to discover bundled extensions.")
                return
            col_n = max(len(e.name) for e in entries)
            col_s = max(len(_source_location(e)) for e in entries)
            col_n = max(col_n, 4)
            col_s = max(col_s, 8)
            hdr = f"{'NAME':<{col_n}}  {'LOCATION':<{col_s}}  STATUS"
            print(hdr)
            print("-" * len(hdr))
            for e in entries:
                loc = _source_location(e)
                print(f"{e.name:<{col_n}}  {loc:<{col_s}}  {_colored_status(e.status)}")
            return

        if sub == "show":
            selector = rest[0] if rest else "all"
            entries = _entries_for(selector)
            if not entries:
                print("No extensions registered." if selector == "all"
                      else f"No extension matching {selector!r}.")
                return
            for e in entries:
                loc = _source_location(e)
                print(f"Name    : {e.name}")
                print(f"Source  : {e.source}")
                print(f"Location: {loc}")
                print(f"Status  : {_colored_status(e.status)}")
                if e.expected_sha256:
                    print(f"sha256 (expected): {e.expected_sha256}")
                if e.actual_sha256:
                    print(f"sha256 (actual)  : {e.actual_sha256}")
                if e.error:
                    print(f"Error   : {e.error}")
                print()
            return

        if sub == "scan":
            root_pkg = rest[0] if rest else "gedcomtools.gedcomx.extensions"
            try:
                pkg = importlib.import_module(root_pkg)
            except ModuleNotFoundError:
                print(f"Package not found: {root_pkg}")
                return
            pkg_path = getattr(pkg, "__path__", None)
            if not pkg_path:
                print(f"{root_pkg} is not a package.")
                return

            found: list[tuple[str, str]] = []
            for mi in pkgutil.iter_modules(pkg_path, root_pkg + "."):
                loc = _resolve_module_path(mi.name)
                found.append((mi.name, loc))

            if not found:
                print(f"No extensions found in {root_pkg}.")
                return

            print(f"Found {len(found)} extension(s) in {root_pkg}:")
            registered = 0
            skipped = 0
            for modname, loc in found:
                short = modname.split(".")[-1]
                try:
                    plugin_registry.allow(modname, name=short)
                    print(f"  + {short:<20}  {loc}")
                    registered += 1
                except RegistryLockedError:
                    print(f"  ! {short:<20}  registry locked — run before 'ext load'")
                    skipped += 1
                except Exception as e:
                    print(f"  ! {short:<20}  {e}")
                    skipped += 1

            if registered:
                print(f"\nRegistered {registered} extension(s). Run 'ext load' to import them.")
            if skipped:
                print(f"Skipped {skipped} (already locked). Restart shell to re-scan.")
            return

        if sub in ("authorize", "auth", "allow"):
            if not rest:
                print("Usage: ext authorize SOURCE [NAME] [sha256=HASH]")
                return
            source = rest[0]
            name: str | None = None
            sha256: str | None = None
            for tok in rest[1:]:
                if tok.startswith("sha256="):
                    sha256 = tok[7:]
                elif name is None:
                    name = tok
            try:
                plugin_registry.allow(source, name=name, sha256=sha256)
                label = name or source
                print(f"Authorized: {label!r}  ({source})")
            except RegistryLockedError as e:
                print(f"Error: {e}")
            except ValueError as e:
                print(f"Error: {e}")
            return

        if sub == "load":
            name_filter = rest[0] if rest else None
            try:
                if name_filter:
                    all_entries = plugin_registry.list()
                    targets = [e for e in all_entries
                               if name_filter.lower() in e.name.lower()]
                    if not targets:
                        print(f"No extension matching {name_filter!r}. "
                              f"Run 'ext ls' to see registered extensions.")
                        return
                    imported: list[str] = []
                    errors: dict[str, Exception] = {}
                    for e in targets:
                        result = plugin_registry.load_one(e.name)
                        imported.extend(result.get("imported", []))
                        errors.update(result.get("errors", {}))
                else:
                    result = plugin_registry.load()
                    imported = result.get("imported", [])
                    errors = result.get("errors", {})
            except RegistryLockedError as e:
                print(f"Error: {e}")
                return
            if imported:
                print(f"Loaded {len(imported)} extension(s):")
                for mod in imported:
                    print(f"  {mod}")
            else:
                print("No extensions loaded.")
            if errors:
                print(f"{len(errors)} error(s):")
                for src, err in errors.items():
                    print(f"  {src}: {err}")
            return

        if sub == "trust":
            if not rest:
                print(f"Trust level: {plugin_registry.trust_level.name}")
                return
            level_str = rest[0].upper()
            try:
                level = TrustLevel[level_str]
            except KeyError:
                print(f"Unknown trust level {rest[0]!r}. Use: DISABLED, BUILTIN, LOCAL, ALL")
                return
            try:
                plugin_registry.set_trust_level(level)
                print(f"Trust level set to {level.name}.")
            except RegistryLockedError as e:
                print(f"Error: {e}")
            return

        print(f"Unknown extension subcommand {sub!r}. Use: ls, show, scan, authorize, load, trust")


class _AhnenMixin:
    """Mixin for Ahnentafel (ancestor table) commands."""

    # Key aliases for ahnen set parsing
    _AHNEN_KEY_MAP: dict[str, str] = {
        "b": "birth_date",   "born": "birth_date",   "birth": "birth_date",
        "bp": "birth_place", "bplace": "birth_place", "birth_place": "birth_place",
        "d": "death_date",   "died": "death_date",   "death": "death_date",
        "dp": "death_place", "dplace": "death_place", "death_place": "death_place",
        "m": "marr_date",    "married": "marr_date",  "marriage": "marr_date",
        "mp": "marr_place",  "mplace": "marr_place",  "marriage_place": "marr_place",
    }

    @staticmethod
    def _ahnen_generation(n: int) -> int:
        """Return 0-based generation of Ahnentafel number n (1→0, 2-3→1, 4-7→2, …)."""
        g = 0
        while n > 1:
            n >>= 1
            g += 1
        return g

    @staticmethod
    def _ahnen_relation(n: int) -> str:
        """Human-readable relationship label for Ahnentafel number n."""
        if n == 1:
            return "proband"
        # Use Shell's static method by calling via type (avoids forward ref)
        gen = _AhnenMixin._ahnen_generation(n)
        line_parts: list[str] = []
        k = n
        while k > 3:
            line_parts.append("paternal" if k % 2 == 0 else "maternal")
            k >>= 1
        line_parts.reverse()
        side = " ".join(line_parts) + " " if line_parts else ""
        gender = "father" if n % 2 == 0 else "mother"
        if gen == 1:
            return gender
        prefix = "great-" * (gen - 2) if gen > 2 else ""
        parent_word = "grandfather" if n % 2 == 0 else "grandmother"
        return f"{side}{prefix}{parent_word}"

    def _ahnen_fmt(self, entry: dict, short: bool = False) -> str:
        """Format a single Ahnentafel entry as a short string."""
        parts = [entry["name"]]
        if entry.get("birth_date"):
            parts.append(f"b.{entry['birth_date']}")
        if not short and entry.get("birth_place"):
            parts.append(f"({entry['birth_place']})")
        if entry.get("death_date"):
            parts.append(f"d.{entry['death_date']}")
        if not short and entry.get("death_place"):
            parts.append(f"({entry['death_place']})")
        return "  ".join(parts)

    def _ahnen_print_tree(
        self,
        n: int,
        max_depth: int,
        depth: int = 0,
        prefix: str = "",
        is_last: bool = True,
    ) -> None:
        has_entry = n in self._ahnen  # type: ignore[attr-defined]
        father_n, mother_n = 2 * n, 2 * n + 1
        has_children = depth < max_depth and (
            father_n in self._ahnen or mother_n in self._ahnen  # type: ignore[attr-defined]
            or (depth + 1 < max_depth and any(
                k in self._ahnen for k in (2*father_n, 2*father_n+1, 2*mother_n, 2*mother_n+1)  # type: ignore[attr-defined]
            ))
        )

        if not has_entry and not has_children:
            return

        connector = "└── " if is_last else "├── "
        line_prefix = prefix + connector if depth > 0 else ""
        child_prefix = prefix + ("    " if is_last else "│   ") if depth > 0 else ""

        relation = self._ahnen_relation(n)

        if has_entry:
            summary = self._ahnen_fmt(self._ahnen[n], short=True)  # type: ignore[attr-defined]
            print(f"{line_prefix}#{n}  {summary}  [{relation}]")
        else:
            print(f"{line_prefix}#{n}  —  [{relation}]")

        if depth < max_depth:
            father_exists = father_n in self._ahnen or (depth + 1 < max_depth and any(  # type: ignore[attr-defined]
                k in self._ahnen for k in range(2*father_n, 4*father_n)))  # type: ignore[attr-defined]
            mother_exists = mother_n in self._ahnen or (depth + 1 < max_depth and any(  # type: ignore[attr-defined]
                k in self._ahnen for k in range(2*mother_n, 4*mother_n)))  # type: ignore[attr-defined]

            if father_exists or mother_exists:
                self._ahnen_print_tree(father_n, max_depth, depth+1, child_prefix, not mother_exists)
                if mother_exists:
                    self._ahnen_print_tree(mother_n, max_depth, depth+1, child_prefix, True)

    def _cmd_ahnen(self, args: list[str]) -> None:
        """
        ahnen set N NAME [b=DATE] [bp=PLACE] [d=DATE] [dp=PLACE] [m=DATE] [mp=PLACE]
            Add or update a person. N=1 is the proband.
            Parents of N are 2N (father) and 2N+1 (mother).
            Key aliases: b/born  bp/bplace  d/died  dp/dplace  m/married  mp/mplace
            Example:  ahnen set 1 "John Smith" b=1850 bp="New York" d=1920

        ahnen get N
            Show full details for person N.

        ahnen ls
            List all entries as a table.

        ahnen tree [DEPTH]
            Show pedigree chart from person 1 (default depth 3).

        ahnen clear [N]
            Remove person N, or clear all if N omitted.

        ahnen build
            Convert all entries to GedcomX and load as root.

        ahnen import FILE
            Import from a text file (one person per line: N NAME key:value …).

        ahnen export FILE
            Export entries to a text file.
        """
        sub = args[0].lower() if args else "ls"
        rest = args[1:]

        if sub == "set":
            if len(rest) < 2:
                print("usage: ahnen set N NAME [b=DATE] [bp=PLACE] [d=DATE] [dp=PLACE] [m=DATE] [mp=PLACE]")
                return
            try:
                n = int(rest[0])
            except ValueError:
                print(f"N must be an integer, got {rest[0]!r}")
                return
            if n < 1:
                print("N must be ≥ 1")
                return

            name = rest[1]
            entry: dict = dict(self._ahnen.get(n, {"name": ""}))  # type: ignore[attr-defined]
            entry["name"] = name

            for tok in rest[2:]:
                if "=" not in tok:
                    print(f"Ignoring unrecognised token {tok!r} (expected key=value)")
                    continue
                k, v = tok.split("=", 1)
                k = k.strip().lower().rstrip("_")
                field = self._AHNEN_KEY_MAP.get(k)
                if field is None:
                    print(f"Unknown key {k!r}. Use: b, bp, d, dp, m, mp")
                    continue
                entry[field] = v.strip()

            self._ahnen[n] = entry  # type: ignore[attr-defined]

            relation = self._ahnen_relation(n)
            child_n = n >> 1
            child_info = f"  (parent of #{child_n})" if n > 1 else ""
            print(f"Set #{n} [{relation}]{child_info}: {self._ahnen_fmt(entry)}")
            return

        if sub == "get":
            if not rest:
                print("usage: ahnen get N")
                return
            try:
                n = int(rest[0])
            except ValueError:
                print(f"N must be an integer")
                return
            if n not in self._ahnen:  # type: ignore[attr-defined]
                print(f"No entry for #{n}.")
                return
            e = self._ahnen[n]  # type: ignore[attr-defined]
            rel = self._ahnen_relation(n)
            print(f"#{n}  {rel}")
            print(f"  Name        : {e['name']}")
            if e.get("birth_date"):  print(f"  Born        : {e['birth_date']}")
            if e.get("birth_place"): print(f"  Birth place : {e['birth_place']}")
            if e.get("death_date"):  print(f"  Died        : {e['death_date']}")
            if e.get("death_place"): print(f"  Death place : {e['death_place']}")
            if e.get("marr_date"):   print(f"  Married     : {e['marr_date']}")
            if e.get("marr_place"):  print(f"  Marr. place : {e['marr_place']}")
            if n > 1:
                child_n = n >> 1
                print(f"  Parent of   : #{child_n} ({self._ahnen.get(child_n, {}).get('name', '—')})")  # type: ignore[attr-defined]
            father_n, mother_n = 2*n, 2*n+1
            if father_n in self._ahnen or mother_n in self._ahnen:  # type: ignore[attr-defined]
                print(f"  Father      : #{father_n} ({self._ahnen.get(father_n, {}).get('name', '—')})")  # type: ignore[attr-defined]
                print(f"  Mother      : #{mother_n} ({self._ahnen.get(mother_n, {}).get('name', '—')})")  # type: ignore[attr-defined]
            return

        if sub == "ls":
            if not self._ahnen:  # type: ignore[attr-defined]
                print("No Ahnentafel entries.  Use: ahnen set N NAME [b=DATE] ...")
                return
            nums = sorted(self._ahnen)  # type: ignore[attr-defined]
            num_w  = max(len(str(n)) for n in nums)
            name_w = max(len(self._ahnen[n]["name"]) for n in nums)  # type: ignore[attr-defined]
            rel_w  = max(len(self._ahnen_relation(n)) for n in nums)
            print(f"{'#':<{num_w}}  {'Name':<{name_w}}  {'Relation':<{rel_w}}  Born        Died        Married")
            print("-" * (num_w + name_w + rel_w + 40))
            for n in nums:
                e = self._ahnen[n]  # type: ignore[attr-defined]
                rel = self._ahnen_relation(n)
                bd = e.get("birth_date", "")
                dd = e.get("death_date", "")
                md = e.get("marr_date", "")
                print(f"{n:<{num_w}}  {e['name']:<{name_w}}  {rel:<{rel_w}}  {bd:<12}{dd:<12}{md}")
            return

        if sub == "tree":
            if not self._ahnen:  # type: ignore[attr-defined]
                print("No Ahnentafel entries.")
                return
            try:
                max_depth = int(rest[0]) if rest else 3
            except ValueError:
                max_depth = 3
            total = len(self._ahnen)  # type: ignore[attr-defined]
            max_n = max(self._ahnen)  # type: ignore[attr-defined]
            gens = self._ahnen_generation(max_n)
            print(f"Pedigree  ({total} entr{'y' if total==1 else 'ies'}, {gens+1} generation(s))")
            print()
            self._ahnen_print_tree(1, max_depth)
            return

        if sub == "clear":
            if not rest:
                count = len(self._ahnen)  # type: ignore[attr-defined]
                self._ahnen.clear()  # type: ignore[attr-defined]
                print(f"Cleared {count} entr{'y' if count==1 else 'ies'}.")
                return
            try:
                n = int(rest[0])
            except ValueError:
                print("usage: ahnen clear [N]")
                return
            if n in self._ahnen:  # type: ignore[attr-defined]
                del self._ahnen[n]  # type: ignore[attr-defined]
                print(f"Removed #{n}.")
            else:
                print(f"No entry for #{n}.")
            return

        if sub == "build":
            if not self._ahnen:  # type: ignore[attr-defined]
                print("No Ahnentafel entries to build from.")
                return
            from gedcomtools.gedcomx import (
                GedcomX, Person, Relationship, RelationshipType,
                Fact, FactType, Name, NameForm, Gender, GenderType,
                Date, PlaceReference,
            )
            from gedcomtools.gedcomx.name import QuickName

            gx = GedcomX()
            persons: dict[int, Any] = {}

            for n, e in sorted(self._ahnen.items()):  # type: ignore[attr-defined]
                p = Person()
                p.id = f"P{n}"
                p.names.append(QuickName(e["name"]))

                if n == 1:
                    p.gender = Gender(type=GenderType.Unknown)
                elif n % 2 == 0:
                    p.gender = Gender(type=GenderType.Male)
                else:
                    p.gender = Gender(type=GenderType.Female)

                if e.get("birth_date") or e.get("birth_place"):
                    f = Fact(type=FactType.Birth)
                    if e.get("birth_date"):
                        f.date = Date(original=e["birth_date"])
                    if e.get("birth_place"):
                        f.place = PlaceReference(original=e["birth_place"])
                    p.facts.append(f)

                if e.get("death_date") or e.get("death_place"):
                    f = Fact(type=FactType.Death)
                    if e.get("death_date"):
                        f.date = Date(original=e["death_date"])
                    if e.get("death_place"):
                        f.place = PlaceReference(original=e["death_place"])
                    p.facts.append(f)

                gx.persons.append(p)
                persons[n] = p

            processed_couples: set[int] = set()
            for n in sorted(persons):
                father_n, mother_n = 2 * n, 2 * n + 1

                couple_key = min(father_n, mother_n)
                if couple_key not in processed_couples:
                    if father_n in persons and mother_n in persons:
                        fa_e = self._ahnen.get(father_n, {})  # type: ignore[attr-defined]
                        mo_e = self._ahnen.get(mother_n, {})  # type: ignore[attr-defined]
                        marr_date = fa_e.get("marr_date") or mo_e.get("marr_date")
                        marr_place = fa_e.get("marr_place") or mo_e.get("marr_place")

                        couple = Relationship(
                            type=RelationshipType.Couple,
                            person1=persons[father_n],
                            person2=persons[mother_n],
                        )
                        if marr_date or marr_place:
                            mf = Fact(type=FactType.Marriage)
                            if marr_date:
                                mf.date = Date(original=marr_date)
                            if marr_place:
                                mf.place = PlaceReference(original=marr_place)
                            couple.facts.append(mf)

                        gx.relationships.append(couple)
                        processed_couples.add(couple_key)

                if father_n in persons:
                    gx.relationships.append(Relationship(
                        type=RelationshipType.ParentChild,
                        person1=persons[father_n],
                        person2=persons[n],
                    ))
                if mother_n in persons:
                    gx.relationships.append(Relationship(
                        type=RelationshipType.ParentChild,
                        person1=persons[mother_n],
                        person2=persons[n],
                    ))

            self._set_root(gx)  # type: ignore[attr-defined]
            self.gedcomx = gx  # type: ignore[attr-defined]
            p_count = len(persons)
            r_count = len(gx.relationships)
            print(f"Built GedcomX: {p_count} person(s), {r_count} relationship(s). Loaded as root.")
            return

        if sub == "import":
            if not rest:
                print("usage: ahnen import FILE")
                return
            path = rest[0].strip('"').strip("'")
            try:
                lines = Path(path).read_text(encoding="utf-8").splitlines()
            except OSError as e:
                print(f"Error reading {path}: {e}")
                return
            imported = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                tokens = line.split()
                if len(tokens) < 2:
                    continue
                try:
                    n = int(tokens[0].rstrip("."))
                except ValueError:
                    continue
                name_parts = []
                kv_start = 2
                for i, tok in enumerate(tokens[1:], 1):
                    if ":" in tok and tok.split(":")[0].lower() in self._AHNEN_KEY_MAP:
                        kv_start = i
                        break
                    name_parts.append(tok)
                name = " ".join(name_parts)
                entry2: dict = dict(self._ahnen.get(n, {"name": ""}))  # type: ignore[attr-defined]
                entry2["name"] = name
                for tok in tokens[kv_start:]:
                    if ":" not in tok:
                        continue
                    k, v = tok.split(":", 1)
                    field = self._AHNEN_KEY_MAP.get(k.lower())
                    if field:
                        entry2[field] = v
                self._ahnen[n] = entry2  # type: ignore[attr-defined]
                imported += 1
            print(f"Imported {imported} entr{'y' if imported==1 else 'ies'} from {path}.")
            return

        if sub == "export":
            if not rest:
                print("usage: ahnen export FILE")
                return
            path = rest[0].strip('"').strip("'")
            lines = ["# Ahnentafel export — gedcomtools gxcli", "# N  Name  key:value ..."]
            for n in sorted(self._ahnen):  # type: ignore[attr-defined]
                e = self._ahnen[n]  # type: ignore[attr-defined]
                parts = [str(n), e["name"]]
                for key, field in [
                    ("b", "birth_date"), ("bp", "birth_place"),
                    ("d", "death_date"),  ("dp", "death_place"),
                    ("m", "marr_date"),   ("mp", "marr_place"),
                ]:
                    if e.get(field):
                        parts.append(f"{key}:{e[field]}")
                lines.append("  ".join(parts))
            try:
                Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
                print(f"Exported {len(self._ahnen)} entr{'y' if len(self._ahnen)==1 else 'ies'} to {path}.")  # type: ignore[attr-defined]
            except OSError as e:
                print(f"Error writing {path}: {e}")
            return

        print(f"Unknown subcommand {sub!r}. Use: set, get, ls, tree, clear, build, import, export")


class _NavMixin:
    """Mixin for navigation commands."""

    def _cmd_back(self, args: list[str]) -> None:
        """
        back
        Return to the previous location in navigation history.
        """
        _ = args
        if not self._nav_history:  # type: ignore[attr-defined]
            print("No navigation history.")
            return
        cur, path = self._nav_history.pop()  # type: ignore[attr-defined]
        self.cur = cur  # type: ignore[attr-defined]
        self.path = path  # type: ignore[attr-defined]
        print("/" + "/".join(self.path))  # type: ignore[attr-defined]

    def _cmd_goto(self, args: list[str]) -> None:
        """
        goto ID
        Navigate directly to any top-level object by its id.
        """
        if not args:
            print("usage: goto ID")
            return
        if self.gedcomx is None:  # type: ignore[attr-defined]
            print("No GedcomX data loaded.")
            return
        target_id = args[0]
        if target_id not in self.gedcomx.id_index:  # type: ignore[attr-defined]
            print(f"No object with id {target_id!r} found.")
            return
        _collections = [
            ("persons",             self.gedcomx.persons),  # type: ignore[attr-defined]
            ("relationships",       self.gedcomx.relationships),  # type: ignore[attr-defined]
            ("agents",              self.gedcomx.agents),  # type: ignore[attr-defined]
            ("sourceDescriptions",  self.gedcomx.sourceDescriptions),  # type: ignore[attr-defined]
            ("places",              self.gedcomx.places),  # type: ignore[attr-defined]
            ("events",              self.gedcomx.events),  # type: ignore[attr-defined]
            ("documents",           self.gedcomx.documents),  # type: ignore[attr-defined]
            ("groups",              self.gedcomx.groups),  # type: ignore[attr-defined]
        ]
        self._nav_history.append((self.cur, list(self.path)))  # type: ignore[attr-defined]
        for coll_name, coll in _collections:
            for i, item in enumerate(coll):
                if getattr(item, "id", None) == target_id:
                    self.path = [coll_name, str(i)]  # type: ignore[attr-defined]
                    self.cur = item  # type: ignore[attr-defined]
                    print(f"→ /{'/'.join(self.path)}")  # type: ignore[attr-defined]
                    return
        self.cur = self.gedcomx.id_index[target_id]  # type: ignore[attr-defined]
        self.path = [f"@{target_id}"]  # type: ignore[attr-defined]
        print(f"→ @{target_id}")

    def _cmd_find(self, args: list[str]) -> None:
        """
        find PATTERN [--type persons|agents|places|sources|events]
        Search by name/title. Default: persons. PATTERN is case-insensitive.
        Select a result with: goto ID
        """
        if not args:
            print("usage: find PATTERN [--type persons|agents|places|sources|events]")
            return
        if self.gedcomx is None:  # type: ignore[attr-defined]
            print("No GedcomX data loaded.")
            return

        pattern = None
        type_filter = "persons"
        i = 0
        while i < len(args):
            if args[i] == "--type" and i + 1 < len(args):
                type_filter = args[i + 1].lower()
                i += 2
            else:
                pattern = args[i]
                i += 1
        if pattern is None:
            print("usage: find PATTERN [--type ...]")
            return

        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            print(f"Invalid regex: {e}")
            return

        def _person_label(p) -> str:
            try:
                return p.names[0].nameForms[0].fullText or "?"
            except (IndexError, AttributeError):
                return getattr(p, "id", "?") or "?"

        def _agent_label(a) -> str:
            try:
                return a.names[0].value or "?"
            except (IndexError, AttributeError):
                return getattr(a, "id", "?") or "?"

        def _place_label(pl) -> str:
            try:
                return pl.names[0].value or "?"
            except (IndexError, AttributeError):
                return getattr(pl, "id", "?") or "?"

        def _event_label(ev) -> str:
            try:
                return ev.type or getattr(ev, "id", "?") or "?"
            except AttributeError:
                return getattr(ev, "id", "?") or "?"

        def _source_label(sd) -> str:
            return getattr(sd, "title", None) or getattr(sd, "id", "?") or "?"

        search_map = {
            "persons": (self.gedcomx.persons, _person_label),  # type: ignore[attr-defined]
            "agents": (self.gedcomx.agents, _agent_label),  # type: ignore[attr-defined]
            "places": (self.gedcomx.places, _place_label),  # type: ignore[attr-defined]
            "events": (self.gedcomx.events, _event_label),  # type: ignore[attr-defined]
            "sources": (self.gedcomx.sourceDescriptions, _source_label),  # type: ignore[attr-defined]
        }
        if type_filter not in search_map:
            print(f"Unknown type {type_filter!r}. Use: {', '.join(search_map)}")
            return

        coll, label_fn = search_map[type_filter]
        results = []
        for obj in coll:
            label = label_fn(obj)
            obj_id = getattr(obj, "id", "?")
            if rx.search(label) or rx.search(str(obj_id)):
                results.append((obj_id, label))

        if not results:
            print(f"No {type_filter} matching {pattern!r}.")
            return

        print(f"{len(results)} match(es) in {type_filter}:")
        id_w = max(len(str(r[0])) for r in results)
        for oid, label in results:
            print(f"  {str(oid):<{id_w}}  {label}")
        if len(results) == 1:
            print(f"Tip: use 'goto {results[0][0]}' to navigate there.")

    def _cmd_bookmark(self, args: list[str]) -> None:
        """
        bookmark [NAME]     Save current location with a name.
        bookmark ls         List all bookmarks.
        bookmark rm NAME    Remove a bookmark.
        """
        if not args or args[0] == "ls":
            if not self._bookmarks:  # type: ignore[attr-defined]
                print("No bookmarks.")
                return
            name_w = max(len(n) for n in self._bookmarks)  # type: ignore[attr-defined]
            for name, (_, path) in sorted(self._bookmarks.items()):  # type: ignore[attr-defined]
                print(f"  {name:<{name_w}}  /{'/'.join(path)}")
            return
        if args[0] == "rm":
            if len(args) < 2:
                print("usage: bookmark rm NAME")
                return
            name = args[1]
            if name in self._bookmarks:  # type: ignore[attr-defined]
                del self._bookmarks[name]  # type: ignore[attr-defined]
                print(f"Removed {name!r}.")
            else:
                print(f"No bookmark named {name!r}.")
            return
        name = args[0]
        self._bookmarks[name] = (self.cur, list(self.path))  # type: ignore[attr-defined]
        print(f"Bookmark {name!r} → /{'/'.join(self.path)}")  # type: ignore[attr-defined]

    def _cmd_go(self, args: list[str]) -> None:
        """
        go NAME   Navigate to a saved bookmark.
        """
        if not args:
            print("usage: go NAME")
            if self._bookmarks:  # type: ignore[attr-defined]
                print("Bookmarks:", ", ".join(sorted(self._bookmarks)))  # type: ignore[attr-defined]
            return
        name = args[0]
        if name not in self._bookmarks:  # type: ignore[attr-defined]
            print(f"No bookmark named {name!r}.")
            if self._bookmarks:  # type: ignore[attr-defined]
                print("Available:", ", ".join(sorted(self._bookmarks)))  # type: ignore[attr-defined]
            return
        self._nav_history.append((self.cur, list(self.path)))  # type: ignore[attr-defined]
        cur, path = self._bookmarks[name]  # type: ignore[attr-defined]
        self.cur = cur  # type: ignore[attr-defined]
        self.path = list(path)  # type: ignore[attr-defined]
        print(f"→ /{'/'.join(self.path)}")  # type: ignore[attr-defined]


class _LoadMixin:
    """Mixin for load/extend/url commands."""

    @staticmethod
    def _is_url(s: str) -> bool:
        return s.startswith("http://") or s.startswith("https://")

    def _dispatch_load(self, src: str) -> Any:
        """Resolve *src* (path or URL) to a GedcomX object and return it."""
        low = src.lower().split("?")[0]
        is_url = self._is_url(src)

        if low.endswith(".ged"):
            print("Loading GEDCOM (size may affect time)…")
            return self._load_from_ged(src) if not is_url else self._load_ged_url(src)

        if low.endswith(".zip"):
            print("Loading GedcomX ZIP archive…")
            return self._load_from_zip(src) if not is_url else self._load_zip_url(src)

        if low.endswith(".json"):
            print("Loading Gedcom-X from JSON…")
            return self._load_from_json(src) if not is_url else self._load_json_url(src)

        print(f"Unsupported file type. Use .ged, .zip, or .json: {src}")
        return None

    def _cmd_extend(self, args: list[str]) -> None:
        """
        extend PATH|URL
        Load a .ged, .json, or .zip (from disk or URL) and extend current root.
        """
        if len(args) != 1:
            print("usage: extend PATH|URL")
            return

        if self.root is None or not hasattr(self.root, "extend"):  # type: ignore[attr-defined]
            print("Current root is None or does not support .extend()")
            return

        src = args[0].strip().strip('"')
        gx = self._dispatch_load(src)
        if gx is not None:
            self.root.extend(gx)  # type: ignore[attr-defined]
            print("Extended.")

    def _cmd_load(self, args: list[str]) -> None:
        """
        load PATH|URL
        Load a .ged (GEDCOM 5/7), .json (GedcomX), or .zip from disk or an HTTP/HTTPS URL.
        """
        if len(args) != 1:
            print("usage: load PATH|URL")
            return

        src = args[0].strip().strip('"')
        gx = self._dispatch_load(src)
        if gx is not None:
            self._set_root(gx)  # type: ignore[attr-defined]
            print("Loaded.")

    def _print_validation_results(self, issues: list) -> None:
        """Print validation results from a list of ValidationIssue objects."""
        errors = [i for i in issues if getattr(i, "severity", "error") == "error"]
        warnings = [i for i in issues if getattr(i, "severity", "error") == "warning"]
        if not issues:
            print("  Validation: OK (no issues)")
            return
        print(f"  Validation: {len(errors)} error(s), {len(warnings)} warning(s)")
        for issue in issues:
            sev = getattr(issue, "severity", "error")
            code = getattr(issue, "code", "")
            line = getattr(issue, "line_num", None)
            tag = getattr(issue, "tag", None)
            msg = getattr(issue, "message", str(issue))
            loc = f" line {line}" if line else ""
            tag_s = f" [{tag}]" if tag else ""
            sev_label = f"{_RED}ERROR{_RESET}" if sev == "error" else "WARN "
            print(f"  {sev_label}{loc}{tag_s}: {code}: {msg}")

    def _load_from_ged(self, path: str) -> Any:
        from gedcomtools.cli import _load_g7, _sniff_source_type
        from gedcomtools.gedcom5.parser import Gedcom5x

        src_type = _sniff_source_type(Path(path))

        if src_type == "g5":
            from gedcomtools.gedcom5.validator5 import Gedcom5Validator
            print("  Parsing GEDCOM 5…")
            g5 = Gedcom5x()
            raw = Path(path).read_bytes()
            if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
                # UTF-16 LE or BE — transcode to UTF-8 for the parser
                g5.parse(io.BytesIO(raw.decode("utf-16").encode("utf-8")))
            else:
                g5.parse_file(str(path), strict=False)
            if g5.violations:
                print(f"  {len(g5.violations)} format violation(s):")
                for v in g5.violations:
                    print(f"    ! {v}")
            print("  Validating GEDCOM 5…")
            issues = Gedcom5Validator(g5).validate()
            self._print_validation_results(issues)
            print("  Converting to GedcomX…")
            conv = GedcomConverter()
            gx: GedcomX = conv.Gedcom5x_GedcomX(g5)
            self.gedcomx = gx  # type: ignore[attr-defined]
            return gx

        if src_type == "g7":
            from gedcomtools.gedcom7.validator import GedcomValidator
            print("  Parsing GEDCOM 7…")
            g7 = _load_g7(Path(path))
            print("  Validating GEDCOM 7…")
            issues = GedcomValidator(g7.records).validate()
            self._print_validation_results(issues)
            print("  Note: GEDCOM 7 → GedcomX conversion is not yet implemented.")
            return None

        raise ValueError(f"Cannot determine GEDCOM version for: {path}")

    def _load_from_zip(self, path: str) -> Any:
        from gedcomtools.gedcomx.zip import GedcomZip
        gx = GedcomZip.read(path)
        self.gedcomx = gx  # type: ignore[attr-defined]
        return gx

    def _load_from_json(self, path: str) -> Any:
        from gedcomtools.cli import _load_gx
        try:
            gx = _load_gx(Path(path))
            self.gedcomx = gx  # type: ignore[attr-defined]
            return gx
        except Exception:
            with open(path, "rb") as f:
                return _json_loads(f.read())

    @staticmethod
    def _fetch_url(url: str) -> bytes:
        """Download *url* and return the raw bytes, or print an error and return b''."""
        try:
            with urllib.request.urlopen(url) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            print(f"! HTTP {exc.code} fetching {url}: {exc.reason}")
            return b""
        except urllib.error.URLError as exc:
            print(f"! Cannot fetch {url}: {exc.reason}")
            return b""

    def _load_ged_url(self, url: str) -> Any:
        data = self._fetch_url(url)
        if not data:
            return None
        suffix = Path(url.split("?")[0]).suffix or ".ged"
        fd, tmp = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            return self._load_from_ged(tmp)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _load_zip_url(self, url: str) -> Any:
        from gedcomtools.gedcomx.zip import GedcomZip
        try:
            gx = GedcomZip.load_url(url)
            self.gedcomx = gx  # type: ignore[attr-defined]
            return gx
        except (urllib.error.URLError, ValueError) as exc:
            print(f"! {exc}")
            return None

    def _load_json_url(self, url: str) -> Any:
        data = self._fetch_url(url)
        if not data:
            return None
        try:
            gx = GedcomX.from_dict(_json_loads(data))
            self.gedcomx = gx  # type: ignore[attr-defined]
            return gx
        except Exception:
            return _json_loads(data)

    def _set_root(self, root: Any) -> None:
        self.root = root  # type: ignore[attr-defined]
        self.cur = root  # type: ignore[attr-defined]
        self.path.clear()  # type: ignore[attr-defined]
        self._nav_history.clear()  # type: ignore[attr-defined]

    def _resolve_opt(self, maybe_path: list[str]) -> Any:
        if not maybe_path:
            return self.cur  # type: ignore[attr-defined]
        node, _ = resolve_path(self.root, self.cur, " ".join(maybe_path))  # type: ignore[attr-defined]
        return node

    def _normalize_path(self, raw: str) -> list[str]:
        if raw.startswith("/"):
            parts: list[str] = []
            segs = [s for s in raw.split("/") if s and s != "."]
        else:
            parts = list(self.path)  # type: ignore[attr-defined]
            segs = [s for s in raw.split("/") if s and s != "."]

        for seg in segs:
            if seg == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(seg)
        return parts

    def _node_from_parts(self, parts: list[str]) -> Any:
        node = self.root  # type: ignore[attr-defined]
        for seg in parts:
            key = _seg_to_key(seg)
            node = get_child(node, key)
        return node


class _DataMixin:
    """Mixin for data inspection and editing commands."""

    def _cmd_del(self, args: list[str]) -> None:
        """
        del NAME [NAME2 ...]
        Delete attributes/fields on the current node.
        """
        if not args:
            print("usage: del NAME [NAME2 ...]")
            return

        obj = self.cur  # type: ignore[attr-defined]
        cls = type(obj)

        is_mapping = isinstance(obj, dict)

        def _is_indexable_sequence(o: Any) -> bool:
            if isinstance(o, (str, bytes, bytearray, dict)):
                return False
            return hasattr(o, "__len__") and hasattr(o, "__getitem__")

        for raw_name in args:
            if "=" in raw_name:
                print(f"! ignoring token with '=' in del: {raw_name!r}")
                continue

            name = raw_name.strip()
            if not name:
                print("! empty name in del")
                continue

            if is_mapping and name in obj:
                try:
                    del obj[name]
                except Exception as e:
                    print(f"! error deleting key {name!r} from dict: {e}")
                else:
                    print(f"dict[{name!r}] deleted")
                continue

            if _is_indexable_sequence(obj):
                idx = None
                try:
                    idx = int(name)
                except ValueError:
                    idx = None

                if idx is not None:
                    try:
                        length = len(obj)  # type: ignore[arg-type]
                        if not -length <= idx < length:
                            print(f"! index {idx} out of range (len={length})")
                            continue
                    except Exception:
                        pass

                    try:
                        if hasattr(obj, "__delitem__"):
                            del obj[idx]  # type: ignore[index]
                        elif hasattr(obj, "pop"):
                            obj.pop(idx)  # type: ignore[call-arg]
                        else:
                            raise TypeError("sequence has neither __delitem__ nor pop")
                    except Exception as e:
                        print(f"! error deleting index {idx} on {cls.__name__}: {e}")
                    else:
                        print(f"{cls.__name__}[{idx}] deleted")
                    continue

            if _is_private(name):
                print(f"! refusing to delete private attribute {name!r}")
                continue

            if not hasattr(obj, name):
                print(f"! {cls.__name__}.{name} not found; nothing to delete.")
                continue

            try:
                cls_attr = inspect.getattr_static(cls, name)
            except Exception:
                cls_attr = None

            if isinstance(cls_attr, property):
                if cls_attr.fset is None and cls_attr.fdel is None:
                    print(f"! {cls.__name__}.{name} is a read-only property; cannot delete.")
                    continue
                try:
                    delattr(obj, name)
                except Exception as e:
                    print(f"! error deleting property {cls.__name__}.{name}: {e}")
                else:
                    print(f"{cls.__name__}.{name} (property) deleted")
                continue

            try:
                delattr(obj, name)
            except Exception as e:
                print(f"! error deleting attribute {cls.__name__}.{name}: {e}")
            else:
                print(f"{cls.__name__}.{name} deleted")

    def _cmd_stats(self, args: list[str]) -> None:
        """
        stats
        Show counts for all top-level GedcomX collections.
        """
        _ = args
        if self.gedcomx is None:  # type: ignore[attr-defined]
            print("No GedcomX data loaded.")
            return
        gx = self.gedcomx  # type: ignore[attr-defined]
        rows = [
            ("Persons",             len(gx.persons)),
            ("Relationships",       len(gx.relationships)),
            ("Agents",              len(gx.agents)),
            ("Source Descriptions", len(gx.sourceDescriptions)),
            ("Places",              len(gx.places)),
            ("Events",              len(gx.events)),
            ("Documents",           len(gx.documents)),
            ("Groups",              len(gx.groups)),
        ]
        col_w = max(len(label) for label, _ in rows)
        print(f"{'Collection':<{col_w}}  Count")
        print("-" * (col_w + 8))
        for label, count in rows:
            print(f"{label:<{col_w}}  {count}")
        print("-" * (col_w + 8))
        print(f"{'Total':<{col_w}}  {sum(n for _, n in rows)}")

    def _cmd_grep(self, args: list[str]) -> None:
        """
        grep PATTERN [--all] [--depth N]
        Search field values for PATTERN (case-insensitive regex).
        --all     search from root instead of current node
        --depth N max recursion depth (default 6)
        """
        if not args:
            print("usage: grep PATTERN [--all] [--depth N]")
            return
        pattern: str | None = None
        from_root = False
        max_depth = 6
        i = 0
        while i < len(args):
            if args[i] == "--all":
                from_root = True
            elif args[i] == "--depth" and i + 1 < len(args):
                try:
                    max_depth = int(args[i + 1])
                except ValueError:
                    pass
                i += 1
            elif pattern is None:
                pattern = args[i]
            i += 1
        if pattern is None:
            print("usage: grep PATTERN [--all] [--depth N]")
            return
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            print(f"Invalid regex: {e}")
            return
        start = self.root if from_root else self.cur  # type: ignore[attr-defined]
        if start is None:
            print("No data loaded.")
            return
        results: list[tuple[str, str]] = []
        _grep_node(start, rx, "", results, 0, set(), max_depth)
        if not results:
            print(f"No matches for {pattern!r}.")
            return
        print(f"{len(results)} match(es):")
        for path, val in results[:50]:
            display = val if len(val) <= 80 else val[:77] + "..."
            print(f"  {path}: {display!r}")
        if len(results) > 50:
            print(f"  … and {len(results) - 50} more")

    def _cmd_validate(self, args: list[str]) -> None:
        """
        validate
        Run GedcomX validation on the loaded data and show all issues.
        """
        _ = args
        if self.gedcomx is None:  # type: ignore[attr-defined]
            print("No GedcomX data loaded.")
            return
        result = self.gedcomx.validate()  # type: ignore[attr-defined]
        errors = result.errors
        warnings = result.warnings
        print(f"Validation: {len(errors)} error(s), {len(warnings)} warning(s)")
        if not result.issues:
            print("  OK — no issues found.")
            return
        for issue in result.issues:
            sev = issue.severity
            label = f"{_RED}ERROR{_RESET}" if sev == "error" else "WARN "
            print(f"  {label}  {issue.path}: {issue.message}")

    def _cmd_diff(self, args: list[str]) -> None:
        """
        diff PATH
        Compare the current root against another file by ID.
        Supports .ged, .json, and .zip.
        """
        if not args:
            print("usage: diff PATH")
            return
        if self.gedcomx is None:  # type: ignore[attr-defined]
            print("No GedcomX data loaded (nothing to diff against).")
            return
        path = args[0].strip().strip('"')
        low = path.lower()
        try:
            if low.endswith(".zip"):
                from gedcomtools.gedcomx.zip import GedcomZip
                other = GedcomZip.read(path)
            elif low.endswith(".json"):
                from gedcomtools.cli import _load_gx
                other = _load_gx(Path(path))
            elif low.endswith(".ged"):
                from gedcomtools.cli import _sniff_source_type, _load_g5
                src_type = _sniff_source_type(Path(path))
                if src_type == "g7":
                    print("GEDCOM 7 → GedcomX conversion not yet implemented.")
                    return
                g5 = _load_g5(Path(path))
                other = GedcomConverter().Gedcom5x_GedcomX(g5)
            else:
                print(f"Unsupported file type: {path}")
                return
        except Exception as e:
            print(f"Error loading {path}: {e}")
            return

        _colls = [
            ("persons",            self.gedcomx.persons,            other.persons),  # type: ignore[attr-defined]
            ("relationships",      self.gedcomx.relationships,      other.relationships),  # type: ignore[attr-defined]
            ("agents",             self.gedcomx.agents,             other.agents),  # type: ignore[attr-defined]
            ("sourceDescriptions", self.gedcomx.sourceDescriptions, other.sourceDescriptions),  # type: ignore[attr-defined]
            ("places",             self.gedcomx.places,             other.places),  # type: ignore[attr-defined]
            ("events",             self.gedcomx.events,             other.events),  # type: ignore[attr-defined]
            ("documents",          self.gedcomx.documents,          other.documents),  # type: ignore[attr-defined]
            ("groups",             self.gedcomx.groups,             other.groups),  # type: ignore[attr-defined]
        ]

        print(f"Diff: current  ←→  {path}")
        any_diff = False
        for cname, cur_coll, other_coll in _colls:
            cur_ids   = {getattr(o, "id", None) for o in cur_coll}   - {None}
            other_ids = {getattr(o, "id", None) for o in other_coll} - {None}
            added   = other_ids - cur_ids
            removed = cur_ids - other_ids
            common  = cur_ids & other_ids
            if not added and not removed:
                continue
            any_diff = True
            total_a = len(cur_coll)
            total_b = len(other_coll)
            print(f"\n  {cname}: {total_a} current / {total_b} other")
            if added:
                print(f"    + {len(added)} added in other")
                for oid in sorted(added)[:5]:
                    print(f"        {oid}")
                if len(added) > 5:
                    print(f"        … and {len(added) - 5} more")
            if removed:
                print(f"    - {len(removed)} only in current")
                for oid in sorted(removed)[:5]:
                    print(f"        {oid}")
                if len(removed) > 5:
                    print(f"        … and {len(removed) - 5} more")
            if common:
                print(f"    = {len(common)} in common (field-level diff not yet implemented)")
        if not any_diff:
            print("  No differences found by ID.")

    def _cmd_cd(self, args: list[str]) -> None:
        """
        cd [PATH]
        Change current node. No args resets to root.
        """
        self._nav_history.append((self.cur, list(self.path)))  # type: ignore[attr-defined]
        if not args:
            self.cur = self.root  # type: ignore[attr-defined]
            self.path = []  # type: ignore[attr-defined]
            return

        raw = " ".join(args).strip()
        parts = self._normalize_path(raw)  # type: ignore[attr-defined]
        try:
            node = self._node_from_parts(parts)  # type: ignore[attr-defined]
        except Exception as e:
            self._nav_history.pop()  # type: ignore[attr-defined]
            print(f"! Error: {e}")
            return

        self.path = parts  # type: ignore[attr-defined]
        self.cur = node  # type: ignore[attr-defined]

    def _cmd_pwd(self, args: list[str]) -> None:
        """
        pwd
        Print the current path.
        """
        _ = args
        print("/" + "/".join(self.path))  # type: ignore[attr-defined]

    def _cmd_dump(self, args: list[str]) -> None:
        """
        dump [PATH]
        Print node as JSON (always).
        """
        node = self._resolve_opt(args)  # type: ignore[attr-defined]
        print(_json_dumps(node))

    def _cmd_show(self, args: list[str]) -> None:
        """
        show [PATH]
        show persons
          - With a normal PATH (or no args): pretty-print the resolved node as JSON.
          - With a top-level collection name (e.g. 'persons'): list its items in a table.
        """
        if args and self.root is not None and isinstance(args[0], str):  # type: ignore[attr-defined]
            top = args[0]
            if (not top.startswith("/")) and hasattr(self.root, top):  # type: ignore[attr-defined]
                coll = getattr(self.root, top, None)  # type: ignore[attr-defined]
                items = as_indexable_list(coll) or []
                if not items:
                    print(f"(root.{top} is empty or None)")
                    return

                rows: list[list[str]] = []
                for idx, item in enumerate(items):
                    pid = _get_item_id(item)
                    pid_str = "" if pid is None else str(pid)

                    pname_str = ""
                    try:
                        if hasattr(item, "name"):
                            pname = getattr(item, "name")
                            pname_str = "" if pname is None else str(pname)
                    except Exception:
                        pname_str = ""

                    if not pname_str:
                        try:
                            pname_str = short_preview(item, max_len=60)
                        except Exception:
                            pname_str = f"<{type(item).__name__}>"

                    rows.append([str(idx), pid_str, pname_str])

                _print_table(rows, ["idx", "id", "name"])
                return

        node = self._resolve_opt(args)  # type: ignore[attr-defined]
        print(_json_dumps(node))

    def _cmd_getprop(self, args: list[str]) -> None:
        """
        getprop NAME [NAME ...]
        Print values of @property descriptors defined on the class.
        """
        if not args:
            print("usage: getprop NAME [NAME ...]")
            return

        cls = type(self.cur)  # type: ignore[attr-defined]
        for name in args:
            attr = inspect.getattr_static(cls, name, None)
            if isinstance(attr, property):
                try:
                    value = getattr(self.cur, name)  # type: ignore[attr-defined]
                except Exception as e:
                    print(f"{cls.__name__}.{name} is a @property but raised: {e!r}")
                else:
                    print(f"{cls.__name__}.{name} = {value!r}")
            else:
                if hasattr(self.cur, name) or hasattr(cls, name):  # type: ignore[attr-defined]
                    kind = "method" if callable(getattr(self.cur, name, None)) else "attribute"  # type: ignore[attr-defined]
                    print(f"{cls.__name__}.{name} exists but is not a @property ({kind})")
                else:
                    print(f"{cls.__name__}.{name} not found")

    def _cmd_props(self, args: list[str]) -> None:
        """
        props [--instance] [--class] [--private]
        List instance attrs + class properties/attrs with current values.
        """
        show_instance = "--class" not in args
        show_class = "--instance" not in args
        include_private = "--private" in args

        obj = self.cur  # type: ignore[attr-defined]
        cls = type(obj)

        def _ok(name: str) -> bool:
            return include_private or not name.startswith("_")

        rows: list[list[str]] = []
        seen_class_names: set[str] = set()

        if show_instance and hasattr(obj, "__dict__"):
            for name, val in sorted(vars(obj).items(), key=lambda kv: kv[0]):
                if not _ok(name):
                    continue
                rows.append(["instance", "data", name, short_preview(val)])

        if show_class:
            for base in cls.mro():
                for name, attr in base.__dict__.items():
                    if name in seen_class_names:
                        continue
                    if not _ok(name):
                        continue
                    seen_class_names.add(name)

                    if isinstance(attr, property):
                        kind = "property"
                        try:
                            val = getattr(obj, name)
                        except Exception as e:
                            val = f"<raised {e.__class__.__name__}: {e}>"
                        rows.append(["class", kind, name, short_preview(val)])
                    else:
                        if not callable(attr):
                            rows.append(["class", "attr", name, short_preview(attr)])

        if not rows:
            print("(no matching properties)")
            return

        _print_table(rows, ["scope", "kind", "name", "value"])

    def _cmd_getattr(self, args: list[str]) -> None:
        """
        getattr NAME [NAME ...]
        Smart getattr that prints value and kind.
        """
        if not args:
            print("usage: getattr NAME [NAME ...]")
            return
        clsname = type(self.cur).__name__  # type: ignore[attr-defined]
        for name in args:
            value, kind = smart_getattr(self.cur, name)  # type: ignore[attr-defined]
            print(f"{clsname}.{name} = {value!r}  ({kind})")

    def _cmd_methods(self, args: list[str]) -> None:
        """
        methods [--private] [--own] [--match SUBSTR]
        List callable methods on current node.
        """
        include_private = "--private" in args
        own_only = "--own" in args

        match = None
        if "--match" in args:
            idx = args.index("--match")
            if idx + 1 >= len(args):
                print("usage: methods [--private] [--own] [--match SUBSTR]")
                return
            match = args[idx + 1].lower()

        obj = self.cur  # type: ignore[attr-defined]
        rows = []
        seen = set()

        for cls in (type(obj).mro() if not own_only else [type(obj)]):
            for name, member in cls.__dict__.items():
                if not include_private and _is_private(name):
                    continue
                if isinstance(member, property):
                    continue
                is_callish = (
                    inspect.isfunction(member)
                    or inspect.ismethod(member)
                    or inspect.ismethoddescriptor(member)
                    or isinstance(member, (staticmethod, classmethod))
                    or callable(getattr(obj, name, None))
                )
                if not is_callish:
                    continue
                if name in seen:
                    continue
                if match and match not in name.lower():
                    continue

                seen.add(name)
                bound = getattr(obj, name, member)
                sig = _format_signature(bound)
                owner = _declaring_class(obj, name)

                doc = ""
                try:
                    doc_src = inspect.getdoc(member) or ""
                    if doc_src:
                        doc = doc_src.strip().splitlines()[0]
                except Exception:
                    pass

                rows.append([name, sig, owner, doc])

        if not rows:
            print("(no methods)")
            return

        rows.sort(key=lambda r: (r[2] != type(self.cur).__name__, r[0]))  # type: ignore[attr-defined]
        _print_table(rows, ["name", "signature", "defined in", "doc"])

    def _cmd_call(self, args: list[str]) -> None:
        """
        call NAME [args...] [kw=val ...]
        Call a method on the current node with coerced args.
        """
        if not args:
            print("usage: call NAME [args...] [kw=val ...]")
            return

        name, *rest = args
        target = getattr(self.cur, name, None)  # type: ignore[attr-defined]
        if target is None or not callable(target):
            print(f"! method '{name}' not found or not callable on {type(self.cur).__name__}")  # type: ignore[attr-defined]
            return

        try:
            pos, kw = _split_args_kwargs(rest)
        except ValueError as e:
            print(f"! {e}")
            return

        try:
            sig = inspect.signature(target)
            sig.bind_partial(*pos, **kw)
        except (TypeError, ValueError) as e:
            print(f"! argument error: {e}")
            return

        try:
            result = target(*pos, **kw)
        except Exception as e:
            print(f"! call raised {e.__class__.__name__}: {e}")
            return

        if result is None:
            print("Result: None")
        else:
            print("Result:", short_preview(result, 200))

    def _cmd_ls(self, args: list[str]) -> None:
        """
        ls [PATH] [--full]
           --full : do not abbreviate long runs in lists/collections
        """
        ABBREV_RUN_MIN = 3
        no_abbrev = False

        path_args: list[str] = []
        for a in args:
            if a == "--full":
                no_abbrev = True
            else:
                path_args.append(a)

        class _Elided:
            __slots__ = ("type_name", "count")

            def __init__(self, type_name: str, count: int) -> None:
                self.type_name = type_name
                self.count = count

            def __repr__(self) -> str:
                return f"… {self.type_name} × {self.count}"

        def _short_type_str(s: str) -> str:
            if not s:
                return s
            s = s.replace("gedcomx.gedcomx.", "").replace("gedcomx.", "").replace("typing.", "")
            s = re.sub(r"(?:\b[\w]+\.)+([A-Z]\w+)", r"\1", s)
            s = re.sub(r"\s*\|\s*NoneType", "?", s)
            s = re.sub(r"NoneType\s*\|\s*", "", s)
            return s

        def _actual_type_str(v: Any) -> str:
            if isinstance(v, _Elided):
                return "…"
            it = getattr(v, "item_type", None)
            if it is not None:
                return f"TypeCollection[{getattr(it, '__name__', str(it))}]"
            t = type(v)
            n = getattr(t, "__name__", str(t))
            if n == "NoneType":
                return "None"
            if n in ("list", "tuple", "set", "dict"):
                return n.capitalize()
            return n

        def _type_key(v: Any) -> str:
            it = getattr(v, "item_type", None)
            if it is not None:
                return f"TypeCollection[{getattr(it, '__name__', str(it))}]"
            return getattr(type(v), "__name__", str(type(v)))

        def _preview(v: Any, width: int) -> str:
            if isinstance(v, _Elided):
                return _clip(repr(v), width)

            base: str | None = None
            if not is_primitive(v) and not isinstance(v, (dict, list, tuple, set)):
                try:
                    s = str(v)
                    if not (s.startswith("<") and "object at 0x" in s):
                        base = s
                except Exception as e:
                    base = f"<str-error: {type(e).__name__}>"

            if base is None:
                try:
                    base = short_preview(v)
                except Exception as e:
                    base = f"<preview-error: {type(e).__name__}>"

            try:
                id_val = _get_item_id(v)
                if id_val is not None and f"id={id_val!r}" not in base:
                    base = f"{base} (id={id_val!r})"
            except Exception:
                pass

            return _clip(base, width)

        if path_args:
            raw = " ".join(path_args).strip()
            abs_parts = self._normalize_path(raw)  # type: ignore[attr-defined]
            try:
                node = self._node_from_parts(abs_parts)  # type: ignore[attr-defined]
            except Exception as e:
                print(f"! Error: {e}")
                return
        else:
            node = self.cur  # type: ignore[attr-defined]
            abs_parts = list(self.path)  # type: ignore[attr-defined]

        rows = list_fields(node)
        if not rows:
            print("(no fields)")
            return

        expected_map: dict[str, Any] = {}
        expected_disp: dict[str, str] = {}

        col = as_indexable_list(node)
        if col is not None:
            if abs_parts:
                parent = self.root  # type: ignore[attr-defined]
                for seg in abs_parts[:-1]:
                    parent = get_child(
                        parent,
                        int(seg) if (seg.isdigit() or (seg.startswith("-") and seg[1:].isdigit())) else seg,
                    )
                field_name = abs_parts[-1]
                elem_tp = _expected_element_type_from_parent(parent, field_name)
                parent_field_tp = _schema_fields_for_object(parent).get(field_name)
                container_disp = type_repr(parent_field_tp) if parent_field_tp is not None else "-"
            else:
                elem_tp = None
                container_disp = "-"

            mat = list(col)

            if no_abbrev:
                rows = [(str(i), mat[i]) for i in range(len(mat))]
            else:
                collapsed: list[tuple[str, Any]] = []
                i = 0
                while i < len(mat):
                    k0 = _type_key(mat[i])
                    j = i + 1
                    while j < len(mat) and _type_key(mat[j]) == k0:
                        j += 1
                    run_len = j - i
                    if run_len >= ABBREV_RUN_MIN:
                        collapsed.append((str(i), mat[i]))
                        collapsed.append(("…", _Elided(k0, run_len - 2)))
                        collapsed.append((str(j - 1), mat[j - 1]))
                    else:
                        for k in range(i, j):
                            collapsed.append((str(k), mat[k]))
                    i = j
                rows = collapsed

            for idx, _v in rows:
                if idx != "…":
                    expected_map[idx] = elem_tp
                    exp = (
                        type_repr(elem_tp)
                        if (elem_tp is not None and not isinstance(elem_tp, str))
                        else (elem_tp if isinstance(elem_tp, str) else container_disp)
                    )
                    expected_disp[idx] = _short_type_str(exp or "-")
                else:
                    expected_map[idx] = None
                    expected_disp[idx] = _short_type_str(container_disp or "-")

        else:
            schema_raw = _schema_fields_for_object(node)
            for name, val in rows:
                tp = schema_raw.get(name)
                if tp is None:
                    item_type = getattr(val, "item_type", None)
                    if item_type is not None:
                        tp = item_type
                        exp = f"TypeCollection[{getattr(item_type, '__name__', str(item_type))}]"
                    else:
                        exp = "-"
                else:
                    exp = type_repr(tp)
                expected_map[name] = tp
                expected_disp[name] = _short_type_str(exp)

        term_width = shutil.get_terminal_size((150, 24)).columns
        name_vals = [name for name, _ in rows]
        type_vals = [_actual_type_str(val) for _, val in rows]
        schema_vals = [expected_disp.get(name, "-") for name, _ in rows]

        w_name = min(max(6, *(len(n) for n in name_vals)), 40)
        w_type = min(max(6, *(len(_sans_ansi(t)) for t in type_vals)), 32)
        w_schema = min(max(8, *(len(s) for s in schema_vals)), 72)

        fixed = w_name + w_type + w_schema + 9
        w_prev = max(24, term_width - fixed)

        print(
            f"{_clip('name', w_name).ljust(w_name)} | "
            f"{_clip('type', w_type).ljust(w_type)} | "
            f"{_clip('schema', w_schema).ljust(w_schema)} | "
            f"{'preview'}"
        )
        print(
            f"{'-'*w_name} | "
            f"{'-'*w_type} | "
            f"{'-'*w_schema} | "
            f"{'-'*min(w_prev, 40)}"
        )

        for name, val in rows:
            actual_raw = _actual_type_str(val)
            exp_obj = expected_map.get(name)
            exp_disp = expected_disp.get(name, "-")

            mism = (name != "…") and (not _names_match(exp_obj, val))

            actual_shown = _clip(actual_raw, w_type)
            actual_shown = _red(actual_shown) if mism else actual_shown

            line = (
                f"{_clip(name, w_name).ljust(w_name)} | "
                f"{actual_shown.ljust(w_type + (len(actual_shown) - len(_sans_ansi(actual_shown))))} | "
                f"{_clip(exp_disp, w_schema).ljust(w_schema)} | "
                f"{_preview(val, w_prev)}"
            )
            print(line)

    def _cmd_set(self, args: list[str]) -> None:
        """
        set NAME VALUE
        set NAME=VALUE [NAME2=VALUE2 ...]
        set --n NAME [NAME2 ...]
        """
        if not args:
            print("usage: set NAME VALUE  |  set NAME=VALUE [NAME2=VALUE2 ...]  |  set --n NAME [NAME2 ...]")
            return

        new_mode = False
        clean_args: list[str] = []
        for a in args:
            if a == "--n":
                new_mode = True
            else:
                clean_args.append(a)
        args = clean_args

        obj = self.cur  # type: ignore[attr-defined]
        cls = type(obj)

        def _instantiate_for_field(field_name: str) -> Any:
            elem_type = _expected_element_type_from_parent(obj, field_name)
            if elem_type is None:
                fields = SCHEMA.get_class_fields(type(obj).__name__) or {}
                field_type = fields.get(field_name)
                if field_type is None:
                    raise ValueError(f"no schema info for field {field_name!r}")
                elem_type = field_type

            def _strip_optional(tp: Any) -> Any:
                origin = get_origin(tp)
                if origin is None:
                    return tp
                args2 = [a for a in get_args(tp) if a is not type(None)]  # noqa: E721
                return args2[0] if args2 else tp

            elem_type2 = _strip_optional(elem_type)

            primitive_defaults = {str: "", int: 0, float: 0.0, bool: False}

            if isinstance(elem_type2, type):
                if elem_type2 in primitive_defaults:
                    return primitive_defaults[elem_type2]
                try:
                    return elem_type2()
                except Exception as e:
                    raise TypeError(f"cannot instantiate {elem_type2} without args: {e}") from e

            raise TypeError(f"unsupported schema type for field {field_name!r}: {elem_type2!r}")

        if new_mode:
            if not args:
                print("usage: set --n NAME [NAME2 ...]")
                return

            for name in args:
                if "=" in name:
                    print(f"! in --n mode, use bare field names only (got {name!r})")
                    continue
                if _is_private(name):
                    print(f"! refusing to create for private attribute {name!r}")
                    continue

                cur_val = getattr(obj, name, None) if hasattr(obj, name) else None

                is_collection = False
                if cur_val is not None:
                    col = as_indexable_list(cur_val)
                    if col is not None and not isinstance(cur_val, dict) and not isinstance(cur_val, (str, bytes, bytearray)):
                        is_collection = True

                try:
                    new_instance = _instantiate_for_field(name)
                except Exception as e:
                    print(f"! cannot create new instance for field {cls.__name__}.{name}: {e}")
                    continue

                if is_collection:
                    if hasattr(cur_val, "append"):
                        try:
                            idx = len(cur_val)  # type: ignore
                        except Exception:
                            idx = "?"
                        try:
                            cur_val.append(new_instance)  # type: ignore
                        except Exception as e:
                            print(f"! error appending to {cls.__name__}.{name}: {e}")
                            continue
                        print(f"{cls.__name__}.{name}[{idx}] ← new {type(new_instance).__name__}()")
                    else:
                        print(f"! field {cls.__name__}.{name} looks like a collection but has no append(); not modifying.")
                else:
                    try:
                        setattr(obj, name, new_instance)
                    except Exception as e:
                        print(f"! error setting {cls.__name__}.{name} to new instance: {e}")
                        continue
                    print(f"{cls.__name__}.{name} = new {type(new_instance).__name__}()")
            return

        assignments: dict[str, Any] = {}

        if any("=" in a for a in args):
            for tok in args:
                if "=" not in tok:
                    print(f"! ignoring token without '=': {tok!r}")
                    continue
                name, val_str = tok.split("=", 1)
                name = name.strip()
                if not name:
                    print("! empty attribute name")
                    continue
                if _is_private(name):
                    print(f"! refusing to set private attribute {name!r}")
                    continue

                value = _coerce_token(val_str)
                if not is_primitive(value):
                    print(f"! value for {name!r} is not primitive (got {type(value).__name__})")
                    continue

                assignments[name] = value
        else:
            if len(args) < 2:
                print("usage: set NAME VALUE  |  set NAME=VALUE [NAME2=VALUE2 ...]  |  set --n NAME [NAME2 ...]")
                return

            name = args[0]
            if _is_private(name):
                print(f"! refusing to set private attribute {name!r}")
                return

            val_str = " ".join(args[1:])
            value = _coerce_token(val_str)
            if not is_primitive(value):
                print(f"! value for {name!r} is not primitive (got {type(value).__name__})")
                return
            assignments[name] = value

        for name, value in assignments.items():
            try:
                cls_attr = inspect.getattr_static(cls, name)
            except Exception:
                cls_attr = None

            if isinstance(cls_attr, property):
                if cls_attr.fset is None:
                    print(f"! {cls.__name__}.{name} is a read-only property; not setting.")
                    continue
                try:
                    setattr(obj, name, value)
                except Exception as e:
                    print(f"! error setting property {cls.__name__}.{name}: {e}")
                else:
                    print(f"{cls.__name__}.{name} = {value!r}  (property)")
                continue

            if not hasattr(obj, name):
                print(f"! {cls.__name__} has no attribute {name!r}; refusing to create new attributes.")
                continue

            try:
                cur_val = getattr(obj, name)
            except Exception:
                cur_val = None
            if cur_val is not None and not is_primitive(cur_val):
                print(f"! {cls.__name__}.{name} currently holds {type(cur_val).__name__}, refusing to overwrite.")
                continue

            try:
                setattr(obj, name, value)
            except Exception as e:
                print(f"! error setting {cls.__name__}.{name}: {e}")
            else:
                print(f"{cls.__name__}.{name} = {value!r}")

    def _cmd_resolve(self, args: list[str]) -> None:
        """
        resolve
        Resolve resource references in the current root.
        """
        _ = args
        if isinstance(self.root, GedcomX) and (self.root is not None):  # type: ignore[attr-defined]
            print("Resolving resource references (size may affect time)…")
            stats = ResolveStats()
            Serialization._resolve_structure(self.root, self.root._resolve, stats=stats)  # type: ignore[attr-defined]
            print("total refs:", stats.total_refs)
            print("cache hits:", stats.cache_hits, "misses:", stats.cache_misses)
            print("ok:", stats.resolved_ok, "fail:", stats.resolved_fail)
            print("by ref type:", stats.by_ref_type)
            print("by target type:", stats.by_target_type)
            print("resolver time (ms):", round(stats.resolver_time_ms, 2))
            for f in stats.failures:
                print("FAIL", f)
        else:
            print("Root is not a GedcomX object, no resolver available.")

    def _cmd_write(self, args: list[str]) -> int | None:
        """
        write gx PATH      Write current root as GEDCOM-X JSON.
        write zip PATH     Write current root as a GEDCOM-X ZIP archive.
        write jsonl PATH   Write current node as JSON-L.
        write adbg DIR     Write ArangoDB graph files.
        """
        if len(args) < 2 or args[0] not in ["gx", "zip", "adbg", "jsonl"]:
            print("usage: write FORMAT[gx | zip | adbg | jsonl] PATH")
            return None
        if args[0] == "zip":
            from gedcomtools.gedcomx.zip import GedcomZip
            if self.root is None:  # type: ignore[attr-defined]
                print("No data loaded.")
                return None
            path = args[1].strip('"').strip("'")
            if not path.lower().endswith(".zip"):
                path += ".zip"
            with GedcomZip(path) as gz:
                arcname = gz.add_object_as_resource(self.root)  # type: ignore[attr-defined]
            if arcname:
                print(f"Written: {gz.path}  ({arcname})")
            else:
                print("Root is not a GedcomX object; nothing written.")
            return None
        if args[0] == "gx":
            js = orjson.dumps(
                self.root._to_dict(),  # type: ignore[attr-defined]
                option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE,
            )
            with open(args[1], "wb") as f:
                f.write(js)
        elif args[0] == "jsonl":
            if self.cur is not None:  # type: ignore[attr-defined]
                path = Path(args[1].strip('"').strip("'"))
                return write_jsonl(self.cur, Path(path))  # type: ignore[attr-defined]
            print("usage: write FORMAT[gx | adbg | jsonl] PATH")
            return None
        elif args[0] == "adbg":
            if args[1]:
                argo_graph_files_folder = Path(args[1])
                argo_graph_files_folder.mkdir(parents=True, exist_ok=True)
                print('Writing Argo Graph Files')
                if self.root is None:  # type: ignore[attr-defined]
                    print("No data loaded.")
                    return None
                file_specs = make_arango_graph_files(self.root)  # type: ignore[attr-defined]
                persons_file = argo_graph_files_folder / 'persons.jsonl'
                with persons_file.open("w", encoding="utf-8") as f:
                    for line in file_specs['persons']:
                        print('Writing Person')
                        f.write(json.dumps(line))
                        f.write("\n")
                persons_to_file = argo_graph_files_folder / 'person_to_person.jsonl'
                with persons_to_file.open("w", encoding="utf-8") as f:
                    for line in file_specs['relationships']:
                        print('Writing Relationship')
                        f.write(json.dumps(line))
                        f.write("\n")
        return None
