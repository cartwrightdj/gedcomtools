#!/usr/bin/env python3
from __future__ import annotations

"""
======================================================================
 Project: Gedcom-X
 File:    gxcli.py
 Author:  David J. Cartwright
 Purpose: cli to inspect GedcomX objects

 Created: 2026-02-01
 Updated:
    - 2025-10-25 smart_getattr(obj, name): returns (value, kind) where kind ∈ {'instance','property','class_attr','missing'}
    - 2025-10-25 Shell._cmd_getprop: robust property introspection using inspect.getattr_static
    - 2025-10-25 Shell._cmd_props: list both instance and class-level properties/attrs with current values
    - 2025-10-25 Shell._cmd_getattr: REPL helper to inspect any attribute with kind
    - 2025-11-12 ls: show item IDs in preview and allow cd by id in list-like containers
    - 2026-02-01 added loggingkit, and _cmd_log
    - 2026-02-23 jsonl to cmd_write, if current node is an iterable, it serializes is to jsonl file
======================================================================
"""

import argparse
import ast
import dataclasses
import inspect  # used for descriptor-safe lookups
import json
import logging
import os
import re
import shlex
import shutil
import sys
import traceback
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, get_args, get_origin

import orjson

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from gedcomtools.glog import setup_logging, get_logger, LoggerSpec

# Logging is initialized in main() to avoid side effects on import.
_LOG_MGR = None


def init_logging(app_name: str = "gedcomtools"):
    global _LOG_MGR
    if _LOG_MGR is None:
        _LOG_MGR = setup_logging(app_name=app_name)
    return _LOG_MGR

from gedcomtools.gedcomx import GedcomConverter, GedcomX
from gedcomtools.gedcom5.parser import Gedcom5x
from gedcomtools.gedcomx.schemas import SCHEMA, type_repr
from gedcomtools.gedcomx.serialization import ResolveStats, Serialization
from gedcomtools.gedcomx.cli import objects_to_schema_table, write_jsonl
from gedcomtools.gedcomx.arango import make_arango_graph_files


SHELL_VERSION = '0.5.21'

def _level_from_str(s: str) -> int:
    s = (s or "").strip().upper()
    mapping = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    if s not in mapping:
        raise ValueError(f"Unknown level '{s}'. Use: DEBUG, INFO, WARNING, ERROR, CRITICAL, NOTSET")
    return mapping[s]


def _set_all_handler_levels(logger: logging.Logger, level: int) -> None:
    for h in logger.handlers:
        h.setLevel(level)

# ── Colors ───────────────────────────────────────────────────────────────────
# On Windows, raw ANSI escape codes require either colorama or Windows 10+
# Virtual Terminal Processing. When colorama is available it wraps stdout so
# that all escape sequences work on every Windows version.  When it is not
# available and we are on Windows, we disable colour entirely so the terminal
# is not littered with literal escape characters.
try:
    from colorama import Fore, Style, init as _colorama_init

    _colorama_init()
    _RED, _RESET = Fore.RED, Style.RESET_ALL
    _ANSI_SUPPORTED = True
except Exception:
    _ANSI_SUPPORTED = not sys.platform.startswith("win")
    if _ANSI_SUPPORTED:
        _RED, _RESET = "\033[31m", "\033[0m"
    else:
        _RED, _RESET = "", ""

ANSI: dict[str, str]
if _ANSI_SUPPORTED:
    ANSI = {
        "red": "\x1b[31m",
        "green": "\x1b[32m",
        "yellow": "\x1b[33m",
        "cyan": "\x1b[36m",
        "dim": "\x1b[2m",
        "reset": "\x1b[0m",
    }
else:
    ANSI = {k: "" for k in ("red", "green", "yellow", "cyan", "dim", "reset")}

# ── Status flags ─────────────────────────────────────────────────────────────
NO_DATA = 0xB0
JSON_LOAD = 0xB1
M_JSON_LD = 0xB2
XML_LOAD = 0xB4
CNVRT_GC5 = 0xB16

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_DEQUAL_RE = re.compile(r"(?<!\w)(?:[A-Za-z_]\w*\.)+([A-Za-z_]\w*)")


def _dequalify_type_str(s: str) -> str:
    return _DEQUAL_RE.sub(r"\1", s)


def _sans_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _pad_ansi(s: str, width: int) -> str:
    visible = len(_sans_ansi(s))
    pad = max(0, width - visible)
    return s + " " * pad


def _clip(s: str, width: int) -> str:
    if width <= 1:
        return "" if width <= 0 else s[:1]
    return s if len(s) <= width else s[: width - 1] + "…"


def _human_type_name(val: Any) -> str:
    if hasattr(val, "item_type") and type(val).__name__ == "TypeCollection":
        it = getattr(val, "item_type", None)
        if it is not None:
            it_name = getattr(it, "__name__", str(it)).split(".")[-1]
            return f"TypeCollection[{it_name}]"
        return "TypeCollection"

    t = type(val)
    name = getattr(t, "__name__", str(t))
    if name == "NoneType":
        return "None"
    if name == "list":
        return "List"
    if name == "tuple":
        return "Tuple"
    if name == "set":
        return "Set"
    if name == "dict":
        return "Dict"
    return name


def _red(s: str) -> str:
    return f"{_RED}{s}{_RESET}"


# ── JSON helpers ─────────────────────────────────────────────────────────────
def _json_loads(b: bytes | str) -> Any:
    try:
        return orjson.loads(b if isinstance(b, (bytes, bytearray)) else b.encode("utf-8"))
    except Exception:
        if isinstance(b, (bytes, bytearray)):
            b = b.decode("utf-8")
        return json.loads(b)

