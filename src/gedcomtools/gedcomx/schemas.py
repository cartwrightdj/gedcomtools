"""Schema registry and type-introspection helpers for GedcomX models."""

from __future__ import annotations
# ======================================================================
#  Project: gedcomtools
#  File:    gedcomx/schemas.py
#  Author:  David J. Cartwright
#  Purpose: Central schema registry for field type metadata
#  Created: 2025-08-25
#  Updated: 2026-03-31 — fact_from_even_tag/event_from_even_tag moved to
#                         conversion.py; stubs retained for backward compat
#  Updated: 2026-04-03 — narrow bare except Exception to ImportError / (NameError, AttributeError, TypeError)
#  Updated: 2026-04-08 — pass full extension field types through to
#                         GedcomXModel.define_ext so generic model lists
#                         stay typed during deserialization
#  Updated: 2026-05-02 — merged parallel field-table maintenance into
#                         Pydantic model_fields; field_type_table, _bases,
#                         _subclasses, _inherited_extras are now computed
#                         properties; kept legacy helper exports for callers
# ======================================================================
import functools
import inspect
import operator
import threading
import types
from functools import reduce
from typing import Any, Callable, Dict, Iterable, Union, cast, get_args, get_origin, get_type_hints
try:
    from typing import Annotated  # type: ignore
except ImportError:  # pragma: no cover
    Annotated = None  # type: ignore

_UNION_ORIGINS = tuple(
    x for x in (Union, getattr(types, "UnionType", None)) if x is not None
)


def _gx_base_cls():
    """Return GedcomXModel if importable, else None."""
    try:
        from .gx_base import GedcomXModel
        return GedcomXModel
    except ImportError:
        return None


def _all_gx_subclasses(base) -> list:
    """Recursively collect all live subclasses of *base*."""
    result = []
    for sub in base.__subclasses__():
        result.append(sub)
        result.extend(_all_gx_subclasses(sub))
    return result


