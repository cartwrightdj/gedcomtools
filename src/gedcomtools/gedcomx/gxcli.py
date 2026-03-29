#!/usr/bin/env python3
"""Interactive command-line shell for browsing, editing, and exporting GedcomX data."""

from __future__ import annotations

# ======================================================================
#  Project: Gedcom-X
#  File:    gxcli.py
#  Author:  David J. Cartwright
#  Purpose: cli to inspect GedcomX objects
#  Created: 2026-02-01
# ======================================================================
import argparse
import ast
import dataclasses
import glob as _glob_mod
import inspect  # used for descriptor-safe lookups
import json
import logging
import os
import re
import shlex
import shutil
import sys
import traceback
from dataclasses import fields as dataclass_fields, is_dataclass
from pathlib import Path
from typing import Any, Iterable, get_args, get_origin

try:
    import readline as _readline
    _READLINE = True
except ImportError:
    _readline = None  # type: ignore[assignment]
    _READLINE = False

import orjson

# GEDCOM Module Types
from gedcomtools.glog import setup_logging, get_logger, LoggerSpec

# Logging is initialized in main() to avoid side effects on import.
_LOG_MGR = None


def init_logging(app_name: str = "gedcomtools"):
    """Initialize CLI logging configuration."""
    global _LOG_MGR  # pylint: disable=global-statement
    if _LOG_MGR is None:
        _LOG_MGR = setup_logging(app_name=app_name)
    return _LOG_MGR

from gedcomtools.gedcomx import GedcomConverter, GedcomX
from gedcomtools.gedcomx.schemas import SCHEMA, type_repr
from gedcomtools.gedcomx.serialization import ResolveStats, Serialization
from gedcomtools.gedcomx.cli import objects_to_schema_table, write_jsonl
from gedcomtools.gedcomx.arango import make_arango_graph_files


SHELL_VERSION = '0.7.1'

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
    """Return whether the value should be treated as a primitive shell value."""
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
    if hasattr(obj, "__dict__"):
        d = {k: v for k, v in vars(obj).items() if not k.startswith("_")}
        if d:
            return d
    return obj

def to_plain(obj: Any, *, max_depth: int = 6, _seen: set[int] | None = None) -> Any:
    """Convert nested objects into plain Python data structures."""
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
    """Return a short preview string for a value."""
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
    """Return the visible fields for a shell node."""
    if isinstance(obj, dict):
        return [(str(k), v) for k, v in obj.items()]
    if isinstance(obj, (list, tuple)):
        return [(str(i), v) for i, v in enumerate(obj)]
    # Pydantic models: use model_fields + model_extra to enumerate fields correctly.
    # Must be checked before as_indexable_list because BaseModel.__iter__ yields
    # (field, value) tuples — which would make every model appear to be a list of tuples.
    if not isinstance(obj, type) and hasattr(type(obj), "model_fields"):
        fields = [(k, getattr(obj, k)) for k in type(obj).model_fields]
        extra = getattr(obj, "model_extra", None) or {}
        fields += [(k, v) for k, v in extra.items() if not k.startswith("_")]
        return fields
    col = as_indexable_list(obj)
    if col is not None:
        return [(str(i), v) for i, v in enumerate(col)]
    if is_dataclass(obj) and not isinstance(obj, type):
        return [(f.name, getattr(obj, f.name)) for f in dataclass_fields(obj)]
    if hasattr(obj, "__dict__"):
        return [(k, v) for k, v in vars(obj).items() if not k.startswith("_")]
    return []

def type_of(obj: Any) -> str:
    """Return a readable type name for the given value."""
    return getattr(obj, "__name__", None) or obj.__class__.__name__