def _json_dumps(obj: Any) -> str:
    plain = to_plain(obj, max_depth=64)
    try:
        return orjson.dumps(plain, option=orjson.OPT_INDENT_2).decode("utf-8")
    except Exception:
        return json.dumps(plain, ensure_ascii=False, indent=2)

def _is_private(name: str) -> bool:
    return name.startswith("_")

def _coerce_token(tok: str):
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

def _split_args_kwargs(tokens: list[str]):
    args: list[object] = []
    kwargs: dict[str, object] = {}
    for tok in tokens:
        if "=" in tok:
            k, v = tok.split("=", 1)
            k = k.strip()
            if not k or _is_private(k):
                raise ValueError(f"invalid keyword '{k}'")
            kwargs[k] = _coerce_token(v)
        else:
            args.append(_coerce_token(tok))
    return args, kwargs

def _declaring_class(obj, attr_name: str) -> str:
    for cls in type(obj).mro():
        if attr_name in cls.__dict__:
            return cls.__name__
    return type(obj).__name__

def _format_signature(bound_member) -> str:
    try:
        sig = inspect.signature(bound_member)
    except (TypeError, ValueError):
        return "()"
    params = list(sig.parameters.values())
    if params and params[0].name == "self":
        params = params[1:]
    sig2 = "(" + ", ".join(str(p) for p in params) + ")"
    if sig.return_annotation is not inspect.Signature.empty:
        ann = sig.return_annotation
        try:
            ann_str = getattr(ann, "__name__", None) or str(ann)
        except Exception:
            ann_str = str(ann)
        return f"{sig2} -> {ann_str}"
    return sig2

# ── Plainification / introspection ───────────────────────────────────────────
_PRIMITIVES = (str, int, float, bool, type(None))


def is_primitive(x: Any) -> bool:
    return isinstance(x, _PRIMITIVES)

def _maybe_as_dict(obj: Any) -> Any:
    if hasattr(obj, "__class__") and hasattr(type(obj), "__module__") and "gedcomtools" in getattr(type(obj), "__module__", ""):
        try:
            return Serialization.serialize(obj)
        except Exception:
            pass
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return obj.model_dump()
        except Exception:
            pass
    if is_dataclass(obj) and not isinstance(obj, type):
        try:
            return asdict(obj)
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        d = {k: v for k, v in vars(obj).items() if not k.startswith("_")}
        if d:
            return d
    return obj

def to_plain(obj: Any, *, max_depth: int = 6, _seen: set[int] | None = None) -> Any:
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

def short_preview(val: Any, max_len: int = 80) -> str:
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
        return f"<{str(val)}>"
    except Exception:
        return f"<{type(val).__name__}>"

def list_fields(obj: Any) -> list[tuple[str, Any]]:
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

def type_of(obj: Any) -> str:
    return getattr(obj, "__name__", None) or obj.__class__.__name__

# ── Collection detection ─────────────────────────────────────────────────────
def as_indexable_list(obj: Any) -> list[Any] | None:
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
            return list(items) if isinstance(items, Iterable) else None
        except Exception:
            pass
    if hasattr(obj, "__iter__"):
        try:
            return list(obj)
        except Exception:
            pass
    return None

# ── Path navigation helpers ──────────────────────────────────────────────────
def _seg_to_key(seg: str):
    if seg.isdigit() or (seg.startswith("-") and seg[1:].isdigit()):
        return int(seg)
    return seg

def _get_item_id(obj: Any) -> Any | None:
    candidates = ("id", "xref_id", "identifier")
    for attr in candidates:
        try:
            if isinstance(obj, dict) and attr in obj:
                return obj[attr]
            if hasattr(obj, "__dict__") and attr in obj.__dict__:
                return obj.__dict__[attr]
        except Exception:
            continue
    return None

def get_child(parent: Any, key: int | str) -> Any:
    if isinstance(parent, dict):
        return parent[key]

    if isinstance(parent, (list, tuple)):
        if isinstance(key, int):
            return parent[key]
        if isinstance(key, str):
            for item in parent:
                id_val = _get_item_id(item)
                if id_val is not None and str(id_val) == key:
                    return item
            raise KeyError(f"No child with id {key!r} in {type(parent).__name__}")
        raise KeyError("List index must be int or an ID string")

    col = as_indexable_list(parent)
    if col is not None:
        if isinstance(key, int):
            return col[key]
        if isinstance(key, str):
            for item in col:
                id_val = _get_item_id(item)
                if id_val is not None and str(id_val) == key:
                    return item
            raise KeyError(f"No child with id {key!r} in {type(parent).__name__}")
        raise KeyError("Collection index must be int or an ID string")

    if not isinstance(key, int) and hasattr(parent, key):
        return getattr(parent, key)

    if hasattr(parent, "__getitem__"):
        return parent[key]  # type: ignore[index]

    raise KeyError(f"Cannot access key/attr {key!r} on {type(parent).__name__}")

def resolve_path(root: Any, cur: Any, path: str) -> tuple[Any, list[str]]:
    if not path or path == ".":
        return cur, []
    node = root if path.startswith("/") else cur
    parts = [p for p in path.strip("/").split("/") if p]
    stack: list[str] = []
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

