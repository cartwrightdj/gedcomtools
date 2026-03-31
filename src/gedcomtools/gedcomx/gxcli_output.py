#!/usr/bin/env python3
"""Standalone module-level helpers, constants, and output utilities for gxcli."""
from __future__ import annotations

# ======================================================================
#  Project: gedcomtools
#  File:    gxcli_output.py
#  Purpose: All standalone (non-Shell) functions, constants, and helpers
#           that were previously at the top of gxcli.py.
#  Created: 2026-03-31 — split from gxcli.py
# ======================================================================
import ast
import dataclasses
import inspect
import json
import logging
import os
import re
import sys
from dataclasses import fields as dataclass_fields, is_dataclass
from pathlib import Path
from typing import Any, Iterable, get_args, get_origin

import orjson

from gedcomtools.glog import setup_logging, get_logger, LoggerSpec
from gedcomtools.gedcomx import GedcomConverter, GedcomX
from gedcomtools.gedcomx.schemas import SCHEMA, type_repr
from gedcomtools.gedcomx.serialization import ResolveStats, Serialization
from gedcomtools.gedcomx.cli import objects_to_schema_table, write_jsonl
from gedcomtools.gedcomx.arango import make_arango_graph_files


SHELL_VERSION = '0.7.1'

# Logging is initialized in main() to avoid side effects on import.
_LOG_MGR = None


def init_logging(app_name: str = "gedcomtools"):
    """Initialize CLI logging configuration."""
    global _LOG_MGR  # pylint: disable=global-statement
    if _LOG_MGR is None:
        _LOG_MGR = setup_logging(app_name=app_name)
    return _LOG_MGR


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
try:
    from colorama import Fore, Style, init as _colorama_init

    _colorama_init()
    _RED, _RESET = Fore.RED, Style.RESET_ALL
    _ANSI_SUPPORTED = True
except ImportError:
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
    except (orjson.JSONDecodeError, ValueError, UnicodeDecodeError):
        if isinstance(b, (bytes, bytearray)):
            b = b.decode("utf-8")
        return json.loads(b)

def _json_dumps(obj: Any) -> str:
    plain = to_plain(obj, max_depth=64)
    try:
        return orjson.dumps(plain, option=orjson.OPT_INDENT_2).decode("utf-8")
    except (orjson.JSONEncodeError, TypeError, ValueError):
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
        except (AttributeError, TypeError):
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
        except (TypeError, AttributeError, ValueError):
            pass
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return obj.model_dump()
        except (TypeError, AttributeError):
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
    except (TypeError, AttributeError, RecursionError):
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
        except (TypeError, IndexError, KeyError):
            pass
    if hasattr(obj, "items"):
        try:
            items = obj.items() if callable(obj.items) else obj.items
            return list(items) if isinstance(items, Iterable) else None
        except (TypeError, AttributeError):
            pass
    if hasattr(obj, "__iter__"):
        try:
            return list(obj)
        except (TypeError, AttributeError):
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
        except (AttributeError, KeyError, TypeError):
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
    except (AttributeError, TypeError):
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
        except (OSError, json.JSONDecodeError):
            pass
    return cfg

def _save_settings(cfg: dict[str, Any]) -> None:
    try:
        _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_SETTINGS_PATH, "w") as _f:
            json.dump(cfg, _f, indent=2)
    except OSError as e:
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
