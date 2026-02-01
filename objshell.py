#!/usr/bin/env python3
from __future__ import annotations

"""
======================================================================
 Project: ObjectShell
 File:    objshell.py
 Author:  David J. Cartwright (base structure inspired)
 Purpose: Generic CLI to inspect and manipulate arbitrary Python objects

 Features:
   - Command registry with metadata (aliases, help, categories)
   - Read-only mode for safety
   - Generic navigation over dict / list / object attributes
   - ls / cd / pwd / show / dump / type / getattr / methods / call / set / del
   - Bookmarks: mark, marks, goto
   - Search: findname, grep
   - Colorized, ANSI-safe table output
   - Optional readline support + persistent history
   - Debug mode via OBJSHELL_DEBUG=1

 Created: 2025-11-20
======================================================================
"""

import argparse
import ast
import dataclasses
import json
import os
import re
import shlex
import sys
import traceback
from dataclasses import dataclass, asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# ── Optional orjson support ──────────────────────────────────────────────────
try:
    import orjson as _orjson  # type: ignore[import]
except Exception:
    _orjson = None

# ── Optional readline support (for history, editing) ─────────────────────────
try:
    if sys.platform != "win32":
        import readline  # type: ignore[import]  # noqa: F401

        _HISTORY_PATH = Path(os.path.expanduser("~/.objshell_history"))
        if _HISTORY_PATH.is_file():
            try:
                readline.read_history_file(str(_HISTORY_PATH))
            except Exception:
                pass
    else:
        _HISTORY_PATH = None
except Exception:
    _HISTORY_PATH = None

# ── ANSI / colors ────────────────────────────────────────────────────────────
ANSI = {
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "cyan": "\x1b[36m",
    "dim": "\x1b[2m",
    "reset": "\x1b[0m",
}

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")




def _sans_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _pad_ansi(s: str, width: int) -> str:
    """Left-justify a string containing ANSI codes to a visual width."""
    visible = len(_sans_ansi(s))
    pad = max(0, width - visible)
    return s + " " * pad


def _clip(s: str, width: int) -> str:
    if width <= 1:
        return "" if width <= 0 else s[:1]
    return s if len(s) <= width else s[: width - 1] + "…"


# ── Primitive / plainification helpers ───────────────────────────────────────
_PRIMITIVES = (str, int, float, bool, type(None))


def is_primitive(x: Any) -> bool:
    return isinstance(x, _PRIMITIVES)


def _maybe_as_dict(obj: Any) -> Any:
    """Best-effort conversion of arbitrary object to a dict-like structure."""
    # Custom protocol: _as_dict_
    if hasattr(obj, "_as_dict_"):
        attr = getattr(obj, "_as_dict_")
        try:
            return attr() if callable(attr) else attr
        except Exception:
            pass

    # Pydantic-style
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return obj.model_dump()
        except Exception:
            pass

    # Dataclasses
    if is_dataclass(obj):
        try:
            return asdict(obj)
        except Exception:
            pass

    # Generic __dict__
    if hasattr(obj, "__dict__"):
        d = {k: v for k, v in vars(obj).items() if not k.startswith("_")}
        if d:
            return d

    return obj


def to_plain(obj: Any, *, max_depth: int = 6, _seen: Optional[set[int]] = None) -> Any:
    """Recursively convert objects to JSON-serializable primitives."""
    if _seen is None:
        _seen = set()
    oid = id(obj)
    if oid in _seen:
        return f"<…cycle {type(obj).__name__}…>"
    _seen.add(oid)

    if is_primitive(obj):
        return obj
    if isinstance(obj, (bytes, bytearray)):
        return f"<{type(obj).__name__} len={len(obj)}>"

    if isinstance(obj, (list, tuple, set)):
        if max_depth <= 0:
            return f"<{type(obj).__name__} len={len(obj)}>"
        return [to_plain(v, max_depth=max_depth - 1, _seen=_seen) for v in obj]

    if isinstance(obj, dict):
        if max_depth <= 0:
            return f"<dict len={len(obj)}>"
        return {str(k): to_plain(v, max_depth=max_depth - 1, _seen=_seen) for k, v in obj.items()}

    obj2 = _maybe_as_dict(obj)
    if obj2 is obj:
        return repr(obj)
    return to_plain(obj2, max_depth=max_depth, _seen=_seen)