# ── Schema helpers ───────────────────────────────────────────────────────────
def _typename(t: Any) -> str:
    from typing import Any as _Any

    if isinstance(t, str):
        return t
    origin = get_origin(t)
    if origin is None:
        return getattr(t, "__name__", str(t)).replace("typing.", "")
    args = get_args(t)
    name = getattr(origin, "__name__", str(origin)).replace("typing.", "")
    if name in ("list", "List"):
        return f"List[{_typename(args[0])}]" if args else "List[Any]"
    if name in ("set", "Set"):
        return f"Set[{_typename(args[0])}]" if args else "Set[Any]"
    if name in ("tuple", "Tuple"):
        return "Tuple[" + ", ".join(_typename(a) for a in args) + "]" if args else "Tuple"
    if name in ("dict", "Dict"):
        k, v = (args + (_Any, _Any))[:2]
        return f"Dict[{_typename(k)}, {_typename(v)}]"
    inner = ", ".join(_typename(a) for a in args)
    return f"{name}[{inner}]" if inner else name

def _print_table(rows: Iterable[Iterable[str]], headers: list[str]) -> None:
    rows = [[str(c) for c in r] for r in rows]
    widths = [len(h) for h in headers]
    for r in rows:
        for i, col in enumerate(r):
            widths[i] = max(widths[i], len(_sans_ansi(col)))

    def fmt(row):
        return " | ".join(_pad_ansi(_clip(c, widths[i]), widths[i]) for i, c in enumerate(row))

    print(fmt(headers))
    print(" | ".join("-" * w for w in widths))
    for r in rows:
        print(fmt(r))