class Schema:
    """
    Central registry of fields for classes.

    For GedcomXModel subclasses all field information is derived directly
    from Pydantic's ``model_fields`` rather than maintained in a separate
    table.  Computed properties (``field_type_table``, ``_bases``,
    ``_subclasses``, ``_inherited_extras``) build their dicts on demand
    from the live class hierarchy.

    For non-Pydantic classes the old explicit-registration path is still
    available for backward compatibility (used by ``@extensible`` on plain
    classes).
    """

    def __init__(self) -> None:
        # Top-level class registry — no Pydantic equivalent.
        self._toplevel: Dict[str, Dict[str, Any]] = {}

        # Extras declared by plugins via register_extra().
        # For GedcomXModel subclasses this mirrors what define_ext() stores
        # in _ext_field_names; kept here so register_extra() callers can
        # still introspect what they registered.
        self._extras: Dict[str, Dict[str, Any]] = {}

        # Fields for non-Pydantic classes registered via register_class().
        # GedcomXModel subclasses are never stored here — they use model_fields.
        self._np_fields: Dict[str, Dict[str, Any]] = {}

        # Inheritance tracking for non-Pydantic classes only.
        self._np_bases: Dict[str, list] = {}
        self._np_subclasses: Dict[str, set] = {}
        self._np_extras: Dict[str, Dict[str, Any]] = {}
        self._np_inh_extras: Dict[str, Dict[str, Any]] = {}

        # String-name → class object cache (populated lazily).
        self._class_registry: Dict[str, type] = {}

        # Per-class field dict cache.  Invalidated by register_extra().
        # Keyed by the class object itself (not id, which can be reused).
        self._fields_cache: Dict[type, Dict[str, Any]] = {}
        self._fields_cache_lock = threading.Lock()

        # Cached merged table (np_fields + all GX classes).  Set to None to
        # invalidate; rebuilt lazily by field_type_table.
        self._gx_table_cache: Dict[str, Dict[str, Any]] | None = None

        # Optional bindings used by the normalization pipeline.
        self._uri_cls: type | None = None
        self._resource_cls: type | None = None

    # ──────────────────────────────
    # Bind concrete classes (optional, improves Union resolution)
    # ──────────────────────────────
    def set_uri_class(self, cls: type | None) -> None:
        """Register the URI class used by schema helpers."""
        self._uri_cls = cls

    def set_resource_class(self, cls: type | None) -> None:
        """Register the Resource class used by schema helpers."""
        self._resource_cls = cls

    # ──────────────────────────────
    # Internal helpers
    # ──────────────────────────────

    def _all_gx_classes(self) -> list[type]:
        """Return all currently imported GedcomXModel subclasses."""
        base = _gx_base_cls()
        return _all_gx_subclasses(base) if base else []

    def _resolve_class(self, cls_or_name: type | str) -> type | None:
        """Return the class object for *cls_or_name*, scanning GX subclasses if needed."""
        if isinstance(cls_or_name, type):
            self._class_registry[cls_or_name.__name__] = cls_or_name
            return cls_or_name
        name = str(cls_or_name)
        if name in self._class_registry:
            return self._class_registry[name]
        for cls in self._all_gx_classes():
            self._class_registry[cls.__name__] = cls
        return self._class_registry.get(name)

    def _pydantic_fields(self, cls: type) -> Dict[str, Any]:
        """Return {field_name: normalized_type} derived from cls.model_fields."""
        result = {}
        for k, fi in cls.model_fields.items():
            result[k] = self._normalize_field_type(fi.annotation)
        return result

    def _is_gx_model(self, cls: type) -> bool:
        base = _gx_base_cls()
        return base is not None and isinstance(cls, type) and issubclass(cls, base)

    # ──────────────────────────────
    # Computed properties (replace maintained dicts for GX models)
    # ──────────────────────────────

    @property
    def field_type_table(self) -> Dict[str, Dict[str, Any]]:
        """Field map for all known classes.

        Built once and cached; invalidated when register_extra() clears
        _fields_cache (e.g. after a plugin wires a new field).
        """
        if self._gx_table_cache is None:
            result = dict(self._np_fields)
            for cls in self._all_gx_classes():
                self._class_registry[cls.__name__] = cls
                result[cls.__name__] = self._cached_pydantic_fields(cls)
            self._gx_table_cache = result
        return self._gx_table_cache

    def _cached_pydantic_fields(self, cls: type) -> Dict[str, Any]:
        if cls not in self._fields_cache:
            with self._fields_cache_lock:
                if cls not in self._fields_cache:
                    self._fields_cache[cls] = self._pydantic_fields(cls)
        return self._fields_cache[cls]

    @property
    def _bases(self) -> Dict[str, list]:
        """Inheritance bases per class name, computed from Python MRO."""
        result = dict(self._np_bases)
        for cls in self._all_gx_classes():
            result[cls.__name__] = [b.__name__ for b in cls.__mro__[1:] if b is not object]
        return result

    @property
    def _subclasses(self) -> Dict[str, set]:
        """Subclass mapping per class name, computed from Python MRO."""
        result: Dict[str, set] = {k: set(v) for k, v in self._np_subclasses.items()}
        for cls in self._all_gx_classes():
            for b in cls.__mro__[1:]:
                if b is not object:
                    result.setdefault(b.__name__, set()).add(cls.__name__)
        return result

    @property
    def _inherited_extras(self) -> Dict[str, Dict[str, Any]]:
        """Extras that a class inherits but did not declare directly."""
        result = dict(self._np_inh_extras)
        base = _gx_base_cls()
        if not base:
            return result
        for cls in self._all_gx_classes():
            direct_names: set = vars(cls).get("_ext_field_names", set())
            all_names: set = set()
            for klass in cls.__mro__:
                all_names.update(vars(klass).get("_ext_field_names", set()))
            inh_names = all_names - direct_names
            if inh_names:
                result[cls.__name__] = {
                    name: self._normalize_field_type(cls.model_fields[name].annotation)
                    for name in inh_names
                    if name in cls.model_fields
                }
        return result

    # ──────────────────────────────
    # Public API
    # ──────────────────────────────

    def register_class(
        self,
        cls: type,
        *,
        mapping: Dict[str, Any] | None = None,
        include_bases: bool = True,
        use_annotations: bool = True,
        use_init: bool = True,
        overwrite: bool = False,
        ignore: set[str] | None = None,
        toplevel: bool = False,
        toplevel_meta: Dict[str, Any] | None = None,
    ) -> None:
        """Register a class.

        For GedcomXModel subclasses this simply records the class in the
        string-name registry and invalidates the per-class field cache —
        field information is always derived from ``model_fields``.

        For non-Pydantic classes the legacy annotation-introspection path
        is used to populate ``_np_fields``.
        """
        if self._is_gx_model(cls):
            self._class_registry[cls.__name__] = cls
            self._fields_cache.pop(cls, None)
            self._gx_table_cache = None
            if toplevel:
                self._toplevel[cls.__name__] = dict(toplevel_meta or {})
            return

        # ── Non-Pydantic path ─────────────────────────────────────────────
        cname = cls.__name__
        ignore = ignore or set()
        self._class_registry[cname] = cls

        def collect(c: type) -> Dict[str, Any]:
            d: Dict[str, Any] = {}
            if use_annotations:
                d.update(self._get_hints_from_class(c))
            if use_init and not d:
                d.update(self._get_hints_from_init(c))
            for k in list(d.keys()):
                if k in ignore or k.startswith("_"):
                    d.pop(k, None)
            for k, v in list(d.items()):
                d[k] = self._normalize_field_type(v)
            return d

        fields: Dict[str, Any] = {}
        classes = list(reversed(cls.mro())) if include_bases else [cls]
        for c in classes:
            if c is object:
                continue
            fields.update(collect(c))

        if mapping:
            for k, v in mapping.items():
                fields[k] = self._normalize_field_type(v)

        bases = [b.__name__ for b in cls.mro()[1:] if b is not object]
        self._np_bases[cname] = bases
        for b in bases:
            self._np_subclasses.setdefault(b, set()).add(cname)

        direct_extras = dict(self._np_extras.get(cname, {}))
        if direct_extras:
            for k, v in direct_extras.items():
                fields.setdefault(k, v)

        inherited: Dict[str, Any] = {}
        for bname in bases:
            for src in (self._np_extras.get(bname, {}), self._np_inh_extras.get(bname, {})):
                for k, v in src.items():
                    if k not in fields:
                        inherited.setdefault(k, v)
        if inherited:
            merged = self._np_inh_extras.get(cname, {})
            merged.update(inherited)
            self._np_inh_extras[cname] = merged
            fields.update(inherited)

        if not overwrite and cname in self._np_fields:
            self._np_fields[cname].update(fields)
        else:
            self._np_fields[cname] = fields

        if toplevel:
            self._toplevel[cname] = dict(toplevel_meta or {})

    def _propagate_extra_np(self, subclass_name: str, name: str, typ: Any, *, overwrite: bool) -> None:
        """Propagate a non-Pydantic extra to subclasses."""
        fields = self._np_fields.setdefault(subclass_name, {})
        if overwrite or name not in fields:
            fields[name] = typ
            inh = self._np_inh_extras.setdefault(subclass_name, {})
            inh[name] = typ
        for deeper in self._np_subclasses.get(subclass_name, set()):
            self._propagate_extra_np(deeper, name, typ, overwrite=overwrite)

    def register_extra(
        self,
        cls: type | str,
        name: str,
        typ: Any,
        *,
        overwrite: bool = False,
    ) -> None:
        """Register a single extra field (normalized) and propagate to subclasses.

        For GedcomXModel subclasses also calls ``define_ext()`` so the field
        becomes a proper model field (not just an ``extra``-captured value).
        Clears the per-class field cache so ``get_class_fields()`` reflects
        the new field immediately.
        """
        cname = self._cls_name(cls)
        nt = self._normalize_field_type(typ)
        self._extras.setdefault(cname, {})[name] = nt

        actual_cls = cls if isinstance(cls, type) else self._resolve_class(cls)

        if actual_cls is not None and hasattr(actual_cls, "define_ext"):
            # Pydantic model: wire up as a proper model field and clear caches.
            actual_cls.define_ext(name, typ=typ, overwrite=overwrite)
            # define_ext() rebuilds cls and all its subclasses, so invalidate
            # the entire field cache rather than hunting individual subclasses.
            self._fields_cache.clear()
            self._gx_table_cache = None
        else:
            # Non-Pydantic: maintain _np_fields manually.
            if actual_cls is not None:
                self._np_fields.setdefault(cname, {})[name] = nt
                self._np_extras.setdefault(cname, {})[name] = nt
                for sub in self._np_subclasses.get(cname, set()):
                    self._propagate_extra_np(sub, name, nt, overwrite=overwrite)

    def normalize_all(self) -> None:
        """Re-run normalization across all non-Pydantic registered fields."""
        for _, fields in self._np_fields.items():
            for k, v in list(fields.items()):
                fields[k] = self._normalize_field_type(v)

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get_class_fields(self, type_name: str | type) -> Dict[str, Any] | None:
        """Return normalised field map for *type_name*.

        For GedcomXModel subclasses derived from ``model_fields`` with a
        per-class cache.  For non-Pydantic classes returns the explicitly
        registered field map, if any.
        """
        cls = self._resolve_class(type_name)
        if cls is None:
            return None
        if self._is_gx_model(cls):
            return self._cached_pydantic_fields(cls)
        return self._np_fields.get(cls.__name__)

    def set_toplevel(self, cls: type, *, meta: Dict[str, Any] | None = None) -> None:
        """Register a class as a top-level GedcomX type."""
        self._toplevel[cls.__name__] = dict(meta or {})

    def is_toplevel(self, cls_or_name: type | str) -> bool:
        """Return whether the class is registered as top-level."""
        name = cls_or_name if isinstance(cls_or_name, str) else cls_or_name.__name__
        return name in self._toplevel

    def is_toplevel_obj(self, obj: Any) -> bool:
        """Like is_toplevel, but takes an arbitrary object and checks its class."""
        if isinstance(obj, (str, type)):
            return self.is_toplevel(obj)
        return self.is_toplevel(obj.__class__)

    def get_toplevel(self) -> Dict[str, Dict[str, Any]]:
        """Return the registered top-level classes."""
        return dict(self._toplevel)

    def get_extras(self, cls_or_name: type | str) -> Dict[str, Any]:
        """Direct extras declared on this class (not inherited)."""
        cls = self._resolve_class(cls_or_name)
        if cls is None:
            return {}
        if self._is_gx_model(cls):
            direct_names: set = vars(cls).get("_ext_field_names", set())
            return {
                name: self._normalize_field_type(cls.model_fields[name].annotation)
                for name in direct_names
                if name in cls.model_fields
            }
        cname = cls.__name__
        return dict(self._np_extras.get(cname, {}))

    def get_all_extras(self, cls_or_name: type | str) -> Dict[str, Any]:
        """Direct + inherited extras for this class."""
        cls = self._resolve_class(cls_or_name)
        if cls is None:
            return {}
        if self._is_gx_model(cls):
            all_names: set = set()
            for klass in cls.__mro__:
                all_names.update(vars(klass).get("_ext_field_names", set()))
            return {
                name: self._normalize_field_type(cls.model_fields[name].annotation)
                for name in all_names
                if name in cls.model_fields
            }
        cname = cls.__name__
        out: Dict[str, Any] = {}
        out.update(self._np_inh_extras.get(cname, {}))
        out.update(self._np_extras.get(cname, {}))
        return out

    # ── Utils ─────────────────────────────────────────────────────────────────

    def _cls_name(self, cls_or_name: type | str) -> str:
        return cls_or_name if isinstance(cls_or_name, str) else cls_or_name.__name__

    @property
    def json(self) -> dict[str, dict[str, str]]:
        """Return a JSON-compatible representation of the current data."""
        return schema_to_jsonable(self)

    # ──────────────────────────────
    # Normalization pipeline
    #   strip Optional -> prefer URI/Resource -> collapse unions
    #   (recurse into containers)
    # ──────────────────────────────
    def _normalize_field_type(self, tp: Any) -> Any:
        tp = self._strip_optional(tp)
        tp = self._prefer_uri_or_resource_or_first(tp)
        tp = self._collapse_unions(tp)
        return tp

    def _strip_optional(self, tp: Any) -> Any:
        if isinstance(tp, str):
            return self._strip_optional_str(tp)
        origin = get_origin(tp)
        args = get_args(tp)
        if Annotated is not None and origin is Annotated:
            return self._strip_optional(args[0])
        if origin in _UNION_ORIGINS:
            kept = tuple(a for a in args if a is not type(None))  # noqa: E721
            if not kept:
                return Any
            if len(kept) == 1:
                return self._strip_optional(kept[0])
            return self._rebuild_union_tuple(kept)
        if origin in (list, set, tuple, dict):
            sub = tuple(self._strip_optional(a) for a in args)
            return self._rebuild_param(origin, sub, fallback=tp)
        return tp

    def _prefer_uri_or_resource_or_first(self, tp: Any) -> Any:
        if isinstance(tp, str):
            if tp == "URI" and self._uri_cls:
                return self._uri_cls
            if tp == "Resource" and self._resource_cls:
                return self._resource_cls
            return self._prefer_str(tp)
        origin = get_origin(tp)
        args = get_args(tp)
        if Annotated is not None and origin is Annotated:
            return self._prefer_uri_or_resource_or_first(args[0])
        if origin in _UNION_ORIGINS:
            pick = None
            for a in args:
                name = a if isinstance(a, str) else getattr(a, "__name__", "")
                if (a is self._uri_cls) or (name == "URI"):
                    pick = self._uri_cls or a
                    break
            if pick is None:
                for a in args:
                    name = a if isinstance(a, str) else getattr(a, "__name__", "")
                    if (a is self._resource_cls) or (name == "Resource"):
                        pick = self._resource_cls or a
                        break
            if pick is None:
                pick = args[0]
            return self._prefer_uri_or_resource_or_first(pick)
        if origin in (list, set, tuple, dict):
            sub = tuple(self._prefer_uri_or_resource_or_first(a) for a in args)
            return self._rebuild_param(origin, sub, fallback=tp)
        return tp

    def _collapse_unions(self, tp: Any) -> Any:
        if isinstance(tp, str):
            return self._collapse_unions_str(tp)
        origin = get_origin(tp)
        args = get_args(tp)
        if Annotated is not None and origin is Annotated:
            return self._collapse_unions(args[0])
        if origin in _UNION_ORIGINS:
            return self._collapse_unions(args[0])
        if origin in (list, set, tuple, dict):
            sub = tuple(self._collapse_unions(a) for a in args)
            return self._rebuild_param(origin, sub, fallback=tp)
        return tp

    def _name_of(self, a: Any) -> str:
        if isinstance(a, str):
            return a.strip()
        if isinstance(a, type):
            return getattr(a, "__name__", str(a))
        return str(a).replace("typing.", "")

    def _rebuild_union_tuple(self, args: tuple[Any, ...]) -> Any:
        try:
            return reduce(operator.or_, args)
        except TypeError:
            return Union.__getitem__(args)  # type: ignore[attr-defined]

    def _rebuild_param(self, origin: Any, sub: tuple[Any, ...], *, fallback: Any) -> Any:
        try:
            return origin[sub] if sub else origin
        except TypeError:
            return fallback

    # ── String-based normalization (legacy forward-ref support) ───────────────

    def _strip_optional_str(self, s: str) -> str:
        s = s.strip().replace("typing.", "")
        while s.startswith("Optional[") and s.endswith("]"):
            s = s[len("Optional["):-1].strip()
        if s.startswith("Union[") and s.endswith("]"):
            inner = s[len("Union["):-1].strip()
            parts = [p for p in self._split_top_level(inner, ",") if p.strip() not in ("None", "NoneType", "")]
            return f"Union[{', '.join(parts)}]" if len(parts) > 1 else (parts[0].strip() if parts else "Any")
        if "|" in s:
            parts = [p.strip() for p in self._split_top_level(s, "|")]
            parts = [p for p in parts if p not in ("None", "NoneType", "")]
            return " | ".join(parts) if len(parts) > 1 else (parts[0] if parts else "Any")
        for head in ("List", "Set", "Tuple", "Dict", "Annotated"):
            if s.startswith(head + "[") and s.endswith("]"):
                inner = s[len(head) + 1:-1]
                if head == "Annotated":
                    items = self._split_top_level(inner, ",")
                    return self._strip_optional_str(items[0].strip()) if items else "Any"
                if head in ("List", "Set"):
                    return f"{head}[{self._strip_optional_str(inner)}]"
                if head == "Tuple":
                    elems = [self._strip_optional_str(p.strip()) for p in self._split_top_level(inner, ",")]
                    return f"Tuple[{', '.join(elems)}]"
                if head == "Dict":
                    kv = self._split_top_level(inner, ",")
                    k = self._strip_optional_str(kv[0].strip()) if kv else "Any"
                    v = self._strip_optional_str(kv[1].strip()) if len(kv) > 1 else "Any"
                    return f"Dict[{k}, {v}]"
        return s

    def _prefer_str(self, s: str) -> str:
        s = s.strip().replace("typing.", "")
        if s.startswith("Union[") and s.endswith("]"):
            inner = s[len("Union["):-1]
            parts = [p.strip() for p in self._split_top_level(inner, ",")]
            if "URI" in parts:
                return "URI"
            if "Resource" in parts:
                return "Resource"
            return parts[0] if parts else "Any"
        if "|" in s:
            parts = [p.strip() for p in self._split_top_level(s, "|")]
            if "URI" in parts:
                return "URI"
            if "Resource" in parts:
                return "Resource"
            return parts[0] if parts else "Any"
        for head in ("List", "Set", "Tuple", "Dict", "Annotated"):
            if s.startswith(head + "[") and s.endswith("]"):
                inner = s[len(head) + 1:-1]
                if head == "Annotated":
                    items = self._split_top_level(inner, ",")
                    return self._prefer_str(items[0].strip()) if items else "Any"
                if head in ("List", "Set"):
                    return f"{head}[{self._prefer_str(inner)}]"
                if head == "Tuple":
                    elems = [self._prefer_str(p.strip()) for p in self._split_top_level(inner, ",")]
                    return f"Tuple[{', '.join(elems)}]"
                if head == "Dict":
                    kv = self._split_top_level(inner, ",")
                    k = self._prefer_str(kv[0].strip()) if kv else "Any"
                    v = self._prefer_str(kv[1].strip()) if len(kv) > 1 else "Any"
                    return f"Dict[{k}, {v}]"
        return s

    def _collapse_unions_str(self, s: str) -> str:
        s = s.strip().replace("typing.", "")
        if s.startswith("Union[") and s.endswith("]"):
            inner = s[len("Union["):-1]
            parts = [p.strip() for p in self._split_top_level(inner, ",")]
            return parts[0] if parts else "Any"
        if "|" in s:
            parts = [p.strip() for p in self._split_top_level(s, "|")]
            return parts[0] if parts else "Any"
        for head in ("List", "Set", "Tuple", "Dict", "Annotated"):
            if s.startswith(head + "[") and s.endswith("]"):
                inner = s[len(head) + 1:-1]
                if head == "Annotated":
                    items = self._split_top_level(inner, ",")
                    return self._collapse_unions_str(items[0].strip()) if items else "Any"
                if head in ("List", "Set"):
                    return f"{head}[{self._collapse_unions_str(inner)}]"
                if head == "Tuple":
                    elems = [self._collapse_unions_str(p.strip()) for p in self._split_top_level(inner, ",")]
                    return f"Tuple[{', '.join(elems)}]"
                if head == "Dict":
                    kv = self._split_top_level(inner, ",")
                    k = self._collapse_unions_str(kv[0].strip()) if kv else "Any"
                    v = self._collapse_unions_str(kv[1].strip()) if len(kv) > 1 else "Any"
                    return f"Dict[{k}, {v}]"
        return s

    def _split_top_level(self, s: str, sep: str) -> list[str]:
        """Split *s* by single-char *sep* at top level (not inside brackets)."""
        out: list[str] = []
        buf: list[str] = []
        depth = 0
        for ch in s:
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
            if ch == sep and depth == 0:
                out.append("".join(buf).strip())
                buf = []
            else:
                buf.append(ch)
        out.append("".join(buf).strip())
        return [p for p in out if p != ""]

    # ── Annotation introspection (used only for non-Pydantic register_class) ──

    def _get_hints_from_class(self, cls: type) -> Dict[str, Any]:
        import sys as _sys
        module = _sys.modules.get(cls.__module__)
        gns = dict(module.__dict__) if module else {}
        if self._uri_cls is not None:
            gns.setdefault("URI", self._uri_cls)
        if self._resource_cls is not None:
            gns.setdefault("Resource", self._resource_cls)
        lns = dict(vars(cls))
        try:
            return get_type_hints(cls, include_extras=True, globalns=gns, localns=lns)
        except (NameError, AttributeError, TypeError):
            return dict(getattr(cls, "__annotations__", {}) or {})

    def _get_hints_from_init(self, cls: type) -> Dict[str, Any]:
        import sys as _sys
        fn = cls.__dict__.get("__init__", getattr(cls, "__init__", None))
        if not callable(fn):
            return {}
        module = _sys.modules.get(cls.__module__)
        gns = module.__dict__ if module else {}
        if self._uri_cls is not None:
            gns.setdefault("URI", self._uri_cls)
        if self._resource_cls is not None:
            gns.setdefault("Resource", self._resource_cls)
        lns = dict(vars(cls))
        try:
            hints = get_type_hints(fn, include_extras=True, globalns=gns, localns=lns)
        except (NameError, AttributeError, TypeError):
            hints = dict(getattr(fn, "__annotations__", {}) or {})
        hints.pop("return", None)
        hints.pop("self", None)
        sig = inspect.signature(fn)
        for pname, p in list(sig.parameters.items()):
            if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                hints.pop(pname, None)
        return hints