def _abbrev_value(val: Any, max_items: int = 5) -> Any:
    """
    Abbreviate long list-like or dict-like values before preview.

    - For list/sequence-like values: show only the first few items and total count.
    - For dicts: show only the first few keys and total key count.
    - Everything else: returned as-is (preview is handled by short_preview).
    """
    col = as_indexable_list(val)
    if col is not None and not isinstance(val, dict):
        length = len(col)
        if length > max_items:
            preview_items = [short_preview(x, 20) for x in col[:max_items]]
            return f"[{', '.join(preview_items)}, ... ({length} items)]"
        else:
            return f"[{', '.join(short_preview(x, 20) for x in col)}]"

    if isinstance(val, dict):
        keys = list(val.keys())
        length = len(keys)
        if length > max_items:
            first = keys[:max_items]
            return f"{{{', '.join(map(str, first))}, ... ({length} keys)}}"
        else:
            return f"{{{', '.join(map(str, keys))}}}"

    return val

def short_preview(val: Any, max_len: int = 80) -> str:
    """1-line preview of a value for tabular listing."""
    if is_primitive(val):
        s = repr(val)
        return s if len(s) <= max_len else s[: max_len - 1] + "…"
    if isinstance(val, dict):
        return f"<dict len={len(val)}>"
    if isinstance(val, (list, tuple, set)):
        return f"<{type(val).__name__} len={len(val)}>"
    col = as_indexable_list(val)
    if col is not None:
        return f"<{type(val).__name__} len={len(col)}>"
    try:
        s = str(val)
        if not (s.startswith("<") and "object at 0x" in s):
            return _clip(s, max_len)
    except Exception:
        pass
    return f"<{type(val).__name__}>"

def list_fields(obj: Any) -> List[Tuple[str, Any]]:
    """Enumerate fields/items for listing based on runtime type."""
    if isinstance(obj, dict):
        return [(str(k), v) for k, v in obj.items()]
    if isinstance(obj, (list, tuple)):
        return [(str(i), v) for i, v in enumerate(obj)]
    col = as_indexable_list(obj)
    if col is not None:
        return [(str(i), v) for i, v in enumerate(col)]
    if is_dataclass(obj):
        return [(f.name, getattr(obj, f.name)) for f in dataclasses.fields(obj)]
    if hasattr(obj, "__dict__"):
        return [(k, v) for k, v in vars(obj).items() if not k.startswith("_")]
    return []

def as_indexable_list(obj: Any) -> Optional[List[Any]]:
    """Coerce indexable/iterable containers to list; return None if not a collection."""
    if obj is None or isinstance(obj, (str, bytes, bytearray, dict)):
        return None
    if isinstance(obj, (list, tuple, set)):
        return list(obj)
    if hasattr(obj, "__len__") and hasattr(obj, "__getitem__"):
        try:
            return [obj[i] for i in range(len(obj))]  # type: ignore[index]
        except Exception:
            pass
    if hasattr(obj, "items"):
        try:
            items = obj.items() if callable(obj.items) else obj.items
            from collections.abc import Iterable as _Iterable  # noqa

            return list(items) if isinstance(items, _Iterable) else None
        except Exception:
            pass
    if hasattr(obj, "__iter__"):
        try:
            return list(obj)
        except Exception:
            pass
    return None


# ── Path navigation helpers ──────────────────────────────────────────────────
def _seg_to_key(seg: str) -> Any:
    if seg.isdigit() or (seg.startswith("-") and seg[1:].isdigit()):
        return int(seg)
    return seg


def get_child(parent: Any, key: int | str) -> Any:
    """Generic child-access across dict / list / sequence / object attribute."""
    if isinstance(parent, dict):
        return parent[key]

    if isinstance(parent, (list, tuple)):
        if isinstance(key, int):
            return parent[key]
        raise KeyError("List index must be int")

    col = as_indexable_list(parent)
    if col is not None:
        if isinstance(key, int):
            return col[key]
        raise KeyError("Collection index must be int")

    if not isinstance(key, int) and hasattr(parent, key):
        return getattr(parent, key)

    if hasattr(parent, "__getitem__"):
        return parent[key]  # type: ignore[index]

    raise KeyError(f"Cannot access key/attr {key!r} on {type(parent).__name__}")


def resolve_path(root: Any, cur: Any, path: str) -> Tuple[Any, List[str]]:
    """Resolve a path-like expression to a node and return (node, absolute_path_parts)."""
    if not path or path == ".":
        return cur, []
    node = root if path.startswith("/") else cur
    parts = [p for p in path.strip("/").split("/") if p]
    stack: List[str] = []
    for seg in parts:
        if seg == ".":
            continue
        if seg == "..":
            if stack:
                stack.pop()
            continue
        key = _seg_to_key(seg)
        node = get_child(node, key)
        stack.append(seg)
    return node, stack


# ── JSON helpers ─────────────────────────────────────────────────────────────
def json_dumps(obj: Any, *, max_depth: int = 6) -> str:
    """Pretty JSON dump, preferring orjson, after plainifying."""
    plain = to_plain(obj, max_depth=max_depth)
    if _orjson is not None:
        try:
            return _orjson.dumps(plain, option=_orjson.OPT_INDENT_2).decode("utf-8")
        except Exception:
            pass
    return json.dumps(plain, ensure_ascii=False, indent=2)