def _schema_fields_for_object(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    cls_name = obj.__class__.__name__
    return SCHEMA.get_class_fields(cls_name) or {}

def _parse_elem_from_type_str(container_str: str) -> str | None:
    s = container_str.strip()
    if "[" not in s or not s.endswith("]"):
        return None
    head, inner = s.split("[", 1)
    inner = inner[:-1]
    head = head.strip().lower()
    if head in ("list", "set", "sequence", "collection", "tuple"):
        return inner.split(",", 1)[0].strip() if inner else None
    if head == "dict":
        parts = [p.strip() for p in inner.split(",", 1)]
        return parts[1] if len(parts) == 2 else None
    return None

def _expected_element_type_from_parent(parent: Any, field_name: str) -> Any | None:
    ann = _schema_fields_for_object(parent).get(field_name)
    if ann is None:
        return None

    origin = get_origin(ann)
    args = get_args(ann)
    if origin in (list, set, tuple):
        return args[0] if args else None
    if origin is dict and len(args) == 2:
        return args[1]

    cont_str = type_repr(ann)
    inner = _parse_elem_from_type_str(cont_str)
    return inner or ann

def _names_match(expected: Any | None, value: Any) -> bool:
    from typing import Any as TypingAny, get_args as _ga, get_origin as _go

    if expected is None or expected is TypingAny:
        return True

    def _head_inner_from_expected(exp: Any) -> tuple[str, str | None]:
        if isinstance(exp, str):
            head = exp.split("[", 1)[0].split(".")[-1]
            inner = None
            if "[" in exp and exp.endswith("]"):
                inner = exp[exp.find("[") + 1 : -1].split(",", 1)[0].split(".")[-1].strip()
            return head, inner
        origin = _go(exp)
        if origin is not None:
            head = getattr(origin, "__name__", str(origin)).split(".")[-1]
            args = _ga(exp)
            inner = None
            if args:
                a0 = args[0]
                inner = (getattr(a0, "__name__", str(a0))).split(".")[-1]
            return head, inner
        if isinstance(exp, type):
            return exp.__name__, None
        return str(exp).split(".")[-1], None

    def _head_inner_from_value(val: Any) -> tuple[str, str | None]:
        head = type(val).__name__
        inner = None
        if hasattr(val, "item_type") and head == "TypeCollection":
            it = getattr(val, "item_type", None)
            if it is not None:
                inner = getattr(it, "__name__", str(it)).split(".")[-1]
        return head, inner

    exp_head, exp_inner = _head_inner_from_expected(expected)
    act_head, act_inner = _head_inner_from_value(value)

    alias = {
        "list": "list",
        "set": "set",
        "tuple": "tuple",
        "dict": "dict",
        "typecollection": "typecollection",
    }
    if alias.get(exp_head.lower(), exp_head.lower()) != alias.get(act_head.lower(), act_head.lower()):
        return False

    if exp_inner and act_inner:
        return exp_inner.lower() == act_inner.lower()

    return True

# ── Smart getattr ────────────────────────────────────────────────────────────
def smart_getattr(obj: Any, name: str, default=None) -> tuple[Any, str]:
    cls = type(obj)

    if hasattr(obj, "__dict__") and name in obj.__dict__:
        return obj.__dict__[name], "instance"

    attr = inspect.getattr_static(cls, name, None)
    if isinstance(attr, property):
        try:
            return getattr(obj, name), "property"
        except Exception as e:
            return f"<error: {e}>", "property"

    if attr is not None and not callable(attr):
        return attr, "class_attr"

    return default, "missing"

# ── Shell / REPL ─────────────────────────────────────────────────────────────
class Shell:
    def __init__(self, root: Any | None = None):
        self.gedcomx: Any | None = None
        self.root = root
        self.cur = root
        self.path: list[str] = []
        self.use_color = sys.stdout.isatty() or ("WT_SESSION" in os.environ)
        self.status = NO_DATA
        self.version = SHELL_VERSION

        self.commands = {
            "agentstbl": self._cmd_agenttbl,
            "call": self._cmd_call,
            "cd": self._cmd_cd,
            "del": self._cmd_del,
            "extend": self._cmd_extend,
            "extras": self._cmd_extras,
            "getattr": self._cmd_getattr,
            "getprop": self._cmd_getprop,
            "help": self._cmd_help,
            "?": self._cmd_help,
            "ld": self._cmd_load,
            "load": self._cmd_load,
            "log":self._cmd_log,
            "ls": self._cmd_ls,
            "list": self._cmd_ls,
            "methods": self._cmd_methods,
            "props": self._cmd_props,
            "pwd": self._cmd_pwd,
            "resolve": self._cmd_resolve,
            "schema": self._cmd_schema,
            "set": self._cmd_set,
            "dump": self._cmd_dump,
            "show": self._cmd_show,
            "type": self._cmd_type,
            "ver": self._cmd_ver,
            "write": self._cmd_write,
        }

    def prompt(self) -> str:
        return "gx:/" + "/".join(self.path) + "> "

    def run(self) -> None:
        print(f"Entering GEDCOM-X browser ({self.version}) Type 'help' for commands, 'quit' to exit.")
        while True:
            try:
                line = input(self.prompt()).strip()
            except (EOFError, KeyboardInterrupt):
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
                continue

            try:
                handler(args)
            except Exception as e:
                tb = e.__traceback__
                last = traceback.extract_tb(tb)[-1]

                print(f"! cmd error ({last.filename}:{last.lineno}): {e}")

    # ---- commands -----------------------------------------------------------
    def _cmd_ver(self, args: list[str]) -> None:
        print(self.version)

    def _cmd_del(self, args: list[str]) -> None:
        """
        del NAME [NAME2 ...]
        Delete attributes/fields on the current node.
        """
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

    def _cmd_help(self, args: list[str]) -> None:
        """
        help [COMMAND]
        Show general help or help for a specific command.
        """
        if args:
            name = args[0]
            handler = self.commands.get(name)
            if handler and handler.__doc__:
                print(handler.__doc__.strip())
                return
            print(f"No help for command {name!r}")
            return

        print(
            "Commands:\n"
            "  load PATH                load .ged (5x) or .json (GEDCOM-X)\n"
            "  extend PATH              load and extend current root\n"
            "  ls [PATH] [--full]       list fields/items under node (schema-aware)\n"
            "  cd PATH                  change node (.., /, indices, id strings)\n"
            "  pwd                      print current path\n"
            "  show [PATH|toplevel]     pretty-print node or list top-level collection items\n"
            "  dump [PATH]              same as show but always JSON\n"
            "  schema ...               inspect schema/classes/extras (see: schema help)\n"
            "  extras [opts]            list extras across all classes\n"
            "  type [opts] [PATH|ATTR]  runtime & schema type info\n"
            "  resolve                  resolve Resource/URI refs using model resolver\n"
            "  write gx PATH            write current root as GEDCOM-X JSON\n"
            "  getprop NAME [...]       print value of @property(ies) on current node\n"
            "  props [--instance|--class] [--private]\n"
            "                           list instance attrs + class properties/attrs\n"
            "  getattr NAME [...]       smart getattr → value + kind\n"
            "  methods [--private] [--own] [--match SUBSTR]\n"
            "                           list callable methods on current node\n"
            "  call NAME [args...] [kw=val ...]\n"
            "                           call a method on current node with typed args\n"
            "  set NAME VALUE | NAME=VALUE [...]\n"
            "  set --n NAME [NAME2 ...] create and assign/append new instance(s) based on schema\n"
            "  del NAME [NAME2 ...]     delete attributes/keys/indices on current node\n"
            "  ver                      print version\n"
            "  quit | exit              leave\n"
        )

    def _cmd_agenttbl(self, args: list[str]) -> None:
        """
        agentstbl
        Show a schema table for agents (paged).
        """
        if self.gedcomx is None or not hasattr(self.gedcomx, "agents"):
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
                    input("\n[Press Enter to continue…]\n")

        page_table(objects_to_schema_table(self.gedcomx.agents))

    def _cmd_extend(self, args: list[str]) -> None:
        """
        extend PATH
        Load a .ged or .json and extend current root (must support .extend()).
        """
        if len(args) != 1:
            print("usage: extend PATH")
            return
        path = args[0].strip().strip('"')

        if self.root is None or not hasattr(self.root, "extend"):
            print("Current root is None or does not support .extend()")
            return

        if path.lower().endswith(".ged"):
            print("Loading GEDCOM (size may affect time)…")
            gx = self._load_from_ged(path)
            self.root.extend(gx)
            print("Loaded GEDCOM 5.x and converted to GedcomX.")
            return

        if path.lower().endswith(".json"):
            print("Loading Gedcom-X from JSON (size may affect time)…")
            gx = self._load_from_json(path)
            self.root.extend(gx)
            print("Loaded GEDCOM-X JSON.")
            return

        print(f"Unsupported file type. Use .ged or .json: {path}")

    def _cmd_load(self, args: list[str]) -> None:
        """
        load PATH
        Load a .ged (Gedcom 5.x) or .json (GedcomX) and set as root.
        """
        if len(args) != 1:
            print("usage: load PATH")
            return
        path = args[0].strip().strip('"')

        if path.lower().endswith(".ged"):
            print("Loading GEDCOM (size may affect time)…")
            gx = self._load_from_ged(path)
            self._set_root(gx)
            print("Loaded GEDCOM 5.x and converted to GedcomX.")
            return

        if path.lower().endswith(".json"):
            print("Loading Gedcom-X from JSON (size may affect time)…")
            gx = self._load_from_json(path)
            self._set_root(gx)
            print("Loaded GEDCOM-X JSON.")
            return

        print(f"Unsupported file type. Use .ged or .json: {path}")

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
            logger = get_logger(channel)  # uses active manager config
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

            # Configure this channel if not already configured
            # filename="" => console-only (matches your default behavior)
            spec = LoggerSpec(name=channel, filename="", level=level or logging.INFO, also_to_console=True)
            logger = mgr.get_sublogger(spec)

            # If user supplied level, ensure logger's level is set accordingly
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

            # Make sure the logger exists/configured (or at least in registry)
            if channel == "common":
                logger = mgr.get_common()
            else:
                # If not configured, configure console-only so changes actually do something
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

            # Update handler levels for every configured logger (common + sublogs)
            _set_all_handler_levels(mgr.get_common(), level)
            for _, lg in mgr._sub_loggers.items():  # internal but fine for CLI
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

    def _load_from_ged(self, path: str) -> Any:
        p = Gedcom5x()
        p.parse_file(path, True)
        conv = GedcomConverter()
        gx: GedcomX = conv.Gedcom5x_GedcomX(p)
        self.gedcomx = gx
        return gx

    def _load_from_json(self, path: str) -> Any:
        with open(path, "rb") as f:
            data = _json_loads(f.read())

        try:
            gx = Serialization.deserialize(data=data, class_type=GedcomX)  # type: ignore[attr-defined]
            self.gedcomx = gx
            return gx
        except Exception:
            pass

        try:
            gx = GedcomX(**data)  # type: ignore[arg-type]
            self.gedcomx = gx
            return gx
        except Exception:
            return data

    def _set_root(self, root: Any) -> None:
        self.root = root
        self.cur = root
        self.path.clear()

    def _resolve_opt(self, maybe_path: list[str]) -> Any:
        if not maybe_path:
            return self.cur
        node, _ = resolve_path(self.root, self.cur, " ".join(maybe_path))
        return node

    def _normalize_path(self, raw: str) -> list[str]:
        if raw.startswith("/"):
            parts: list[str] = []
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

    def _node_from_parts(self, parts: list[str]) -> Any:
        node = self.root
        for seg in parts:
            key = _seg_to_key(seg)
            node = get_child(node, key)
        return node

    def _cmd_cd(self, args: list[str]) -> None:
        """
        cd [PATH]
        Change current node. No args resets to root.
        """
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

    def _cmd_pwd(self, args: list[str]) -> None:
        """
        pwd
        Print the current path.
        """
        _ = args
        print("/" + "/".join(self.path))

    def _cmd_dump(self, args: list[str]) -> None:
        """
        dump [PATH]
        Print node as JSON (always).
        """
        node = self._resolve_opt(args)
        print(_json_dumps(node))

    def _cmd_show(self, args: list[str]) -> None:
        """
        show [PATH]
        show persons
          - With a normal PATH (or no args): pretty-print the resolved node as JSON.
          - With a top-level collection name (e.g. 'persons'): list its items in a table.
        """
        if args and self.root is not None and isinstance(args[0], str):
            top = args[0]
            if (not top.startswith("/")) and hasattr(self.root, top):
                coll = getattr(self.root, top, None)
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

        node = self._resolve_opt(args)
        print(_json_dumps(node))

    def _cmd_getprop(self, args: list[str]) -> None:
        """
        getprop NAME [NAME ...]
        Print values of @property descriptors defined on the class.
        """
        if not args:
            print("usage: getprop NAME [NAME ...]")
            return

        cls = type(self.cur)
        for name in args:
            attr = inspect.getattr_static(cls, name, None)
            if isinstance(attr, property):
                try:
                    value = getattr(self.cur, name)
                except Exception as e:
                    print(f"{cls.__name__}.{name} is a @property but raised: {e!r}")
                else:
                    print(f"{cls.__name__}.{name} = {value!r}")
            else:
                if hasattr(self.cur, name) or hasattr(cls, name):
                    kind = "method" if callable(getattr(self.cur, name, None)) else "attribute"
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

        obj = self.cur
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
        clsname = type(self.cur).__name__
        for name in args:
            value, kind = smart_getattr(self.cur, name)
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

        obj = self.cur
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

        rows.sort(key=lambda r: (r[2] != type(self.cur).__name__, r[0]))
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
            return re.sub(r"(?:\b[\w]+\.)+([A-Z]\w+)", r"\1", s)

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
            abs_parts = self._normalize_path(raw)
            try:
                node = self._node_from_parts(abs_parts)
            except Exception as e:
                print(f"! Error: {e}")
                return
        else:
            node = self.cur
            abs_parts = list(self.path)

        rows = list_fields(node)
        if not rows:
            print("(no fields)")
            return

        expected_map: dict[str, Any] = {}
        expected_disp: dict[str, str] = {}

        col = as_indexable_list(node)
        if col is not None:
            if abs_parts:
                parent = self.root
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

            for idx, v in rows:
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
            for name, _ in rows:
                tp = schema_raw.get(name)
                expected_map[name] = tp
                exp = type_repr(tp) if tp is not None else "-"
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

    def _cmd_schema(self, args: list[str]) -> None:
        """
        schema help
        schema here
        schema class <ClassName>
        schema extras [ClassName] [--all|--direct]
        schema find <field>
        schema where <TypeExpr>
        schema bases <ClassName>
        schema toplevel
        schema diff [PATH]
        schema json [ClassName]
        """
        if not args or args[0] in ("help", "-h", "--help"):
            print((self._cmd_schema.__doc__ or "").strip())
            return

        sub, *rest = args
        table: list[list[str]] = []

        def _class_exists(name: str) -> bool:
            return name in SCHEMA.field_type_table

        def _fields_for_class(name: str) -> Dict[str, Any]:
            return SCHEMA.get_class_fields(name) or {}

        if sub == "here":
            obj = self.cur
            clsname = type(obj).__name__
            fields = _fields_for_class(clsname)
            if not fields:
                print(f"(no schema for {clsname})")
                return
            for fname, ftype in sorted(fields.items()):
                table.append([fname, _typename(ftype)])
            _print_table(table, ["field", "type"])
            return

        if sub == "class":
            if not rest:
                print("usage: schema class <ClassName>")
                return
            clsname = rest[0]
            if not _class_exists(clsname):
                print(f"unknown class: {clsname}")
                return
            for fname, ftype in sorted(_fields_for_class(clsname).items()):
                table.append([fname, _typename(ftype)])
            _print_table(table, ["field", "type"])
            return

        if sub == "extras":
            clsname = None
            mode = "--all"
            for a in rest:
                if a in ("--all", "--direct"):
                    mode = a
                else:
                    clsname = a
            if clsname is None:
                clsname = type(self.cur).__name__
            if not _class_exists(clsname):
                print(f"unknown class: {clsname}")
                return
            extras = SCHEMA.get_all_extras(clsname) if mode == "--all" else SCHEMA.get_extras(clsname)
            if not extras:
                print("(no extras)")
                return
            for fname, ftype in sorted(extras.items()):
                src = "inherited" if fname in (SCHEMA._inherited_extras.get(clsname, {})) else "direct"
                table.append([fname, _typename(ftype), src])
            _print_table(table, ["field", "type", "source"])
            return

        if sub == "find":
            if not rest:
                print("usage: schema find <field>")
                return
            target = rest[0]
            for clsname, fields in sorted(SCHEMA.field_type_table.items()):
                if target in fields:
                    table.append([clsname, target, _typename(fields[target])])
            if not table:
                print("(no matches)")
                return
            _print_table(table, ["class", "field", "type"])
            return

        if sub == "where":
            if not rest:
                print("usage: schema where <TypeExpr>")
                return
            needle = rest[0]
            for clsname, fields in sorted(SCHEMA.field_type_table.items()):
                for fname, ftype in fields.items():
                    tname = _typename(ftype)
                    if needle in tname:
                        table.append([clsname, fname, tname])
            if not table:
                print("(no matches)")
                return
            _print_table(table, ["class", "field", "type"])
            return

        if sub == "bases":
            if not rest:
                print("usage: schema bases <ClassName>")
                return
            clsname = rest[0]
            bases = SCHEMA._bases.get(clsname, [])
            subs = sorted(SCHEMA._subclasses.get(clsname, set()))
            print("Bases:", ", ".join(bases) if bases else "(none)")
            print("Subclasses:", ", ".join(subs) if subs else "(none)")
            return

        if sub == "toplevel":
            tops = sorted(SCHEMA.get_toplevel().keys())
            if not tops:
                print("(no top-level classes)")
                return
            for name in tops:
                table.append([name])
            _print_table(table, ["toplevel"])
            return

        if sub == "json":
            if rest:
                clsname = rest[0]
                if not _class_exists(clsname):
                    print(f"unknown class: {clsname}")
                    return
                payload = {clsname: {k: _typename(v) for k, v in _fields_for_class(clsname).items()}}
            else:
                payload = {k: {f: _typename(t) for f, t in v.items()} for k, v in SCHEMA.field_type_table.items()}
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return

        if sub == "diff":
            target = self.cur
            if rest:
                try:
                    target, _ = resolve_path(self.root, self.cur, rest[0])
                except Exception as e:
                    print(f"! bad path: {e}")
                    return
            clsname = type(target).__name__
            fields = _fields_for_class(clsname)
            if not fields:
                print(f"(no schema for {clsname})")
                return

            runtime: Dict[str, Any] = {}
            if hasattr(target, "__dict__"):
                for k, v in vars(target).items():
                    if k.startswith("_") or callable(v):
                        continue
                    runtime[k] = v

            for fname, stype in sorted(fields.items()):
                if hasattr(target, fname):
                    val = getattr(target, fname)
                    rtype = type(val).__name__ if val is not None else "NoneType"
                    sname = _typename(stype)
                    status_ok = (rtype == sname) or (rtype == getattr(stype, "__name__", rtype))
                    status = "ok" if status_ok else f"{ANSI['red']}mismatch{ANSI['reset']}"
                    s_disp = sname if status_ok else f"{ANSI['yellow']}{sname}{ANSI['reset']}"
                    r_disp = rtype if status_ok else f"{ANSI['red']}{rtype}{ANSI['reset']}"
                    table.append([fname, s_disp, r_disp, status])
                else:
                    sname = _typename(stype)
                    table.append([fname, sname, f"{ANSI['red']}(missing){ANSI['reset']}", f"{ANSI['red']}missing{ANSI['reset']}"])

            extra_names = [k for k in runtime.keys() if k not in fields]
            for k in sorted(extra_names):
                v = runtime[k]
                table.append(
                    [
                        f"{ANSI['cyan']}{k}{ANSI['reset']}",
                        f"{ANSI['cyan']}(extra){ANSI['reset']}",
                        type_of(v),
                        f"{ANSI['cyan']}extra{ANSI['reset']}",
                    ]
                )

            _print_table(table, ["field", "schema", "runtime", "status"])
            return

        print(f"unknown subcommand: {sub}. Try 'schema help'.")

    def _cmd_extras(self, args: list[str]) -> None:
        """
        extras [--all|--direct] [--filter SUBSTR]
        List extras across ALL classes in the schema.
        """
        mode = "--all"
        flt = None

        i = 0
        while i < len(args):
            a = args[i]
            if a in ("--all", "--direct"):
                mode = a
            elif a in ("-f", "--filter"):
                if i + 1 >= len(args):
                    print("missing value for --filter")
                    return
                flt = args[i + 1]
                i += 1
            else:
                print(self._cmd_extras.__doc__.strip()) # type: ignore
                return
            i += 1

        rows = []
        for clsname in sorted(SCHEMA.field_type_table):
            direct = SCHEMA.get_extras(clsname)
            items = (SCHEMA.get_all_extras(clsname) if mode == "--all" else direct).items()
            inherited_names = set(SCHEMA.get_all_extras(clsname).keys()) - set(direct.keys())

            for fname, ftype in sorted(items):
                tstr = _typename(ftype)
                src = "inherited" if fname in inherited_names else "direct"
                if flt and not any(flt in s for s in (clsname, fname, tstr)):
                    continue
                rows.append([clsname, fname, tstr, src])

        if not rows:
            print("(no extras)")
            return

        _print_table(rows, ["class", "field", "type", "source"])

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

        obj = self.cur
        cls = type(obj)

        def _instantiate_for_field(field_name: str) -> Any:
            elem_type = _expected_element_type_from_parent(obj, field_name)
            if elem_type is None:
                fields = SCHEMA.get_class_fields(type(obj).__name__) or {}
                field_type = fields.get(field_name)
                if field_type is None:
                    raise ValueError(f"no schema info for field {field_name!r}")
                elem_type = field_type

            from typing import get_args as _ga, get_origin as _go

            def _strip_optional(tp: Any) -> Any:
                origin = _go(tp)
                if origin is None:
                    return tp
                args2 = [a for a in _ga(tp) if a is not type(None)]  # noqa: E721
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
                            idx = len(cur_val) # type: ignore
                        except Exception:
                            idx = "?"
                        try:
                            cur_val.append(new_instance) # type: ignore
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
        if isinstance(self.root, GedcomX) and (self.root is not None):
            print("Resolving resource references (size may affect time)…")
            stats = ResolveStats()
            Serialization._resolve_structure(self.root, self.root._resolve, stats=stats)
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
        write gx PATH
        Write current root as GEDCOM-X JSON.
        """
        if len(args) < 2 or args[0] not in ["gx","adbg","jsonl"]:
            print("usage: write FORMAT[gx | adbg | jsonl] PATH")
            return
        if args[0] == "gx":
            js = orjson.dumps(
                Serialization.serialize(self.root),
                option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE,
            )
            with open(args[1], "wb") as f:
                f.write(js)
        elif args[0] == "jsonl":
            if self.cur is not None:
                path = Path(args[1].strip('"').strip("'"))
                return write_jsonl(self.cur, Path(path))
            print("usage: write FORMAT[gx | adbg | jsonl] PATH")
            return
        elif args[0] == "adbg":
            if args[1]:
                argo_graph_files_folder = Path(args[1])
                argo_graph_files_folder.mkdir(parents=True, exist_ok=True)
                print('Writing Argo Graph Files')
                if self.root is None:
                    print("No data loaded.")
                    return
                file_specs = make_arango_graph_files(self.root)
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

    def _cmd_type(self, args: list[str]) -> None:
        """
        type                           → describe the current node's runtime type + schema (inferred)
        type <PATH|ATTR>               → describe that child/target
        type class <ClassName>         → describe a schema class directly

        Flags:
        --fields   : include the class' field table
        --mro      : show Python MRO
        -c/--class : force schema class by name (for current/target node)
        """
        show_fields = False
        show_mro = False
        forced_class: str | None = None
        pos: list[str] = []

        i = 0
        while i < len(args):
            a = args[i]
            if a == "--fields":
                show_fields = True
            elif a == "--mro":
                show_mro = True
            elif a in ("-c", "--class"):
                if i + 1 >= len(args):
                    print("missing class name for --class")
                    return
                forced_class = args[i + 1]
                i += 1
            else:
                pos.append(a)
            i += 1

        def _schema_class_exists(name: str) -> bool:
            return name in SCHEMA.field_type_table

        def _infer_schema_class_from_node(node) -> str | None:
            if node is not None:
                cname = type(node).__name__
                if _schema_class_exists(cname):
                    return cname
            item_t = getattr(node, "item_type", None)
            if item_t:
                cname = getattr(item_t, "__name__", None)
                if cname and _schema_class_exists(cname):
                    return cname
            if isinstance(node, (list, tuple)) and node:
                cname = type(node[0]).__name__
                if _schema_class_exists(cname):
                    return cname
            if getattr(self, "root", None) is not None:
                cname = type(self.root).__name__
                if _schema_class_exists(cname):
                    return cname
            return None

        def _summ_runtime(node) -> list[list[str]]:
            rows: list[list[str]] = []
            if node is None:
                rows.append(["runtime", "type", "NoneType"])
                return rows
            rtype = type(node)
            rows.append(["runtime", "type", f"{rtype.__module__}.{rtype.__name__}"])
            if isinstance(node, dict):
                rows.append(["runtime", "container", f"dict (len={len(node)})"])
            elif isinstance(node, (list, tuple, set)):
                rows.append(["runtime", "container", f"{rtype.__name__} (len={len(node)})"])
                if node:
                    rows.append(["runtime", "elem-type", type(next(iter(node))).__name__])
            if getattr(node, "item_type", None) is not None:
                it = node.item_type # type: ignore
                rows.append(["runtime", "item_type", getattr(it, "__name__", str(it))])
                rows.append(["runtime", "size", str(len(node)) if hasattr(node, "__len__") else "?"])
            return rows

        if pos and pos[0] == "class":
            if len(pos) < 2:
                print("usage: type class <ClassName> [--fields] [--mro]")
                return
            clsname = pos[1]
            if not _schema_class_exists(clsname):
                print(f"unknown class: {clsname}")
                return
            print(f"=== type: class {clsname} ===")
            bases = SCHEMA._bases.get(clsname, [])
            subs = sorted(SCHEMA._subclasses.get(clsname, set()))
            print("bases     :", ", ".join(bases) if bases else "(none)")
            print("subclasses:", ", ".join(subs) if subs else "(none)")
            fields = SCHEMA.get_class_fields(clsname) or {}
            print(f"fields    : {len(fields)}")
            if show_fields and fields:
                rows = []
                direct_ex = SCHEMA.get_extras(clsname)
                inh_all = SCHEMA.get_all_extras(clsname)
                inh_names = set(inh_all.keys()) - set(direct_ex.keys())
                for fname, ftype in sorted(fields.items()):
                    src = (
                        "extra:direct"
                        if fname in direct_ex
                        else ("extra:inherited" if fname in inh_names else "")
                    )
                    rows.append([fname, _typename(ftype), src])
                _print_table(rows, ["field", "schema-type", "note"])
            return

        target = self.cur
        field_name = None
        parent_for_field = None

        if pos:
            if len(pos) == 1 and hasattr(self.cur, pos[0]):
                field_name = pos[0]
                parent_for_field = self.cur
                target = getattr(self.cur, field_name)
            else:
                try:
                    node, stack = resolve_path(self.root, self.cur, pos[0])
                except Exception as e:
                    print(f"! bad path: {e}")
                    return
                target = node
                if stack:
                    field_name = stack[-1]
                    try:
                        parent_for_field, _ = resolve_path(self.root, self.cur, "/".join(stack[:-1]))
                    except Exception:
                        parent_for_field = None

        print(f"=== type: {('field ' + field_name) if field_name else 'node'} ===")
        rows = _summ_runtime(target)

        if forced_class:
            if not _schema_class_exists(forced_class):
                print(f"unknown class: {forced_class}")
                return
            clsname = forced_class
            rows.append(["schema", "class (forced)", clsname])
        else:
            clsname = _infer_schema_class_from_node(target)
            rows.append(["schema", "class", clsname or "(none)"])

        if clsname:
            bases = SCHEMA._bases.get(clsname, [])
            subs = sorted(SCHEMA._subclasses.get(clsname, set()))
            rows.append(["schema", "bases", ", ".join(bases) if bases else "(none)"])
            rows.append(["schema", "subs", ", ".join(subs) if subs else "(none)"])

        if field_name and parent_for_field is not None:
            parent_cls = type(parent_for_field).__name__
            ftable = SCHEMA.get_class_fields(parent_cls) or {}
            sch_type = _typename(ftable.get(field_name, "(not in schema)"))
            run_type = type(target).__name__ if target is not None else "NoneType"
            rows.append(["field", "parent-class", parent_cls])
            rows.append(["field", "schema-type", sch_type])
            rows.append(["field", "runtime-type", run_type])
            if field_name in ftable:
                s_ok = (run_type == getattr(ftable[field_name], "__name__", run_type)) or (run_type == sch_type)
                rows.append(["field", "match", "ok" if s_ok else "MISMATCH"])

        _print_table(rows, ["scope", "key", "value"])

        if show_fields and clsname:
            fields = SCHEMA.get_class_fields(clsname) or {}
            if fields:
                print("\n--- fields ---")
                rows2 = []
                direct_ex = SCHEMA.get_extras(clsname)
                inh_all = SCHEMA.get_all_extras(clsname)
                inh_names = set(inh_all.keys()) - set(direct_ex.keys())
                for fname, ftype in sorted(fields.items()):
                    src = (
                        "extra:direct"
                        if fname in direct_ex
                        else ("extra:inherited" if fname in inh_names else "")
                    )
                    rows2.append([fname, _typename(ftype), src])
                _print_table(rows2, ["field", "schema-type", "note"])

        if show_mro and target is not None:
            try:
                mro_names = [c.__name__ for c in type(target).mro()]
                print("\n--- mro ---")
                print(" → ".join(mro_names))
            except Exception:
                pass


# ── Entrypoint ───────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    init_logging(app_name="gedcomtools")
    parser = argparse.ArgumentParser(description="GEDCOM-X Inspector (schema-aware, cleaned)")
    parser.add_argument("path", nargs="?", help="optional file to load at start (.ged or .json)")
    args = parser.parse_args(argv)

    sh = Shell()
    if args.path:
        sh._cmd_load([args.path])
    sh.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