# ──────────────────────────────
# Stringification helpers (JSON dump)
# ──────────────────────────────
def type_repr(tp: Any) -> str:
    """Return a readable string representation of a type annotation."""
    if isinstance(tp, str):
        return tp
    origin = get_origin(tp)
    args = get_args(tp)
    if origin is None:
        if isinstance(tp, type):
            return tp.__name__
        return str(tp).replace("typing.", "")
    if origin in _UNION_ORIGINS:
        return " | ".join(type_repr(a) for a in args)
    if origin is list:
        return f"List[{type_repr(args[0])}]" if args else "List[Any]"
    if origin is set:
        return f"Set[{type_repr(args[0])}]" if args else "Set[Any]"
    if origin is tuple:
        return "Tuple[" + ", ".join(type_repr(a) for a in args) + "]" if args else "Tuple"
    if origin is dict:
        k, v = args or (Any, Any)
        return f"Dict[{type_repr(k)}, {type_repr(v)}]"
    return str(tp).replace("typing.", "")


def schema_to_jsonable(schema: Schema) -> dict[str, dict[str, str]]:
    """Convert schema metadata into JSON-serializable structures."""
    out: dict[str, dict[str, str]] = {}
    for cls_name in sorted(schema.field_type_table):
        fields = schema.field_type_table[cls_name]
        out[cls_name] = {fname: type_repr(fields[fname]) for fname in sorted(fields)}
    return out