# ── CLI token coercion ───────────────────────────────────────────────────────
def _is_private(name: str) -> bool:
    return name.startswith("_")


def _coerce_token(tok: str) -> Any:
    """
    Best-effort safe coercion from string to Python value.
    Tries: literal_eval → booleans/None → as-is string.
    """
    t = tok.strip()
    low = t.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low == "none":
        return None
    try:
        return ast.literal_eval(t)
    except Exception:
        return t


def _split_args_kwargs(tokens: List[str]) -> Tuple[List[Any], Dict[str, Any]]:
    """
    Split CLI tokens into (args, kwargs). kw tokens are of the form key=value.
    Values are coerced with _coerce_token.
    """
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    for tok in tokens:
        if "=" in tok:
            key, val = tok.split("=", 1)
            key = key.strip()
            if not key or _is_private(key):
                raise ValueError(f"invalid keyword '{key}'")
            kwargs[key] = _coerce_token(val)
        else:
            args.append(_coerce_token(tok))
    return args, kwargs



# ── Table rendering ──────────────────────────────────────────────────────────
def print_table(rows: Iterable[Iterable[str]], headers: List[str]) -> None:
    rows = [[str(c) for c in r] for r in rows]
    widths = [len(h) for h in headers]

    # Compute column widths based on *visible* length
    for r in rows:
        for i, col in enumerate(r):
            widths[i] = max(widths[i], len(_sans_ansi(col)))

    def fmt(row: List[str]) -> str:
        cells: List[str] = []
        for i, c in enumerate(row):
            # clip first on raw string
            clipped = _clip(c, widths[i])
            # pad taking ANSI into account
            padded = _pad_ansi(clipped, widths[i])

            # If there is any ANSI in this cell, make sure we end with a reset,
            # so even if we clipped in the middle of a color code, the terminal
            # won't "bleed" color into the rest of the line.
            if "\x1b[" in padded and not padded.endswith(ANSI["reset"]):
                padded += ANSI["reset"]

            cells.append(padded)
        return " | ".join(cells)

    print(fmt(headers))
    print(" | ".join("-" * w for w in widths))
    for r in rows:
        print(fmt(r))


# ── Command registry ─────────────────────────────────────────────────────────
@dataclass
class Command:
    func: Callable[[List[str]], None]
    aliases: Tuple[str, ...] = ()
    help: str = ""
    category: str = "core"