# ── Collection detection ─────────────────────────────────────────────────────
def as_indexable_list(obj: Any) -> list[Any] | None:
    """Return the value as an indexable sequence when possible."""
    if obj is None or isinstance(obj, (str, bytes, bytearray, dict)):
        return None
    if isinstance(obj, (list, tuple, set)):
        return list(obj)
    # Pydantic models have __iter__ that yields (field, value) tuples — not items.
    # Skip them here; list_fields handles them directly via model_fields.
    if not isinstance(obj, type) and hasattr(type(obj), "model_fields"):
        return None
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
    """Return the named or indexed child value from a node."""
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
    """Resolve a shell path expression against the current root."""
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
        k, v = (args + (Any, Any))[:2]
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
    # Pydantic models: read type annotations directly from model_fields.
    cls = type(obj)
    if not isinstance(obj, type) and hasattr(cls, "model_fields"):
        return {k: fi.annotation for k, fi in cls.model_fields.items()}
    # SCHEMA auto-registration for GedcomXModel subclasses.
    cls = type(obj)
    schema_fields = SCHEMA.get_class_fields(cls)
    if schema_fields:
        return schema_fields
    # Fallback: read __init__ type hints for plain classes (e.g. GedcomX).
    try:
        hints = {
            k: v
            for k, v in inspect.get_annotations(cls.__init__, eval_str=False).items()
            if k not in ("self", "return")
        }
        if hints:
            return hints
    except Exception:
        pass
    # Last resort: class-level __annotations__ merged up the MRO.
    merged: dict[str, Any] = {}
    for base in reversed(cls.__mro__):
        merged.update(getattr(base, "__annotations__", {}))
    return {k: v for k, v in merged.items() if not k.startswith("_")}

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
    if expected is None or expected is Any:
        return True

    def _head_inner_from_expected(exp: Any) -> tuple[str, str | None]:
        if isinstance(exp, str):
            head = exp.split("[", 1)[0].split(".")[-1]
            inner = None
            if "[" in exp and exp.endswith("]"):
                inner = exp[exp.find("[") + 1 : -1].split(",", 1)[0].split(".")[-1].strip()
            return head, inner
        origin = get_origin(exp)
        if origin is not None:
            head = getattr(origin, "__name__", str(origin)).rsplit(".", maxsplit=1)[-1]
            args = get_args(exp)
            inner = None
            if args:
                a0 = args[0]
                inner = (getattr(a0, "__name__", str(a0))).rsplit(".", maxsplit=1)[-1]
            return head, inner
        if isinstance(exp, type):
            return exp.__name__, None
        return str(exp).rsplit(".", maxsplit=1)[-1], None

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
    """Safely fetch an attribute without triggering shell-hostile behavior."""
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

# ── Settings ─────────────────────────────────────────────────────────────────
_SETTINGS_PATH = Path.home() / ".config" / "gedcomtools" / "gxcli.json"
_HISTORY_PATH  = Path.home() / ".config" / "gedcomtools" / "gxcli_history"

_DEFAULT_SETTINGS: dict[str, Any] = {
    "page_size": 20,
    "color": "auto",
    "history_size": 200,
}

def _load_settings() -> dict[str, Any]:
    cfg = dict(_DEFAULT_SETTINGS)
    if _SETTINGS_PATH.exists():
        try:
            with open(_SETTINGS_PATH) as _f:
                _data = json.load(_f)
            cfg.update({k: v for k, v in _data.items() if k in _DEFAULT_SETTINGS})
        except Exception:
            pass
    return cfg

def _save_settings(cfg: dict[str, Any]) -> None:
    try:
        _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_SETTINGS_PATH, "w") as _f:
            json.dump(cfg, _f, indent=2)
    except Exception as e:
        print(f"Warning: could not save settings: {e}")


# ── Grep walker ───────────────────────────────────────────────────────────────
def _grep_node(
    obj: Any,
    rx: "re.Pattern[str]",
    prefix: str,
    results: list[tuple[str, str]],
    depth: int,
    visited: set[int],
    max_depth: int,
) -> None:
    obj_id = id(obj)
    if obj_id in visited or depth > max_depth:
        return
    visited.add(obj_id)
    for key, val in list_fields(obj):
        path = f"{prefix}/{key}" if prefix else str(key)
        if isinstance(val, str):
            if rx.search(val):
                results.append((path, val))
        elif isinstance(val, (int, float)):
            if rx.search(str(val)):
                results.append((path, str(val)))
        elif val is not None and not isinstance(val, bool):
            _grep_node(val, rx, path, results, depth + 1, visited, max_depth)