def schema_class(
    mapping: Dict[str, Any] | None = None,
    *,
    include_bases: bool = True,
    use_annotations: bool = True,
    use_init: bool = True,
    overwrite: bool = False,
    ignore: set[str] | None = None,
    toplevel: bool = False,
    toplevel_meta: Dict[str, Any] | None = None,
):
    """Decorator to register a class with SCHEMA at import time."""
    def deco(cls: type):
        SCHEMA.register_class(
            cls,
            mapping=mapping,
            include_bases=include_bases,
            use_annotations=use_annotations,
            use_init=use_init,
            overwrite=overwrite,
            ignore=ignore,
            toplevel=toplevel,
            toplevel_meta=toplevel_meta,
        )
        return cls
    return deco


def bind_schema_property(
    cls: type,
    fget: Callable[..., Any],
    *,
    schema: Schema,
    name: str | None = None,
    typ: Any | None = None,
    fset: Callable[..., Any] | None = None,
    fdel: Callable[..., Any] | None = None,
    overwrite: bool = False,
    doc: str | None = None,
) -> property:
    """Bind a module-level getter as a property on *cls* and register it in *schema*."""
    prop_name = name or fget.__name__
    if typ is None:
        hints = get_type_hints(fget, include_extras=True)
        typ = hints.get("return", Any)
    p = property(fget, doc=doc or fget.__doc__)
    if fset is not None:
        p = p.setter(fset)
    if fdel is not None:
        p = p.deleter(fdel)
    setattr(cls, prop_name, p)
    schema.register_extra(cls, prop_name, typ, overwrite=overwrite)
    return p