# ── Shell / REPL ─────────────────────────────────────────────────────────────
class Shell:
    def __init__(
        self,
        root: Any | None = None,
        *,
        readonly: bool = False,
        use_color: Optional[bool] = None,
    ) -> None:
        self.root = root
        self.cur = root
        self.path: List[str] = []
        self.readonly = readonly
        self.use_color = (
            use_color
            if use_color is not None
            else (sys.stdout.isatty() or ("WT_SESSION" in os.environ))
        )
        self.bookmarks: Dict[str, List[str]] = {}
        self.__version = "0.1.0"

        self.commands: Dict[str, Command] = {}
        self._register_commands()

    # ── basic helpers ────────────────────────────────────────────────────────
    def colorize(self, text: str, color: str) -> str:
        if not self.use_color:
            return text
        return f"{ANSI.get(color, '')}{text}{ANSI['reset']}"

    def prompt(self) -> str:
        return "obj:/" + "/".join(self.path) + "> "

    def _normalize_path(self, raw: str) -> List[str]:
        if raw.startswith("/"):
            parts: List[str] = []
            segs = [s for s in raw.split("/") if s and s != "."]
        else:
            parts = list(self.path)
            segs = [s for s in raw.split("/") if s and s != "."]
        for seg in segs:
            if seg == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(seg)
        return parts

    def _node_from_parts(self, parts: List[str]) -> Any:
        node = self.root
        for seg in parts:
            key = _seg_to_key(seg)
            node = get_child(node, key)
        return node

    def _resolve_opt(self, maybe_path: List[str]) -> Any:
        if not maybe_path:
            return self.cur
        node, _ = resolve_path(self.root, self.cur, " ".join(maybe_path))
        return node

    # ── command registration ────────────────────────────────────────────────
    def _register(self, name: str, cmd: Command) -> None:
        self.commands[name] = cmd
        for alias in cmd.aliases:
            self.commands[alias] = cmd

    def _register_commands(self) -> None:
        self._register(
            "help",
            Command(
                func=self._cmd_help,
                aliases=("?",),
                help="Show help or help for a specific command",
                category="core",
            ),
        )
        self._register(
            "ls",
            Command(
                func=self._cmd_ls,
                aliases=("list",),
                help="List fields/items under the current node or a path",
                category="navigation",
            ),
        )
        self._register(
            "cd",
            Command(
                func=self._cmd_cd,
                help="Change current node (supports .. and / paths)",
                category="navigation",
            ),
        )
        self._register(
            "pwd",
            Command(
                func=self._cmd_pwd,
                help="Print current path",
                category="navigation",
            ),
        )
        self._register(
            "show",
            Command(
                func=self._cmd_show,
                help="Pretty-print a node as JSON",
                category="inspection",
            ),
        )
        self._register(
            "dump",
            Command(
                func=self._cmd_dump,
                help="Dump a node as JSON (raw)",
                category="inspection",
            ),
        )
        self._register(
            "type",
            Command(
                func=self._cmd_type,
                help="Display runtime type and container info for a node/attr",
                category="inspection",
            ),
        )
        self._register(
            "getattr",
            Command(
                func=self._cmd_getattr,
                help="Print attribute values on the current node",
                category="inspection",
            ),
        )
        self._register(
            "methods",
            Command(
                func=self._cmd_methods,
                help="List methods on the current node",
                category="inspection",
            ),
        )
        self._register(
            "call",
            Command(
                func=self._cmd_call,
                help="Call a method on the current node",
                category="mutation",
            ),
        )
        self._register(
            "get",
            Command(
                func=self._cmd_get,
                help="Get value(s) of attributes/keys or a path",
                category="inspection",
            ),
        )
        self._register(
            "set",
            Command(
                func=self._cmd_set,
                help="Set attributes on the current node (primitive values only)",
                category="mutation",
            ),
        )
        self._register(
            "del",
            Command(
                func=self._cmd_del,
                help="Delete attributes/keys/indices on the current node",
                category="mutation",
            ),
        )
        self._register(
            "mark",
            Command(
                func=self._cmd_mark,
                help="Bookmark current path under a name",
                category="navigation",
            ),
        )
        self._register(
            "marks",
            Command(
                func=self._cmd_marks,
                help="List bookmarks",
                category="navigation",
            ),
        )
        self._register(
            "goto",
            Command(
                func=self._cmd_goto,
                help="Jump to a bookmarked path",
                category="navigation",
            ),
        )
        self._register(
            "findname",
            Command(
                func=self._cmd_findname,
                help="Search for field names containing a substring",
                category="search",
            ),
        )
        self._register(
            "grep",
            Command(
                func=self._cmd_grep,
                help="Search for values whose preview contains a substring",
                category="search",
            ),
        )
        self._register(
            "ver",
            Command(
                func=self._cmd_ver,
                help="Show shell version",
                category="core",
            ),
        )

    # ── REPL loop ────────────────────────────────────────────────────────────
    def run(self) -> None:
        print(
            f"Entering ObjectShell ({self.__version}). "
            "Type 'help' for commands, 'quit' to exit."
        )
        while True:
            try:
                line = input(self.prompt())
                if _HISTORY_PATH is not None:
                    try:
                        import readline  # type: ignore[import]

                        readline.write_history_file(str(_HISTORY_PATH))
                    except Exception:
                        pass
            except (EOFError, KeyboardInterrupt):
                print()
                return

            line = line.strip()
            if not line:
                continue

            try:
                parts = shlex.split(line, posix=not sys.platform.startswith("win"))
            except ValueError as e:
                print(f"! Parse error: {e}")
                continue
            if not parts:
                continue

            cmd_name, *args = parts

            if cmd_name in ("quit", "exit"):
                return

            cmd = self.commands.get(cmd_name)
            if not cmd:
                print(f"Unknown command: {cmd_name}. Try 'help'.")
                continue

            try:
                cmd.func(args)
            except Exception as e:
                #if os.getenv("OBJSHELL_DEBUG") == "1":
                traceback.print_exc()
                #else:
                    #print(f"! Error: {e}")

    # ── commands -------------------------------------------------------------
    def _cmd_ver(self, args: List[str]) -> None:
        print(self.__version)

    def _cmd_help(self, args: List[str]) -> None:
        """
        help
        help CMD

        Show global help, or help for a specific command.
        """
        if args:
            name = args[0]
            cmd = self.commands.get(name)
            if not cmd:
                print(f"No such command: {name!r}")
                return
            if cmd.help:
                print(f"{name}: {cmd.help}")
            if cmd.aliases:
                print("aliases:", ", ".join(cmd.aliases))
            # show docstring if available
            if cmd.func.__doc__:
                print()
                print(cmd.func.__doc__.strip())
            return

        # global help: group by category
        cats: Dict[str, List[Tuple[str, Command]]] = {}
        for name, cmd in self.commands.items():
            # Skip aliases in listing (only canonical names)
            if any(name in c.aliases for c in self.commands.values()):
                continue
            cats.setdefault(cmd.category, []).append((name, cmd))

        for cat in sorted(cats):
            print(self.colorize(f"[{cat}]", "cyan"))
            rows = []
            for name, cmd in sorted(cats[cat], key=lambda kv: kv[0]):
                alias_str = ", ".join(cmd.aliases) if cmd.aliases else ""
                rows.append([name, alias_str, cmd.help])
            print_table(rows, ["cmd", "aliases", "help"])
            print()

    def _cmd_pwd(self, args: List[str]) -> None:
        """pwd: print current path"""
        print("/" + "/".join(self.path))

    def _cmd_cd(self, args: List[str]) -> None:
        """cd [PATH]  (.., /, indices, attribute names)"""
        if not args:
            self.cur = self.root
            self.path = []
            return

        raw = " ".join(args).strip()
        parts = self._normalize_path(raw)
        try:
            node = self._node_from_parts(parts)
        except Exception as e:
            print(f"! Error: {e}")
            return

        self.path = parts
        self.cur = node

    
    def _cmd_ls(self, args: List[str]) -> None:
        """
        ls [PATH] [--full]

          - Default: list fields/items under current node (or PATH).
          - For collections:
              * If all elements share the same runtime type AND there are many,
                show head + ellipsis row + tail instead of every single item.
          - Use --full to disable collapsing and show all items.
        """
        full_mode = "--full" in args
        path_args = [a for a in args if a != "--full"]

        # ---- resolve target node ------------------------------------------
        if path_args:
            raw = " ".join(path_args).strip()
            try:
                node, _ = resolve_path(self.root, self.cur, raw)
            except Exception as e:
                print(f"! Error: {e}")
                return
        else:
            node = self.cur

        # ---- collection case ----------------------------------------------
        col = as_indexable_list(node)
        if col is not None and not isinstance(node, dict):
            n = len(col)
            if n == 0:
                print("(empty collection)")
                return

            # check homogeneity of element runtime types
            type_set = {type(v) for v in col}
            homogeneous = len(type_set) == 1
            elem_type_name = next(iter(type_set)).__name__ if homogeneous else "mixed"

            # thresholds
            HEAD = 10
            TAIL = 5
            COLLAPSE_MIN = HEAD + TAIL + 5  # minimum size before collapsing

            rows: List[List[str]] = []

            if homogeneous and not full_mode and n >= COLLAPSE_MIN:
                # head indices
                head_idxs = list(range(HEAD))
                # tail indices
                tail_start = max(HEAD, n - TAIL)
                tail_idxs = list(range(tail_start, n))
                hidden = max(0, n - len(head_idxs) - len(tail_idxs))

                # head rows
                for i in head_idxs:
                    v = col[i]
                    rows.append([
                        str(i),
                        type(v).__name__,
                        short_preview(_abbrev_value(v), 60),
                    ])

                # ellipsis row
                if hidden > 0:
                    rows.append([
                        "…",
                        elem_type_name,
                        f"... {hidden} more items ...",
                    ])

                # tail rows
                for i in tail_idxs:
                    v = col[i]
                    rows.append([
                        str(i),
                        type(v).__name__,
                        short_preview(_abbrev_value(v), 60),
                    ])

            else:
                # show all items (non-homogeneous or full_mode)
                for i, v in enumerate(col):
                    rows.append([
                        str(i),
                        type(v).__name__,
                        short_preview(_abbrev_value(v), 60),
                    ])

            print_table(rows, ["index", "type", "preview"])
            return

        # ---- object/dict case: use list_fields ----------------------------
        field_list = list_fields(node)
        if not field_list:
            print("(no fields)")
            return

        rows: List[List[str]] = []
        for name, val in field_list:
            rows.append([
                str(name),
                type(val).__name__,
                short_preview(_abbrev_value(val), 60),
            ])

        print_table(rows, ["name", "type", "preview"])

    def _cmd_show(self, args: List[str]) -> None:
        """
        show [PATH]
          Pretty-print a node (or current node) as JSON-like text.
        """
        node = self._resolve_opt(args)
        print(json_dumps(node))

    def _cmd_dump(self, args: List[str]) -> None:
        """
        dump [PATH]
          Dump a node as JSON (same as show, but conceptually raw).
        """
        node = self._resolve_opt(args)
        print(json_dumps(node))

    def _cmd_type(self, args: List[str]) -> None:
        """
        type
        type PATH|ATTR

        Describe the runtime type and container info for the current node
        or a specific child path/attribute.
        """
        target = self.cur
        field_name = None

        if args:
            if len(args) == 1 and hasattr(self.cur, args[0]):
                field_name = args[0]
                target = getattr(self.cur, field_name)
            else:
                try:
                    target, stack = resolve_path(self.root, self.cur, args[0])
                    field_name = stack[-1] if stack else None
                except Exception as e:
                    print(f"! bad path: {e}")
                    return

        rows: List[List[str]] = []
        if target is None:
            rows.append(["runtime", "type", "NoneType"])
        else:
            rtype = type(target)
            rows.append(["runtime", "type", f"{rtype.__module__}.{rtype.__name__}"])
            if isinstance(target, dict):
                rows.append(["runtime", "container", f"dict (len={len(target)})"])
            elif isinstance(target, (list, tuple, set)):
                rows.append(["runtime", "container", f"{rtype.__name__} (len={len(target)})"])
            col = as_indexable_list(target)
            if col is not None and not isinstance(target, (list, tuple, set, dict)):
                rows.append(["runtime", "container", f"{type(target).__name__} (len={len(col)})"])

        if field_name is not None:
            rows.append(["field", "name", field_name])

        print_table(rows, ["scope", "key", "value"])

    def _cmd_getattr(self, args: List[str]) -> None:
        """
        getattr NAME [NAME ...]
          Print attribute values on the current node.
        """
        if not args:
            print("usage: getattr NAME [NAME ...]")
            return
        clsname = type(self.cur).__name__
        for name in args:
            if not hasattr(self.cur, name):
                print(f"{clsname}.{name} = <missing>")
                continue
            try:
                value = getattr(self.cur, name)
            except Exception as e:
                print(f"{clsname}.{name} raised {e.__class__.__name__}: {e}")
                continue
            print(f"{clsname}.{name} = {short_preview(value, 200)}")

    def _cmd_methods(self, args: List[str]) -> None:
        """
        methods [--private] [--match SUBSTR]
          List methods on the current node.
        """
        include_private = "--private" in args
        match = None
        if "--match" in args:
            idx = args.index("--match")
            if idx + 1 >= len(args):
                print("usage: methods [--private] [--match SUBSTR]")
                return
            match = args[idx + 1].lower()

        obj = self.cur
        rows: List[List[str]] = []
        seen: set[str] = set()

        for cls in type(obj).mro():
            for name, member in cls.__dict__.items():
                if not include_private and _is_private(name):
                    continue
                if name in seen:
                    continue

                is_callish = callable(getattr(obj, name, None))
                if not is_callish:
                    continue
                if match and match not in name.lower():
                    continue

                seen.add(name)
                try:
                    import inspect

                    bound = getattr(obj, name, member)
                    try:
                        sig = inspect.signature(bound)
                        params = list(sig.parameters.values())
                        if params and params[0].name == "self":
                            params = params[1:]
                        sig_str = "(" + ", ".join(str(p) for p in params) + ")"
                    except Exception:
                        sig_str = "()"
                except Exception:
                    sig_str = "()"

                rows.append([name, sig_str, cls.__name__])

        if not rows:
            print("(no methods)")
            return

        print_table(sorted(rows, key=lambda r: (r[2] != type(obj).__name__, r[0])), ["name", "signature", "defined in"])

    def _cmd_call(self, args: List[str]) -> None:
        """
        call NAME [args...] [kw=val ...]
          Dynamically call a method on the current node.
        """
        if self.readonly:
            print("Read-only mode: 'call' is disabled.")
            return

        if not args:
            print("usage: call NAME [args...] [kw=val ...]")
            return

        name, *rest = args
        target = getattr(self.cur, name, None)
        if target is None or not callable(target):
            print(f"! method '{name}' not found or not callable on {type(self.cur).__name__}")
            return

        try:
            pos, kw = _split_args_kwargs(rest)
        except ValueError as e:
            print(f"! {e}")
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

    def _cmd_get(self, args: List[str]) -> None:
        """
        get NAME [NAME2 ...]
        get PATH
        get --all
        get --all --private

        Enhanced get:

        - get NAME [NAME2 ...]
                Show attributes or dict keys on the current node.

        - get PATH
                Resolve PATH just like cd/ls/show and print the resolved value.

        - get --all
                List all public attributes/keys on the current node.

        - get --all --private
                Same as --all, but include private attributes (those starting with '_').
        """
        if not args:
            print("usage: get NAME [NAME2 ...] | get PATH | get --all [--private]")
            return

        # ---- switches ----
        list_all = "--all" in args
        include_private = "--private" in args
        args = [a for a in args if a not in ("--all", "--private")]

        # ---- ALL mode: list all fields/keys/properties ----
        if list_all:
            node = self.cur
            cls = type(node).__name__

            rows = []

            # dict-like
            if isinstance(node, dict):
                for k, v in node.items():
                    rows.append([str(k), short_preview(v, 80)])
                print_table(rows, ["key", "preview"])
                return

            # object: collect attributes
            # We ONLY consider instance attributes + @property descriptors
            fields = []

            # instance-level attributes
            if hasattr(node, "__dict__"):
                for k, v in node.__dict__.items():
                    if not include_private and k.startswith("_"):
                        continue
                    fields.append((k, v))

            # property descriptors from the class
            for name in dir(node):
                if not include_private and name.startswith("_"):
                    continue
                if name in [k for k, _ in fields]:
                    continue  # already in instance dict
                try:
                    attr = getattr(type(node), name, None)
                    if isinstance(attr, property):
                        try:
                            val = getattr(node, name)
                        except Exception as e:
                            val = f"<error: {e}>"
                        fields.append((name, val))
                except Exception:
                    continue

            for k, v in fields:
                rows.append([k, short_preview(v, 80)])

            if not rows:
                print(f"(no attributes visible on {cls})")
            else:
                print_table(rows, ["attribute", "preview"])
            return

        # ---- PATH mode (single arg that looks like a path) ----
        if (
            len(args) == 1
            and (args[0].startswith("/") or "/" in args[0] or args[0] in (".", ".."))
        ):
            raw = args[0]
            try:
                node, _ = resolve_path(self.root, self.cur, raw)
            except Exception as e:
                print(f"! bad path: {e}")
                return

            if is_primitive(node):
                print(repr(node))
            else:
                print(json_dumps(node))
            return

        # ---- NAME / NAME1 NAME2 mode ----
        node = self.cur
        clsname = type(node).__name__
        is_mapping = isinstance(node, dict)

        for name in args:

            # dict key lookup
            if is_mapping and name in node:
                v = node[name]
                print(f"[{name!r}] = {short_preview(v, 200)}")
                continue

            # attribute lookup
            if hasattr(node, name):
                try:
                    v = getattr(node, name)
                except Exception as e:
                    print(f"{clsname}.{name} raised {e.__class__.__name__}: {e}")
                    continue
                print(f"{clsname}.{name} = {short_preview(v, 200)}")
                continue

            print(f"! {clsname}.{name} (or key {name!r}) not found")

    
    def _cmd_set(self, args: List[str]) -> None:
        """
        set NAME VALUE
        set NAME=VALUE [NAME2=VALUE2 ...]

        Set attributes on the current node.

        - Only primitive values are allowed (str/int/float/bool/None)
        - Private attributes (starting with '_') are refused
        """
        if self.readonly:
            print("Read-only mode: 'set' is disabled.")
            return

        if not args:
            print("usage: set NAME VALUE  |  set NAME=VALUE [NAME2=VALUE2 ...]")
            return

        obj = self.cur
        cls = type(obj)
        assignments: Dict[str, Any] = {}

        # NAME=VALUE form
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
            # NAME VALUE form
            if len(args) < 2:
                print("usage: set NAME VALUE  |  set NAME=VALUE [NAME2=VALUE2 ...]")
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
                setattr(obj, name, value)
            except Exception as e:
                print(f"! error setting {cls.__name__}.{name}: {e}")
            else:
                print(f"{cls.__name__}.{name} = {value!r}")

    def _cmd_del(self, args: List[str]) -> None:
        """
        del NAME [NAME2 ...]
          Delete attributes/fields on the current node:

            - dict:  NAME deletes key
            - list / sequence: NAME must be int index
            - object: NAME treated as attribute name
        """
        if self.readonly:
            print("Read-only mode: 'del' is disabled.")
            return

        if not args:
            print("usage: del NAME [NAME2 ...]")
            return

        obj = self.cur
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

            # dict key deletion
            if is_mapping and name in obj:
                try:
                    del obj[name]  # type: ignore[index]
                except Exception as e:
                    print(f"! error deleting key {name!r} from dict: {e}")
                else:
                    print(f"dict[{name!r}] deleted")
                continue

            # index deletion
            if _is_indexable_sequence(obj):
                try:
                    idx = int(name)
                except ValueError:
                    idx = None
                if idx is not None:
                    try:
                        length = len(obj)  # type: ignore[arg-type]
                        if not (-length <= idx < length):
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

            # attribute deletion
            if _is_private(name):
                print(f"! refusing to delete private attribute {name!r}")
                continue

            if not hasattr(obj, name):
                print(f"! {cls.__name__}.{name} not found; nothing to delete.")
                continue

            try:
                delattr(obj, name)
            except Exception as e:
                print(f"! error deleting attribute {cls.__name__}.{name}: {e}")
            else:
                print(f"{cls.__name__}.{name} deleted")

    # ── bookmarks ------------------------------------------------------------
    def _cmd_mark(self, args: List[str]) -> None:
        """
        mark NAME
          Bookmark the current path under NAME.
        """
        if not args:
            print("usage: mark NAME")
            return
        name = args[0]
        self.bookmarks[name] = list(self.path)
        print(f"Marked {name!r} -> /{'/'.join(self.path)}")

    def _cmd_marks(self, args: List[str]) -> None:
        """
        marks
          List bookmarks.
        """
        if not self.bookmarks:
            print("(no bookmarks)")
            return
        rows = []
        for name, path in sorted(self.bookmarks.items()):
            rows.append([name, "/" + "/".join(path)])
        print_table(rows, ["name", "path"])

    def _cmd_goto(self, args: List[str]) -> None:
        """
        goto NAME
          Jump to a bookmarked path.
        """
        if not args:
            print("usage: goto NAME")
            return
        name = args[0]
        if name not in self.bookmarks:
            print(f"! no such bookmark: {name!r}")
            return
        parts = self.bookmarks[name]
        try:
            node = self._node_from_parts(parts)
        except Exception as e:
            print(f"! Error: {e}")
            return
        self.path = list(parts)
        self.cur = node
        print(f"Now at /{'/'.join(self.path)}")

    # ── search ---------------------------------------------------------------
    def _cmd_findname(self, args: List[str]) -> None:
        """
        findname SUBSTR
          Search for field names containing SUBSTR beneath the current node.
        """
        if not args:
            print("usage: findname SUBSTR")
            return
        needle = args[0].lower()
        hits: List[Tuple[str, Any]] = []

        def walk(node: Any, path_parts: List[str], depth: int = 0, max_depth: int = 6) -> None:
            if depth > max_depth:
                return
            for name, val in list_fields(node):
                if needle in name.lower():
                    hits.append(("/" + "/".join(path_parts + [name]), val))
                if not is_primitive(val):
                    walk(val, path_parts + [name], depth + 1, max_depth)

        walk(self.cur, self.path)
        if not hits:
            print("(no matches)")
            return
        rows = [[p, type(v).__name__, short_preview(v, 60)] for p, v in hits]
        print_table(rows, ["path", "type", "preview"])

    def _cmd_grep(self, args: List[str]) -> None:
        """
        grep SUBSTR
          Search for values whose short preview contains SUBSTR beneath the current node.
        """
        if not args:
            print("usage: grep SUBSTR")
            return
        needle = args[0].lower()
        hits: List[Tuple[str, Any]] = []

        def walk(node: Any, path_parts: List[str], depth: int = 0, max_depth: int = 6) -> None:
            if depth > max_depth:
                return
            for name, val in list_fields(node):
                prev = short_preview(val, 200)
                if needle in prev.lower():
                    hits.append(("/" + "/".join(path_parts + [name]), val))
                if not is_primitive(val):
                    walk(val, path_parts + [name], depth + 1, max_depth)

        walk(self.cur, self.path)
        if not hits:
            print("(no matches)")
            return
        rows = [[p, type(v).__name__, short_preview(v, 60)] for p, v in hits]
        print_table(rows, ["path", "type", "preview"])


