from __future__ import annotations
# ======================================================================
#  Project: Gedcom-X
#  File:    gedcomx/serialization.py
#  Author:  David J. Cartwright
#  Purpose: Serialization and deserialization of Gedcom-X objects to/from JSON
#  Created: 2025-08-25
#  Updated: 2026-03-24 — restored Resource reference serialization; removed
#                         _GXModel short-circuit; added _RESOURCE_REF_FIELDS
#                         with MRO walk; fixed _normalize_field_type for unions;
#                         added _to_dict dispatch for GedcomX container
# ======================================================================

from collections.abc import Sized
from dataclasses import dataclass, field
import enum
from functools import lru_cache
from time import perf_counter
import types
from typing import (
    Any,
    Callable,
    Dict,
    ForwardRef,
    List,
    Set,
    Tuple,
    Union,
    get_args,
    get_origin,
)

# GEDCOM Module Types
from .gedcomx import TypeCollection
from .identifier import IdentifierList
from ..glog import get_logger, hub
from .resource import Resource
from .gx_base import GedcomXModel as _GXModel


# Fields typed Optional[Any] during the pydantic migration that should still be
# serialized as resource references ({"resource": "#id"}).  Keyed by class name
# so the lookup is O(1) and import-free.  MRO is walked so subclass fields are
# covered automatically (see _get_resource_overrides).
_RESOURCE_REF_FIELDS: Dict[str, Set[str]] = {
    "Conclusion":        {"analysis"},
    "Relationship":      {"person1", "person2"},
    "EventRole":         {"person"},
    "GroupRole":         {"person"},
    "SourceReference":   {"description"},   # URI | SourceDescription → resource ref
    "SourceDescription": {"analysis"},       # Resource | Document → resource ref
}


def _normalize_field_type(tp: Any) -> Any:
    """Strip Optional, then prefer Resource over URI over first type in a Union."""
    # Strip Optional[X] → X
    origin = get_origin(tp)
    args = get_args(tp)
    if origin is Union and len(args) == 2 and type(None) in args:
        tp = next(a for a in args if a is not type(None))
        origin = get_origin(tp)
        args = get_args(tp)

    # Union[A, B, ...] → prefer Resource > URI > first
    if origin is Union:
        for preferred in (Resource,):
            if any(a is preferred for a in args):
                return preferred
        return args[0] if args else tp

    return tp


def _get_resource_overrides(cls) -> Set[str]:
    """Accumulate resource-reference field names across the full MRO."""
    overrides: Set[str] = set()
    for base in cls.__mro__:
        overrides |= _RESOURCE_REF_FIELDS.get(base.__name__, set())
    return overrides


def _get_class_fields(cls) -> dict:
    """Return {field_name: normalised_type} for pydantic GedcomXModel subclasses."""
    if not (isinstance(cls, type) and issubclass(cls, _GXModel)):
        return {}
    resource_overrides = _get_resource_overrides(cls)
    result = {}
    for k, v in cls.model_fields.items():
        if k in resource_overrides:
            result[k] = Resource
        else:
            result[k] = _normalize_field_type(v.annotation)
    return result


class _SchemaBridge:
    """SCHEMA compatibility shim: normalised field types from pydantic model_fields."""

    @staticmethod
    def get_class_fields(name_or_cls) -> dict | None:
        if isinstance(name_or_cls, type):
            f = _get_class_fields(name_or_cls)
            return f if f else None
        return None


SCHEMA = _SchemaBridge()
from .uri import URI
#======================================================================

log = get_logger(__name__)

serial_log = "gedcomx.serialization"
deserial_log = "gedcomx.deserialization"

@dataclass
class ResolveStats:
    # high-level counters
    total_refs: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    resolved_ok: int = 0
    resolved_fail: int = 0

    # breakdowns
    by_ref_type: Dict[str, int] = field(default_factory=dict)        # e.g. {"Resource": 12, "URI": 5}
    by_target_type: Dict[str, int] = field(default_factory=dict)     # e.g. {"Person": 8, "PlaceDescription": 2}

    # details
    failures: List[Dict[str, Any]] = field(default_factory=list)     # [{key, ref_type, path, reason}]
    attempts: List[Dict[str, Any]] = field(default_factory=list)     # [{key, ref_type, path, cache_hit}]
    resolver_time_ms: float = 0.0

    def _bump(self, d: Dict[str, int], k: str, n: int = 1) -> None:
        d[k] = d.get(k, 0) + n

    def note_attempt(self, *, ref_type: str, key: Any, path: Tuple[str, ...], cache_hit: bool) -> None:
        self.total_refs += 1
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        self._bump(self.by_ref_type, ref_type)
        self.attempts.append({"ref_type": ref_type, "key": key, "path": "/".join(path), "cache_hit": cache_hit})

    def note_success(self, *, target: Any) -> None:
        self.resolved_ok += 1
        self._bump(self.by_target_type, type(target).__name__)

    def note_failure(self, *, ref_type: str, key: Any, path: Tuple[str, ...], reason: str) -> None:
        self.resolved_fail += 1
        self.failures.append({"ref_type": ref_type, "key": key, "path": "/".join(path), "reason": reason})

    def note_resolver_time(self, dt_ms: float) -> None:
        self.resolver_time_ms += dt_ms