def schema_property(
    *,
    schema: Schema,
    typ: Any | None = None,
    name: str | None = None,
    overwrite: bool = False,
):
    """Decorator: register a method as a schema-visible computed property."""
    def deco(fn: Callable[..., Any]):
        prop_name = name or fn.__name__

        def _register(owner: type):
            nonlocal typ
            if typ is None:
                hints = get_type_hints(fn, include_extras=True)
                typ = hints.get("return", Any)
            schema.register_extra(owner, prop_name, typ, overwrite=overwrite)

        p = property(fn)

        class _RegisteredProperty(property):
            def __set_name__(self, owner: type, attr_name: str) -> None:
                _register(owner)

        return _RegisteredProperty(p.fget, p.fset, p.fdel, p.__doc__)

    return deco


def schema_property_plugin(*, name: str | None = None, typ: Any | None = None):
    """Create a plugin that binds a computed schema property."""
    def deco(fget):
        meta = {"name": name or fget.__name__, "typ": typ, "fset": None, "fdel": None}
        setattr(fget, "__schema_prop__", meta)

        def setter(fset):
            meta["fset"] = fset
            return fget

        def deleter(fdel):
            meta["fdel"] = fdel
            return fget

        fget.setter = setter
        fget.deleter = deleter
        return fget
    return deco