# ── Entrypoint ───────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="Generic ObjectShell inspector")
    parser.add_argument(
        "--json",
        help="Load root object from JSON file",
    )
    parser.add_argument(
        "--eval",
        dest="expr",
        help="Python expression to evaluate for root object (DANGEROUS, use only on trusted code)",
    )
    parser.add_argument(
        "--readonly",
        action="store_true",
        help="Run in read-only mode (disable set/del/call)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    parser.add_argument(
        "--cmd",
        help="Single command to run non-interactively (then exit)",
    )

    args = parser.parse_args()

    root: Any = None
    if args.json:
        path = Path(args.json).expanduser()
        if not path.is_file():
            print(f"! JSON file not found: {path}")
            return 1
        with path.open("r", encoding="utf-8") as f:
            root = json.load(f)

    if args.expr:
        # This is intentionally dangerous and intended for local expert use only.
        ns: Dict[str, Any] = {}
        ns.update(globals())
        try:
            root = eval(args.expr, ns, {})
        except Exception as e:
            print(f"! eval error: {e}")
            return 1

    sh = Shell(root=root, readonly=args.readonly, use_color=not args.no_color)

    if args.cmd:
        # Non-interactive single-command mode
        line = args.cmd.strip()
        try:
            parts = shlex.split(line, posix=not sys.platform.startswith("win"))
        except ValueError as e:
            print(f"! Parse error: {e}")
            return 1
        if not parts:
            return 0
        cmd_name, *cargs = parts
        cmd = sh.commands.get(cmd_name)
        if not cmd:
            print(f"Unknown command: {cmd_name}. Try 'help'.")
            return 1
        try:
            cmd.func(cargs)
        except Exception as e:
            if os.getenv("OBJSHELL_DEBUG") == "1":
                traceback.print_exc()
            else:
                print(f"! Error: {e}")
            return 1
        return 0

    sh.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