class Serialization:

    @staticmethod
    def serialize(obj):
        """Serialize a GedcomX object (or primitive) to a JSON-compatible dict/value.

        Returns:
            A JSON-serializable representation, or None if the input is None or empty.
        """
        if obj is not None:
            with hub.use(serial_log):
                if hasattr(obj, '_serializer'):
                    return obj._serializer

                if isinstance(obj, (str, int, float, bool, type(None))):
                    return obj
                if isinstance(obj, dict):
                    r = {k: Serialization.serialize(v) for k, v in obj.items()}
                    return r if r != {} else None
                if isinstance(obj, URI):
                    return obj.value
                if isinstance(obj, (list, tuple, set, TypeCollection)):
                    seq = obj if not isinstance(obj, TypeCollection) else list(obj)
                    if len(obj) == 0:
                        return None
                    return [Serialization.serialize(v) for v in seq]

                if isinstance(obj, enum.Enum):
                    return Serialization.serialize(obj.value)

                # Walk schema fields, handling Resource and URI specially.
                # Pydantic models fall through to model_dump only when no fields found.
                type_as_dict = {}
                fields = SCHEMA.get_class_fields(type(obj))
                if fields:
                    for field_name, type_ in fields.items():
                        if hasattr(obj, field_name):
                            if (v := getattr(obj, field_name)) is not None:
                                if type_ in (Resource, 'Resource'):
                                    res = Resource._of_object(target=v)
                                    type_as_dict[field_name] = Serialization.serialize(res.value)
                                elif type_ in (URI, 'URI'):
                                    uri = URI.model_validate({"target": v})
                                    type_as_dict[field_name] = uri.value
                                elif (sv := Serialization.serialize(v)) is not None:
                                    type_as_dict[field_name] = sv
                        else:
                            log.warning("{} missing expected field '{}'", type(obj).__name__, field_name)
                    return type_as_dict if type_as_dict else None

                # Fallback for pydantic models with no registered schema fields
                if isinstance(obj, _GXModel):
                    result = obj.model_dump(exclude_none=True, mode="json")
                    return result if result else None
                log.error("No SCHEMA fields found for {}", type(obj).__name__)
        return None

    @staticmethod
    def _serialize_dict(dict_to_serialize: dict) -> dict:
        """
        Walk a dict and serialize nested GedcomX objects to JSON-compatible values.
        - Uses `to_dict` on your objects when present
        - Recurse into dicts / lists / sets / tuples
        - Drops None and empty containers
        """
        def _serialize(value):
            if isinstance(value, (str, int, float, bool, type(None))):
                return value
            if (_fields := SCHEMA.get_class_fields(type(value))) is not None:
                # Expect your objects expose a snapshot via to_dict
                return Serialization.serialize(value)
            if isinstance(value, dict):
                return {k: _serialize(v) for k, v in value.items()}
            if isinstance(value, (list, tuple, set)):
                return [_serialize(v) for v in value]
            # Fallback: string representation
            return str(value)

        if isinstance(dict_to_serialize, dict):
            cooked = {
                k: _serialize(v)
                for k, v in dict_to_serialize.items()
                if v is not None
            }
            # prune empty containers (after serialization)
            return {
                k: v
                for k, v in cooked.items()
                if not (isinstance(v, Sized) and len(v) == 0)
            }
        return {}

    # --- tiny helpers --------------------------------------------------------

    @staticmethod
    def _as_concrete_class(T: Any) -> type | None:
        """If T resolves to an actual class type, return it; else None."""
        U = Serialization._resolve_forward(Serialization._unwrap(T))
        return U if isinstance(U, type) else None

    @staticmethod
    def _is_reference(x: Any) -> bool:
        return isinstance(x, (Resource, URI))

    @staticmethod
    def _has_reference_value(x: Any) -> bool:
        if Serialization._is_reference(x):
            return True
        if isinstance(x, (list, tuple, set)):
            return any(Serialization._has_reference_value(v) for v in x)
        if isinstance(x, dict):
            return any(Serialization._has_reference_value(v) for v in x.values())
        if isinstance(x, TypeCollection):
            return any(Serialization._has_reference_value(v) for v in x)
        return False

    @staticmethod
    def _resolve_structure(x: Any,
                        resolver: Callable[[Any], Any],
                        *,
                        _seen: set[int] | None = None,
                        _cache: dict[Any, Any] | None = None,
                        stats: ResolveStats | None = None,
                        _path: tuple[str, ...] = ()) -> Any:
        """
        Deep-resolve Resource/URI inside containers AND inside model objects' fields.
        If `stats` is provided, it will be populated with telemetry (counts, types, failures, timings).
        """
        with hub.use(deserial_log):
            if _seen is None:
                _seen = set()
            if _cache is None:
                _cache = {}

            oid = id(x)
            if oid in _seen:
                return x
            _seen.add(oid)

            # Direct reference?
            if Serialization._is_reference(x):
                ref_type = type(x).__name__
                key = getattr(x, "resourceId", None) or getattr(x, "resource", None) or getattr(x, "value", None)
                cache_hit = key in _cache
                if stats is not None:
                    stats.note_attempt(ref_type=ref_type, key=key, path=_path, cache_hit=cache_hit)

                if cache_hit:
                    return _cache[key]

                log.debug("looking up: {} from {} at {}", key, ref_type, "/".join(_path))

                t0 = perf_counter()
                try:
                    resolved = resolver(x)
                except Exception as e:
                    if stats is not None:
                        stats.note_failure(ref_type=ref_type, key=key, path=_path, reason=f"{type(e).__name__}: {e}")
                    raise
                finally:
                    if stats is not None:
                        stats.note_resolver_time((perf_counter() - t0) * 1000.0)

                if resolved is None:
                    if stats is not None:
                        stats.note_failure(ref_type=ref_type, key=key, path=_path, reason="resolver returned None")
                    return None

                if key is not None:
                    _cache[key] = resolved
                if stats is not None:
                    stats.note_success(target=resolved)
                return resolved

            # Containers
            if isinstance(x, list):
                return [Serialization._resolve_structure(v, resolver, _seen=_seen, _cache=_cache,
                                                        stats=stats, _path=(*_path, str(i)))
                        for i, v in enumerate(x)]
            if isinstance(x, tuple):
                return tuple(Serialization._resolve_structure(v, resolver, _seen=_seen, _cache=_cache,
                                                            stats=stats, _path=(*_path, str(i)))
                            for i, v in enumerate(x))
            if isinstance(x, set):
                return {Serialization._resolve_structure(v, resolver, _seen=_seen, _cache=_cache,
                                                        stats=stats, _path=(*_path, str(i)))
                        for i, v in enumerate(x)}
            if isinstance(x, dict):
                return {k: Serialization._resolve_structure(v, resolver, _seen=_seen, _cache=_cache,
                                                            stats=stats, _path=(*_path, str(k)))
                        for k, v in x.items()}

            # TypeCollection (preserve wrapper)
            if isinstance(x, TypeCollection):
                elem_cls = getattr(x, "item_type", None)
                new_coll = TypeCollection(elem_cls) if elem_cls else None
                for i, v in enumerate(x):
                    nv = Serialization._resolve_structure(v, resolver, _seen=_seen, _cache=_cache,
                                                        stats=stats, _path=(*_path, str(i)))
                    if new_coll is not None:
                        new_coll.append(nv)
                return new_coll if new_coll is not None else [
                    Serialization._resolve_structure(v, resolver, _seen=_seen, _cache=_cache,
                                                    stats=stats, _path=(*_path, str(i)))
                    for i, v in enumerate(x)
                ]

            # Model objects registered in SCHEMA: walk their fields
            fields = SCHEMA.get_class_fields(type(x)) or {}
            if fields:
                for fname in fields.keys():
                    if not hasattr(x, fname):
                        continue
                    cur = getattr(x, fname)
                    new = Serialization._resolve_structure(cur, resolver, _seen=_seen, _cache=_cache,
                                                        stats=stats, _path=(*_path, fname))
                    if new is not cur:
                        try:
                            setattr(x, fname, new)
                        except Exception:
                            log.debug("'{}' field '{}' did not resolve", type(x).__name__, fname)
                return x

            # Anything else: leave as-is
            return x

    @classmethod
    def apply_resource_resolutions(cls, inst: Any, resolver: Callable[[Any], Any]) -> None:
        """Resolve any queued attribute setters stored on the instance."""
        setters: List[Callable[[Any, Any], None]] = getattr(inst, "_resource_setters", [])
        for set_fn in setters:
            set_fn(inst, resolver)
        # Optional: clear after applying
        inst._resource_setters = []

    # --- your deserialize with setters --------------------------------------

    @classmethod
    def deserialize(
        cls,
        data: dict[str, Any],
        class_type: type,
        *,
        resolver: Callable[[Any], Any] | None = None,
        queue_setters: bool = True,
    ) -> Any:
        """Deserialize a JSON dict into an instance of ``class_type``.

        Args:
            data: A JSON-compatible dict whose keys correspond to ``class_type`` fields.
            class_type: The target class to instantiate.
            resolver: Optional callable to immediately resolve Resource/URI references.
            queue_setters: If True, unresolved references are stored as lazy setters
                on the instance for deferred resolution.

        Returns:
            An instance of ``class_type`` populated from ``data``.
        """
        with hub.use(deserial_log):
            t0 = perf_counter()

            # Pydantic models: delegate to model_validate
            if isinstance(class_type, type) and issubclass(class_type, _GXModel):
                inst = class_type.model_validate(data)
                log.debug("deserialize[{}]: pydantic model_validate %.3f ms",
                          class_type.__name__, (perf_counter() - t0) * 1000)
                return inst

            # Plain classes with a from_dict classmethod (e.g. GedcomX)
            if isinstance(data, dict) and hasattr(class_type, "from_dict"):
                inst = class_type.from_dict(data)
                log.debug("deserialize[{}]: from_dict %.3f ms",
                          class_type.__name__, (perf_counter() - t0) * 1000)
                return inst

            class_fields = SCHEMA.get_class_fields(class_type) or {}

            result: dict[str, Any] = {}
            pending: list[tuple[str, Any]] = []

            # bind hot callables
            _coerce = cls._coerce_value
            _hasres = cls._has_reference_value

            for name, typ in class_fields.items():
                raw = data.get(name, None)
                if raw is None:
                    continue
                try:
                    val = _coerce(raw, typ)
                except Exception:
                    log.exception("deserialize[{}]: coercion failed for field '{}' raw={!r}",
                                class_type.__name__, name, raw)
                    raise
                result[name] = val
                if _hasres(val):
                    pending.append((name, val))

            # instantiate
            try:
                inst = class_type(**result)
            except TypeError:
                log.exception("deserialize[{}]: __init__ failed with kwargs={}",
                            class_type.__name__, list(result.keys()))
                raise

            # resolve now (optional)
            if resolver and pending:
                for attr, raw in pending:
                    try:
                        resolved = cls._resolve_structure(raw, resolver)  # deep-resolve Resources
                        setattr(inst, attr, resolved)
                    except Exception:
                        log.exception("deserialize[{}]: resolver failed for '{}'", class_type.__name__, attr)
                        raise

            # queue setters as callables for later resolution
            if queue_setters and pending:
                existing = getattr(inst, "_resource_setters", [])
                fns = []
                for attr, raw in pending:
                    def _make(attr=attr, raw=raw):
                        def _set(obj, resolver_):
                            resolved = Serialization._resolve_structure(raw, resolver_)
                            setattr(obj, attr, resolved)
                        return _set
                    fns.append(_make())
                inst._resource_setters = [*existing, *fns]

            log.debug("deserialize[{}]: %.3f ms (resolved={}, queued={})",
                    class_type.__name__, (perf_counter() - t0) * 1000,
                    int(bool(resolver)) * len(pending), len(getattr(inst, "_resource_setters", [])))
            return inst


    @classmethod
    def _coerce_value(cls, value: Any, Typ: Any) -> Any:
        """Coerce `value` into `Typ` using the registry (recursively)."""
        # Enums
        if cls._is_enum_type(Typ):
            U = cls._resolve_forward(cls._unwrap(Typ))
            try:
                return U(value)
            except Exception:
                log.exception("coerce: failed to cast {} to {}", value, getattr(U, "__name__", U))
                return value

        # Unwrap typing once
        T = cls._resolve_forward(cls._unwrap(Typ))
        args = get_args(T)

        # Strings to Resource/URI
        if isinstance(value, str):
            if T is Resource:
                try:
                    return Resource(resourceId=value)
                except Exception:
                    log.exception("coerce: str->Resource failed for {!r}", value)
                    return value
            if T is URI:
                try:
                    return URI.from_url(value)
                except Exception:
                    log.exception("coerce: str->URI failed for {!r}", value)
                    return value
            return value

        # Dict to Resource
        if T is Resource and isinstance(value, dict):
            try:
                return Resource(resource=value.get("resource"), resourceId=value.get("resourceId"))
            except Exception:
                log.exception("coerce: dict->Resource failed for {!r}", value)
                return value

        # IdentifierList
        if T is IdentifierList:
            try:
                return IdentifierList.from_json(value)
            except Exception:
                log.exception("coerce: IdentifierList.from_json failed for {!r}", value)
                return value

        # Containers
        if cls._is_typecollection_annot(T):
            elem_t = cls._typecollection_elem_type(T)
            if not isinstance(value, (list, tuple, set, TypeCollection)) and value is not None:
                log.warning("coerce: TypeCollection expected list-like, got {}", type(value).__name__)
                return value
            try:
                src_iter = [] if value is None else (list(value) if not isinstance(value, list) else value)
                items = [cls._coerce_value(v, elem_t) for v in src_iter]
                elem_cls = cls._as_concrete_class(elem_t) or object
                coll = TypeCollection(elem_cls)
                coll.extend(items)
                return coll
            except Exception:
                log.exception("coerce: TypeCollection failed for {!r} elem_t={!r}", value, elem_t)
                return value

        if cls._is_list_like(T):
            elem_t = args[0] if args else Any
            try:
                return [cls._coerce_value(v, elem_t) for v in (value or [])]
            except Exception:
                log.exception("coerce: list failed for {!r} elem_t={!r}", value, elem_t)
                return value

        if cls._is_set_like(T):
            elem_t = args[0] if args else Any
            try:
                return {cls._coerce_value(v, elem_t) for v in (value or [])}
            except Exception:
                log.exception("coerce: set failed for {!r} elem_t={!r}", value, elem_t)
                return value

        if cls._is_tuple_like(T):
            try:
                if not value:
                    return tuple(value or ())
                if len(args) == 2 and args[1] is Ellipsis:
                    elem_t = args[0]
                    return tuple(cls._coerce_value(v, elem_t) for v in (value or ()))
                return tuple(cls._coerce_value(v, t) for v, t in zip(value, args))
            except Exception:
                log.exception("coerce: tuple failed for {!r} args={!r}", value, args)
                return value

        if cls._is_dict_like(T):
            k_t = args[0] if len(args) >= 1 else Any
            v_t = args[1] if len(args) >= 2 else Any
            try:
                return {
                    cls._coerce_value(k, k_t): cls._coerce_value(v, v_t)
                    for k, v in (value or {}).items()
                }
            except Exception:
                log.exception("coerce: dict failed for {!r} k_t={!r} v_t={!r}", value, k_t, v_t)
                return value

        # Objects via registry
        if isinstance(T, type) and isinstance(value, dict):
            fields = SCHEMA.get_class_fields(T) or {}
            if fields:
                kwargs = {}
                for fname, ftype in fields.items():
                    if fname in value:
                        resolved = cls._resolve_forward(cls._unwrap(ftype))
                        try:
                            kwargs[fname] = cls._coerce_value(value[fname], resolved)
                        except Exception:
                            log.exception("coerce: {}.{} field coercion failed", T.__name__, fname)
                try:
                    return T(**kwargs)
                except TypeError as e:
                    log.error("coerce: instantiate {} failed kwargs={}: {}", T.__name__, list(kwargs.keys()), e)
                    return kwargs

        # Already correct type?
        try:
            if isinstance(value, T):
                return value
        except TypeError:
            pass

        log.warning("coerce: fallback — returning original value={!r} (type={})", value, type(value).__name__)
        return value

    @classmethod
    def resolve_references_recursive(cls, root: Any, resolver: Callable[[Any], Any]) -> Any:
        """
        Walk the graph rooted at `root` and resolve all gedcomx.Resource
        instances in-place (or by replacing container elements).
        - Handles dict/list/tuple/set
        - Uses SCHEMA to traverse fields on your model objects
        - Applies any queued _resource_setters
        - Avoids cycles and reuses a small cache so the same Resource isn't
        resolved multiple times.
        Returns the (possibly same) root.
        """
        seen: set[int] = set()
        cache: Dict[Any, Any] = {}

        def resolve_resource(r: Any) -> Any:
            # Key by resourceId or value; fall back to id(r)
            key = getattr(r, "resourceId", None) or getattr(r, "value", None) or id(r)
            if key in cache:
                return cache[key]
            out = resolver(r)
            cache[key] = out
            return out

        def visit(node: Any) -> Any:
            oid = id(node)
            if oid in seen:
                return node
            seen.add(oid)

            # If node itself is a Resource → resolve
            if cls._is_reference(node):
                return resolve_resource(node)

            # Lists / Tuples / Sets
            if isinstance(node, list):
                for i, v in enumerate(list(node)):
                    node[i] = visit(v)
                return node
            if isinstance(node, tuple):
                return tuple(visit(v) for v in node)
            if isinstance(node, set):
                new = {visit(v) for v in list(node)}
                if new != node:
                    node.clear()
                    node.update(new)
                return node

            # Dict
            if isinstance(node, dict):
                for k, v in list(node.items()):
                    node[k] = visit(v)
                return node

            # Your model objects (registered in SCHEMA)
            fields = SCHEMA.get_class_fields(type(node)) or {}
            if fields:
                # Apply any queued per-instance setters first (lazy references)
                try:
                    cls.apply_resource_resolutions(node, resolve_resource)
                except Exception:
                    log.exception("resolve_references_recursive: apply_resource_resolutions failed for {!r}", node)
                # Walk fields according to SCHEMA
                for fname in fields.keys():
                    try:
                        if hasattr(node, fname):
                            cur = getattr(node, fname)
                            new = visit(cur)
                            if new is not cur:
                                setattr(node, fname, new)
                    except Exception:
                        log.exception("resolve_references_recursive: failed visiting {}.{}", type(node).__name__, fname)
                return node

            # Everything else: leave as-is
            return node

        return visit(root)


    # -------------------------- TYPE HELPERS --------------------------


    @staticmethod
    @lru_cache(maxsize=None)
    def _unwrap(T: Any) -> Any:
        origin = get_origin(T)
        if origin is None:
            return T
        if str(origin).endswith("Annotated"):
            args = get_args(T)
            return Serialization._unwrap(args[0]) if args else Any
        if origin in (Union, types.UnionType):
            args = tuple(a for a in get_args(T) if a is not type(None))  # pylint: disable=unidiomatic-typecheck
            return Serialization._unwrap(args[0]) if len(args) == 1 else tuple(Serialization._unwrap(a) for a in args)
        return T

    @staticmethod
    @lru_cache(maxsize=None)
    def _resolve_forward(T: Any) -> Any:
        if isinstance(T, ForwardRef):
            return globals().get(T.__forward_arg__, T)
        if isinstance(T, str):
            return globals().get(T, T)
        return T

    @staticmethod
    @lru_cache(maxsize=None)
    def _is_enum_type(T: Any) -> bool:
        U = Serialization._resolve_forward(Serialization._unwrap(T))
        try:
            return isinstance(U, type) and issubclass(U, enum.Enum)
        except TypeError:
            return False

    @staticmethod
    def _is_list_like(T: Any) -> bool:
        origin = get_origin(T) or T
        return origin in (list, List)

    @staticmethod
    def _is_set_like(T: Any) -> bool:
        origin = get_origin(T) or T
        return origin in (set, Set)

    @staticmethod
    def _is_tuple_like(T: Any) -> bool:
        origin = get_origin(T) or T
        return origin in (tuple, Tuple)

    @staticmethod
    def _is_dict_like(T: Any) -> bool:
        origin = get_origin(T) or T
        return origin in (dict, Dict)

    @staticmethod
    def _is_typecollection_annot(T: Any) -> bool:
        """Return True iff the annotation is TypeCollection[...] or TypeCollection."""
        from .gedcomx import TypeCollection as _TC  # class, not factory
        U = Serialization._resolve_forward(Serialization._unwrap(T))
        origin = get_origin(U)
        if origin is not None:
            return origin is _TC
        return U is _TC  # bare TypeCollection (no param)

    @staticmethod
    def _typecollection_elem_type(T: Any) -> Any:
        """Return the element type from TypeCollection[Elem], or Any if unspecified."""
        U = Serialization._resolve_forward(Serialization._unwrap(T))
        args = get_args(U)
        return args[0] if args else Any