def apply_schema_property(cls: type, fget, *, schema: Schema, overwrite: bool = False):
    """Apply a schema-bound computed property to a class."""
    meta = getattr(fget, "__schema_prop__", None)
    if meta is None:
        raise TypeError(
            f"{getattr(fget, '__name__', fget)!r} missing @schema_property_plugin metadata"
        )
    return bind_schema_property(
        cls,
        fget,
        schema=schema,
        name=meta["name"],
        typ=meta["typ"],
        fset=meta["fset"],
        fdel=meta["fdel"],
        overwrite=overwrite,
    )


# ──────────────────────────────
# accept_extras — wraps __init__ to absorb unknown kwargs (for plain classes)
# Note: GedcomXModel subclasses handle this via model_config extra='allow'.
# ──────────────────────────────
import threading as _threading


def accept_extras(*, stash_attr: str = "_extras",
                  allow_only=None):
    """Wrap a plain class __init__ to absorb unknown kwargs.

    Not needed for GedcomXModel subclasses (``extra='allow'`` handles it).
    """
    WRAPPED_FLAG = "__extras_wrapped__"
    lock = _threading.RLock()

    def _wrap_init(klass):
        with lock:
            if getattr(klass, WRAPPED_FLAG, False):
                return
            orig = klass.__init__
            sig = inspect.signature(orig)

            @functools.wraps(orig)
            def __init__(self, *args, **kwargs):
                known = {}
                for pname, _p in sig.parameters.items():
                    if pname == "self":
                        continue
                    if pname in kwargs:
                        known[pname] = kwargs.pop(pname)
                orig(self, *args, **known)
                extras = kwargs
                if allow_only is not None:
                    allowed = set(allow_only(self.__class__) or ())
                    extras = {k: v for k, v in extras.items() if k in allowed}
                if extras:
                    if hasattr(self, "__slots__"):
                        stash = getattr(self, stash_attr, None)
                        if stash is None:
                            object.__setattr__(self, stash_attr, {})
                            stash = getattr(self, stash_attr)
                        stash.update(extras)
                    else:
                        for k, v in extras.items():
                            setattr(self, k, v)

            klass.__init__ = __init__
            setattr(klass, WRAPPED_FLAG, True)

    def _decorator(klass):
        _wrap_init(klass)
        prev = getattr(klass, "__init_subclass__", None)
        prev_func = prev.__func__ if isinstance(prev, classmethod) else prev

        @classmethod
        def __init_subclass__(subcls, **kw):
            if prev_func:
                cast(Callable[..., Any], prev_func)(subcls, **kw)
            _wrap_init(subcls)

        klass.__init_subclass__ = __init_subclass__
        return klass

    return _decorator