# ── Shell / REPL ─────────────────────────────────────────────────────────────
class Shell:
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
            except Exception:
                return None
        return completer

    def run(self) -> None:
        """Run the interactive shell loop."""
        self._interactive = sys.stdin.isatty()

        # Disable ANSI escape codes when stdout is piped (not a real terminal).
        if not sys.stdout.isatty():
            global _RED, _RESET, ANSI  # pylint: disable=global-statement
            _RED = _RESET = ""
            ANSI = {k: "" for k in ANSI}

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
            except Exception:
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

    # ---- commands -----------------------------------------------------------
    def _cmd_ver(self, _args: list[str]) -> None:
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
                    if self._interactive:
                        input("\n[Press Enter to continue…]\n")

        page_table(objects_to_schema_table(self.gedcomx.agents))

    def _cmd_extend(self, args: list[str]) -> None:
        """
        extend PATH
        Load a .ged, .json, or .zip and extend current root (must support .extend()).
        """
        if len(args) != 1:
            print("usage: extend PATH")
            return
        path = args[0].strip().strip('"')
        low = path.lower()

        if self.root is None or not hasattr(self.root, "extend"):
            print("Current root is None or does not support .extend()")
            return

        if low.endswith(".ged"):
            print("Loading GEDCOM (size may affect time)…")
            gx = self._load_from_ged(path)
            if gx is not None:
                self.root.extend(gx)
                print("Loaded and converted to GedcomX.")
            return

        if low.endswith(".zip"):
            print("Loading GedcomX ZIP archive…")
            gx = self._load_from_zip(path)
            self.root.extend(gx)
            print("Loaded GedcomX ZIP.")
            return

        if low.endswith(".json"):
            print("Loading Gedcom-X from JSON (size may affect time)…")
            gx = self._load_from_json(path)
            self.root.extend(gx)
            print("Loaded GEDCOM-X JSON.")
            return

        print(f"Unsupported file type. Use .ged, .zip, or .json: {path}")

    def _cmd_load(self, args: list[str]) -> None:
        """
        load PATH
        Load a .ged (GEDCOM 5/7), .json (GedcomX), or .zip (GedcomX archive) and set as root.
        """
        if len(args) != 1:
            print("usage: load PATH")
            return
        path = args[0].strip().strip('"')
        low = path.lower()

        if low.endswith(".ged"):
            print("Loading GEDCOM (size may affect time)…")
            gx = self._load_from_ged(path)
            if gx is not None:
                self._set_root(gx)
                print("Loaded and converted to GedcomX.")
            return

        if low.endswith(".zip"):
            print("Loading GedcomX ZIP archive…")
            gx = self._load_from_zip(path)
            self._set_root(gx)
            print("Loaded GedcomX ZIP.")
            return

        if low.endswith(".json"):
            print("Loading Gedcom-X from JSON (size may affect time)…")
            gx = self._load_from_json(path)
            self._set_root(gx)
            print("Loaded GEDCOM-X JSON.")
            return

        print(f"Unsupported file type. Use .ged, .zip, or .json: {path}")

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

    # ------------------------------------------------------------------
    # Extension / plugin management
    # ------------------------------------------------------------------

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

        # ── helpers ───────────────────────────────────────────────────
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
            """Return a human-readable file path for a dotted module name."""
            # Check if already imported
            mod = sys.modules.get(modname)
            if mod:
                f = getattr(mod, "__file__", None)
                if f:
                    return f
                locs = getattr(mod, "__path__", None)
                if locs:
                    return list(locs)[0]
            # Not yet imported — use find_spec (no import side-effect)
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
            """Return the best-known file/module location for an entry."""
            src = entry.source
            # For loaded entries prefer the live module __file__
            if entry.status == PluginStatus.LOADED:
                mod = sys.modules.get(entry.name) or sys.modules.get(src)
                if mod and getattr(mod, "__file__", None):
                    return mod.__file__
            # For module-name sources resolve without importing
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

        # ── ls ────────────────────────────────────────────────────────
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

        # ── show ──────────────────────────────────────────────────────
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

        # ── scan ──────────────────────────────────────────────────────
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

            found: list[tuple[str, str]] = []  # (modname, location)
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

        # ── authorize ─────────────────────────────────────────────────
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

        # ── load ──────────────────────────────────────────────────────
        if sub == "load":
            name_filter = rest[0] if rest else None
            try:
                if name_filter:
                    # Find matching entries (substring match on name)
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

        # ── trust ─────────────────────────────────────────────────────
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

    # ------------------------------------------------------------------
    # Ahnentafel
    # ------------------------------------------------------------------

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
        gen = Shell._ahnen_generation(n)
        # Walk up to determine paternal/maternal line
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
        has_entry = n in self._ahnen
        father_n, mother_n = 2 * n, 2 * n + 1
        has_children = depth < max_depth and (
            father_n in self._ahnen or mother_n in self._ahnen
            or (depth + 1 < max_depth and any(
                k in self._ahnen for k in (2*father_n, 2*father_n+1, 2*mother_n, 2*mother_n+1)
            ))
        )

        if not has_entry and not has_children:
            return

        connector = "└── " if is_last else "├── "
        line_prefix = prefix + connector if depth > 0 else ""
        child_prefix = prefix + ("    " if is_last else "│   ") if depth > 0 else ""

        relation = self._ahnen_relation(n)
        if has_entry:
            summary = self._ahnen_fmt(self._ahnen[n], short=True)
            print(f"{line_prefix}#{n}  {summary}  [{relation}]")
        else:
            print(f"{line_prefix}#{n}  —  [{relation}]")

        if depth < max_depth:
            # Show father first (even), then mother (odd) — both are ancestors
            father_exists = father_n in self._ahnen or (depth + 1 < max_depth and any(
                k in self._ahnen for k in range(2*father_n, 4*father_n)))
            mother_exists = mother_n in self._ahnen or (depth + 1 < max_depth and any(
                k in self._ahnen for k in range(2*mother_n, 4*mother_n)))

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

        # ── set ───────────────────────────────────────────────────────
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
            entry: dict = dict(self._ahnen.get(n, {"name": ""}))
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

            self._ahnen[n] = entry

            relation = self._ahnen_relation(n)
            child_n = n >> 1
            child_info = f"  (parent of #{child_n})" if n > 1 else ""
            print(f"Set #{n} [{relation}]{child_info}: {self._ahnen_fmt(entry)}")
            return

        # ── get ───────────────────────────────────────────────────────
        if sub == "get":
            if not rest:
                print("usage: ahnen get N")
                return
            try:
                n = int(rest[0])
            except ValueError:
                print(f"N must be an integer")
                return
            if n not in self._ahnen:
                print(f"No entry for #{n}.")
                return
            e = self._ahnen[n]
            rel = self._ahnen_relation(n)
            print(f"#{n}  {rel}")
            print(f"  Name        : {e['name']}")
            if e.get("birth_date"):  print(f"  Born        : {e['birth_date']}")
            if e.get("birth_place"): print(f"  Birth place : {e['birth_place']}")
            if e.get("death_date"):  print(f"  Died        : {e['death_date']}")
            if e.get("death_place"): print(f"  Death place : {e['death_place']}")
            if e.get("marr_date"):   print(f"  Married     : {e['marr_date']}")
            if e.get("marr_place"):  print(f"  Marr. place : {e['marr_place']}")
            # Show relationship context
            if n > 1:
                child_n = n >> 1
                print(f"  Parent of   : #{child_n} ({self._ahnen.get(child_n, {}).get('name', '—')})")
            father_n, mother_n = 2*n, 2*n+1
            if father_n in self._ahnen or mother_n in self._ahnen:
                print(f"  Father      : #{father_n} ({self._ahnen.get(father_n, {}).get('name', '—')})")
                print(f"  Mother      : #{mother_n} ({self._ahnen.get(mother_n, {}).get('name', '—')})")
            return

        # ── ls ────────────────────────────────────────────────────────
        if sub == "ls":
            if not self._ahnen:
                print("No Ahnentafel entries.  Use: ahnen set N NAME [b=DATE] ...")
                return
            nums = sorted(self._ahnen)
            # Column widths
            num_w  = max(len(str(n)) for n in nums)
            name_w = max(len(self._ahnen[n]["name"]) for n in nums)
            rel_w  = max(len(self._ahnen_relation(n)) for n in nums)
            print(f"{'#':<{num_w}}  {'Name':<{name_w}}  {'Relation':<{rel_w}}  Born        Died        Married")
            print("-" * (num_w + name_w + rel_w + 40))
            for n in nums:
                e = self._ahnen[n]
                rel = self._ahnen_relation(n)
                bd = e.get("birth_date", "")
                dd = e.get("death_date", "")
                md = e.get("marr_date", "")
                print(f"{n:<{num_w}}  {e['name']:<{name_w}}  {rel:<{rel_w}}  {bd:<12}{dd:<12}{md}")
            return

        # ── tree ──────────────────────────────────────────────────────
        if sub == "tree":
            if not self._ahnen:
                print("No Ahnentafel entries.")
                return
            try:
                max_depth = int(rest[0]) if rest else 3
            except ValueError:
                max_depth = 3
            total = len(self._ahnen)
            max_n = max(self._ahnen)
            gens = self._ahnen_generation(max_n)
            print(f"Pedigree  ({total} entr{'y' if total==1 else 'ies'}, {gens+1} generation(s))")
            print()
            self._ahnen_print_tree(1, max_depth)
            return

        # ── clear ─────────────────────────────────────────────────────
        if sub == "clear":
            if not rest:
                count = len(self._ahnen)
                self._ahnen.clear()
                print(f"Cleared {count} entr{'y' if count==1 else 'ies'}.")
                return
            try:
                n = int(rest[0])
            except ValueError:
                print("usage: ahnen clear [N]")
                return
            if n in self._ahnen:
                del self._ahnen[n]
                print(f"Removed #{n}.")
            else:
                print(f"No entry for #{n}.")
            return

        # ── build ─────────────────────────────────────────────────────
        if sub == "build":
            if not self._ahnen:
                print("No Ahnentafel entries to build from.")
                return
            from gedcomtools.gedcomx import (
                GedcomX, Person, Relationship, RelationshipType,
                Fact, FactType, Name, NameForm, Gender, GenderType,
                Date, PlaceReference,
            )
            from gedcomtools.gedcomx.name import QuickName

            gx = GedcomX()
            persons: dict[int, Person] = {}

            # Pass 1: create all Person objects
            for n, e in sorted(self._ahnen.items()):
                p = Person()
                p.id = f"P{n}"
                p.names.append(QuickName(e["name"]))

                # Gender: even → male, odd → female, 1 → unknown
                if n == 1:
                    p.gender = Gender(type=GenderType.Unknown)
                elif n % 2 == 0:
                    p.gender = Gender(type=GenderType.Male)
                else:
                    p.gender = Gender(type=GenderType.Female)

                # Birth fact
                if e.get("birth_date") or e.get("birth_place"):
                    f = Fact(type=FactType.Birth)
                    if e.get("birth_date"):
                        f.date = Date(original=e["birth_date"])
                    if e.get("birth_place"):
                        f.place = PlaceReference(original=e["birth_place"])
                    p.facts.append(f)

                # Death fact
                if e.get("death_date") or e.get("death_place"):
                    f = Fact(type=FactType.Death)
                    if e.get("death_date"):
                        f.date = Date(original=e["death_date"])
                    if e.get("death_place"):
                        f.place = PlaceReference(original=e["death_place"])
                    p.facts.append(f)

                gx.persons.append(p)
                persons[n] = p

            # Pass 2: parent-child and couple relationships
            processed_couples: set[int] = set()
            for n in sorted(persons):
                father_n, mother_n = 2 * n, 2 * n + 1

                # Couple relationship (father + mother)
                couple_key = min(father_n, mother_n)
                if couple_key not in processed_couples:
                    if father_n in persons and mother_n in persons:
                        marr_e = self._ahnen.get(father_n, {}) or self._ahnen.get(mother_n, {})
                        # Prefer father's entry for marriage data, fall back to mother's
                        fa_e = self._ahnen.get(father_n, {})
                        mo_e = self._ahnen.get(mother_n, {})
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

                # Parent → child relationships
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

            self._set_root(gx)
            self.gedcomx = gx
            p_count = len(persons)
            r_count = len(gx.relationships)
            print(f"Built GedcomX: {p_count} person(s), {r_count} relationship(s). Loaded as root.")
            return

        # ── import ────────────────────────────────────────────────────
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
                # Find where key:value tokens start
                name_parts = []
                kv_start = 2
                for i, tok in enumerate(tokens[1:], 1):
                    if ":" in tok and tok.split(":")[0].lower() in self._AHNEN_KEY_MAP:
                        kv_start = i
                        break
                    name_parts.append(tok)
                name = " ".join(name_parts)
                entry: dict = dict(self._ahnen.get(n, {"name": ""}))
                entry["name"] = name
                for tok in tokens[kv_start:]:
                    if ":" not in tok:
                        continue
                    k, v = tok.split(":", 1)
                    field = self._AHNEN_KEY_MAP.get(k.lower())
                    if field:
                        entry[field] = v
                self._ahnen[n] = entry
                imported += 1
            print(f"Imported {imported} entr{'y' if imported==1 else 'ies'} from {path}.")
            return

        # ── export ────────────────────────────────────────────────────
        if sub == "export":
            if not rest:
                print("usage: ahnen export FILE")
                return
            path = rest[0].strip('"').strip("'")
            lines = ["# Ahnentafel export — gedcomtools gxcli", "# N  Name  key:value ..."]
            for n in sorted(self._ahnen):
                e = self._ahnen[n]
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
                print(f"Exported {len(self._ahnen)} entr{'y' if len(self._ahnen)==1 else 'ies'} to {path}.")
            except OSError as e:
                print(f"Error writing {path}: {e}")
            return

        print(f"Unknown subcommand {sub!r}. Use: set, get, ls, tree, clear, build, import, export")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _cmd_back(self, args: list[str]) -> None:
        """
        back
        Return to the previous location in navigation history.
        """
        _ = args
        if not self._nav_history:
            print("No navigation history.")
            return
        cur, path = self._nav_history.pop()
        self.cur = cur
        self.path = path
        print("/" + "/".join(self.path))

    def _cmd_goto(self, args: list[str]) -> None:
        """
        goto ID
        Navigate directly to any top-level object by its id.
        """
        if not args:
            print("usage: goto ID")
            return
        if self.gedcomx is None:
            print("No GedcomX data loaded.")
            return
        target_id = args[0]
        if target_id not in self.gedcomx.id_index:
            print(f"No object with id {target_id!r} found.")
            return
        _collections = [
            ("persons",             self.gedcomx.persons),
            ("relationships",       self.gedcomx.relationships),
            ("agents",              self.gedcomx.agents),
            ("sourceDescriptions",  self.gedcomx.sourceDescriptions),
            ("places",              self.gedcomx.places),
            ("events",              self.gedcomx.events),
            ("documents",           self.gedcomx.documents),
            ("groups",              self.gedcomx.groups),
        ]
        self._nav_history.append((self.cur, list(self.path)))
        for coll_name, coll in _collections:
            for i, item in enumerate(coll):
                if getattr(item, "id", None) == target_id:
                    self.path = [coll_name, str(i)]
                    self.cur = item
                    print(f"→ /{'/'.join(self.path)}")
                    return
        # Fallback: object found in id_index but not enumerated above
        self.cur = self.gedcomx.id_index[target_id]
        self.path = [f"@{target_id}"]
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
        if self.gedcomx is None:
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
            "persons": (self.gedcomx.persons, _person_label),
            "agents": (self.gedcomx.agents, _agent_label),
            "places": (self.gedcomx.places, _place_label),
            "events": (self.gedcomx.events, _event_label),
            "sources": (self.gedcomx.sourceDescriptions, _source_label),
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
            if not self._bookmarks:
                print("No bookmarks.")
                return
            name_w = max(len(n) for n in self._bookmarks)
            for name, (_, path) in sorted(self._bookmarks.items()):
                print(f"  {name:<{name_w}}  /{'/'.join(path)}")
            return
        if args[0] == "rm":
            if len(args) < 2:
                print("usage: bookmark rm NAME")
                return
            name = args[1]
            if name in self._bookmarks:
                del self._bookmarks[name]
                print(f"Removed {name!r}.")
            else:
                print(f"No bookmark named {name!r}.")
            return
        name = args[0]
        self._bookmarks[name] = (self.cur, list(self.path))
        print(f"Bookmark {name!r} → /{'/'.join(self.path)}")

    def _cmd_go(self, args: list[str]) -> None:
        """
        go NAME   Navigate to a saved bookmark.
        """
        if not args:
            print("usage: go NAME")
            if self._bookmarks:
                print("Bookmarks:", ", ".join(sorted(self._bookmarks)))
            return
        name = args[0]
        if name not in self._bookmarks:
            print(f"No bookmark named {name!r}.")
            if self._bookmarks:
                print("Available:", ", ".join(sorted(self._bookmarks)))
            return
        self._nav_history.append((self.cur, list(self.path)))
        cur, path = self._bookmarks[name]
        self.cur = cur
        self.path = list(path)
        print(f"→ /{'/'.join(self.path)}")

    # ------------------------------------------------------------------
    # Data inspection
    # ------------------------------------------------------------------

    def _cmd_stats(self, args: list[str]) -> None:
        """
        stats
        Show counts for all top-level GedcomX collections.
        """
        _ = args
        if self.gedcomx is None:
            print("No GedcomX data loaded.")
            return
        gx = self.gedcomx
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
        start = self.root if from_root else self.cur
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
        if self.gedcomx is None:
            print("No GedcomX data loaded.")
            return
        result = self.gedcomx.validate()
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
        if self.gedcomx is None:
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
            ("persons",            self.gedcomx.persons,            other.persons),
            ("relationships",      self.gedcomx.relationships,      other.relationships),
            ("agents",             self.gedcomx.agents,             other.agents),
            ("sourceDescriptions", self.gedcomx.sourceDescriptions, other.sourceDescriptions),
            ("places",             self.gedcomx.places,             other.places),
            ("events",             self.gedcomx.events,             other.events),
            ("documents",          self.gedcomx.documents,          other.documents),
            ("groups",             self.gedcomx.groups,             other.groups),
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

    # ------------------------------------------------------------------
    # Shell settings
    # ------------------------------------------------------------------

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
            for k, v in self._settings.items():
                print(f"  {k} = {v!r}  (default: {_DEFAULT_SETTINGS[k]!r})")
            return
        if args[0] == "reset":
            self._settings = dict(_DEFAULT_SETTINGS)
            _save_settings(self._settings)
            print("Settings reset to defaults.")
            return
        key = args[0]
        if key not in _DEFAULT_SETTINGS:
            print(f"Unknown setting {key!r}. Known: {', '.join(_DEFAULT_SETTINGS)}")
            return
        if len(args) == 1:
            print(f"{key} = {self._settings[key]!r}")
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
        self._settings[key] = val
        _save_settings(self._settings)
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
        from gedcomtools.cli import _load_g5, _load_g7, _sniff_source_type

        src_type = _sniff_source_type(Path(path))

        if src_type == "g5":
            from gedcomtools.gedcom5.validator5 import Gedcom5Validator
            print("  Parsing GEDCOM 5…")
            g5 = _load_g5(Path(path))
            print("  Validating GEDCOM 5…")
            issues = Gedcom5Validator(g5).validate()
            self._print_validation_results(issues)
            print("  Converting to GedcomX…")
            conv = GedcomConverter()
            gx: GedcomX = conv.Gedcom5x_GedcomX(g5)
            self.gedcomx = gx
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
        self.gedcomx = gx
        return gx

    def _load_from_json(self, path: str) -> Any:
        from gedcomtools.cli import _load_gx
        try:
            gx = _load_gx(Path(path))
            self.gedcomx = gx
            return gx
        except Exception:
            # Fallback: raw dict (e.g. partial / non-GedcomX JSON)
            with open(path, "rb") as f:
                return _json_loads(f.read())

    def _set_root(self, root: Any) -> None:
        self.root = root
        self.cur = root
        self.path.clear()
        self._nav_history.clear()

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
        self._nav_history.append((self.cur, list(self.path)))
        if not args:
            self.cur = self.root
            self.path = []
            return

        raw = " ".join(args).strip()
        parts = self._normalize_path(raw)
        try:
            node = self._node_from_parts(parts)
        except Exception as e:
            self._nav_history.pop()  # undo push on failure
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
            s = re.sub(r"(?:\b[\w]+\.)+([A-Z]\w+)", r"\1", s)
            # Collapse "X | NoneType" / "NoneType | X" → "X?" for readability
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
                # Fallback: infer type from TypeCollection item_type when not in schema
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

        def _class_exists(name: str) -> bool:
            return name in SCHEMA.field_type_table

        def _fields_for_class(name: str) -> dict[str, Any]:
            return SCHEMA.get_class_fields(name) or {}

        def _do_here(_rest: list[str]) -> None:
            clsname = type(self.cur).__name__
            fields = _fields_for_class(clsname)
            if not fields:
                print(f"(no schema for {clsname})")
                return
            rows = [[fname, _typename(ftype)] for fname, ftype in sorted(fields.items())]
            _print_table(rows, ["field", "type"])

        def _do_class(_rest: list[str]) -> None:
            if not _rest:
                print("usage: schema class <ClassName>")
                return
            clsname = _rest[0]
            if not _class_exists(clsname):
                print(f"unknown class: {clsname}")
                return
            rows = [[fname, _typename(ftype)] for fname, ftype in sorted(_fields_for_class(clsname).items())]
            _print_table(rows, ["field", "type"])

        def _do_extras(_rest: list[str]) -> None:
            clsname = None
            mode = "--all"
            for a in _rest:
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
            rows = []
            for fname, ftype in sorted(extras.items()):
                src = "inherited" if fname in SCHEMA._inherited_extras.get(clsname, {}) else "direct"
                rows.append([fname, _typename(ftype), src])
            _print_table(rows, ["field", "type", "source"])

        def _do_find(_rest: list[str]) -> None:
            if not _rest:
                print("usage: schema find <field>")
                return
            target_field = _rest[0]
            rows = [
                [clsname, target_field, _typename(fields[target_field])]
                for clsname, fields in sorted(SCHEMA.field_type_table.items())
                if target_field in fields
            ]
            print("(no matches)") if not rows else _print_table(rows, ["class", "field", "type"])

        def _do_where(_rest: list[str]) -> None:
            if not _rest:
                print("usage: schema where <TypeExpr>")
                return
            needle = _rest[0]
            rows = [
                [clsname, fname, _typename(ftype)]
                for clsname, fields in sorted(SCHEMA.field_type_table.items())
                for fname, ftype in fields.items()
                if needle in _typename(ftype)
            ]
            print("(no matches)") if not rows else _print_table(rows, ["class", "field", "type"])

        def _do_bases(_rest: list[str]) -> None:
            if not _rest:
                print("usage: schema bases <ClassName>")
                return
            clsname = _rest[0]
            bases = SCHEMA._bases.get(clsname, [])
            subs = sorted(SCHEMA._subclasses.get(clsname, set()))
            print("Bases:", ", ".join(bases) if bases else "(none)")
            print("Subclasses:", ", ".join(subs) if subs else "(none)")

        def _do_toplevel(_rest: list[str]) -> None:
            tops = sorted(SCHEMA.get_toplevel().keys())
            if not tops:
                print("(no top-level classes)")
                return
            _print_table([[name] for name in tops], ["toplevel"])

        def _do_json(_rest: list[str]) -> None:
            if _rest:
                clsname = _rest[0]
                if not _class_exists(clsname):
                    print(f"unknown class: {clsname}")
                    return
                payload = {clsname: {k: _typename(v) for k, v in _fields_for_class(clsname).items()}}
            else:
                payload = {k: {f: _typename(t) for f, t in v.items()} for k, v in SCHEMA.field_type_table.items()}
            print(json.dumps(payload, indent=2, ensure_ascii=False))

        def _do_diff(_rest: list[str]) -> None:
            target = self.cur
            if _rest:
                try:
                    target, _ = resolve_path(self.root, self.cur, _rest[0])
                except Exception as e:
                    print(f"! bad path: {e}")
                    return
            clsname = type(target).__name__
            fields = _fields_for_class(clsname)
            if not fields:
                print(f"(no schema for {clsname})")
                return
            runtime: dict[str, Any] = {
                k: v for k, v in vars(target).items()
                if not k.startswith("_") and not callable(v)
            } if hasattr(target, "__dict__") else {}
            rows: list[list[str]] = []
            for fname, stype in sorted(fields.items()):
                sname = _typename(stype)
                if hasattr(target, fname):
                    val = getattr(target, fname)
                    rtype = type(val).__name__ if val is not None else "NoneType"
                    ok = (rtype == sname) or (rtype == getattr(stype, "__name__", rtype))
                    rows.append([
                        fname,
                        sname if ok else f"{ANSI['yellow']}{sname}{ANSI['reset']}",
                        rtype if ok else f"{ANSI['red']}{rtype}{ANSI['reset']}",
                        "ok" if ok else f"{ANSI['red']}mismatch{ANSI['reset']}",
                    ])
                else:
                    rows.append([fname, sname, f"{ANSI['red']}(missing){ANSI['reset']}", f"{ANSI['red']}missing{ANSI['reset']}"])
            for k in sorted(k for k in runtime if k not in fields):
                rows.append([
                    f"{ANSI['cyan']}{k}{ANSI['reset']}",
                    f"{ANSI['cyan']}(extra){ANSI['reset']}",
                    type_of(runtime[k]),
                    f"{ANSI['cyan']}extra{ANSI['reset']}",
                ])
            _print_table(rows, ["field", "schema", "runtime", "status"])

        _SCHEMA_SUBS: dict[str, Any] = {
            "here":     _do_here,
            "class":    _do_class,
            "extras":   _do_extras,
            "find":     _do_find,
            "where":    _do_where,
            "bases":    _do_bases,
            "toplevel": _do_toplevel,
            "json":     _do_json,
            "diff":     _do_diff,
        }

        handler = _SCHEMA_SUBS.get(sub)
        if handler is None:
            print(f"unknown subcommand: {sub!r}. Try 'schema help'.")
            return
        handler(rest)

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

            def _strip_optional(tp: Any) -> Any:
                origin = get_origin(tp)
                if origin is None:
                    return tp
                args2 = [a for a in get_args(tp) if a is not type(None)]  # noqa: E721  # pylint: disable=unidiomatic-typecheck
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
            if self.root is None:
                print("No data loaded.")
                return None
            path = args[1].strip('"').strip("'")
            if not path.lower().endswith(".zip"):
                path += ".zip"
            with GedcomZip(path) as gz:
                arcname = gz.add_object_as_resource(self.root)
            if arcname:
                print(f"Written: {gz.path}  ({arcname})")
            else:
                print("Root is not a GedcomX object; nothing written.")
            return None
        if args[0] == "gx":
            js = orjson.dumps(
                self.root._to_dict(),
                option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE,
            )
            with open(args[1], "wb") as f:
                f.write(js)
        elif args[0] == "jsonl":
            if self.cur is not None:
                path = Path(args[1].strip('"').strip("'"))
                return write_jsonl(self.cur, Path(path))
            print("usage: write FORMAT[gx | adbg | jsonl] PATH")
            return None
        elif args[0] == "adbg":
            if args[1]:
                argo_graph_files_folder = Path(args[1])
                argo_graph_files_folder.mkdir(parents=True, exist_ok=True)
                print('Writing Argo Graph Files')
                if self.root is None:
                    print("No data loaded.")
                    return None
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
        return None

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
    """Run the command-line entry point."""
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