def extensible(*, allow_only=None, **schema_kwargs):
    """Apply schema_class then accept_extras.  For plain (non-Pydantic) classes."""
    def deco(cls):
        cls = schema_class(**schema_kwargs)(cls)
        eff_allow = allow_only or (lambda c: set(SCHEMA.get_all_extras(c).keys()))
        cls = accept_extras(allow_only=eff_allow)(cls)
        return cls
    return deco


def extensible_dataclass(*d_args, allow_only=None, **schema_kwargs):
    """Decorate a dataclass so it participates in the legacy extension system."""
    from dataclasses import dataclass as _dc

    def deco(cls):
        cls = _dc(*d_args)(cls)
        cls = schema_class(**schema_kwargs)(cls)
        eff_allow = allow_only or (lambda c: set(SCHEMA.get_all_extras(c).keys()))
        return accept_extras(allow_only=eff_allow)(cls)

    return deco


class ExtrasAwareMeta(type):
    """Compatibility metaclass that accepts registered extension kwargs.

    New GedcomXModel subclasses use Pydantic ``extra='allow'`` instead.  This
    class remains for external plain-class callers that imported it from here.
    """

    def __call__(cls, *args, **kwargs):
        allow_fn = getattr(cls, "__extras_allow__", None)
        allowed = (
            set(cast(Iterable[str], allow_fn(cls)))
            if callable(allow_fn)
            else set(SCHEMA.get_all_extras(cls).keys())  # type: ignore[arg-type]
        )

        try:
            sig = inspect.signature(cls.__init__)
        except (TypeError, ValueError):
            sig = None

        known = {}
        accepts_varkw = False
        if sig:
            accepts_varkw = any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values())
            for pname, p in sig.parameters.items():
                if pname == "self" or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                    continue
                if pname in kwargs:
                    known[pname] = kwargs.pop(pname)

        call_kwargs = {**known, **(kwargs if accepts_varkw else {})}
        obj = super().__call__(*args, **call_kwargs)

        extras = {k: v for k, v in kwargs.items() if k in allowed}
        if extras:
            if hasattr(obj, "__slots__"):
                stash = getattr(obj, "_extras", None)
                if stash is None:
                    object.__setattr__(obj, "_extras", {})
                    stash = obj._extras
                stash.update(extras)
            else:
                for k, v in extras.items():
                    setattr(obj, k, v)
        return obj


# Singleton
SCHEMA = Schema()


# ---------------------------------------------------------------------------
# Backward-compat stubs: fact_from_even_tag / event_from_even_tag moved to
# conversion.py.  Kept here for any external callers.
# ---------------------------------------------------------------------------
def fact_from_even_tag(even_value):
    """Return the GedcomX fact type mapped from a GEDCOM EVEN tag."""
    from .tag_mappings import fact_from_even_tag as _fact_from_even_tag
    return _fact_from_even_tag(even_value)


def event_from_even_tag(even_value):
    """Return the GedcomX event type mapped from a GEDCOM EVEN tag."""
    from .tag_mappings import event_from_even_tag as _event_from_even_tag
    return _event_from_even_tag(even_value)
