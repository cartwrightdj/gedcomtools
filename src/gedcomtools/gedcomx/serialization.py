from __future__ import annotations

from collections.abc import Sized
from dataclasses import dataclass, field
import enum
from functools import lru_cache
from time import perf_counter
import types
from typing import (
    Annotated,
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

"""
======================================================================
 Project: Gedcom-X
 File:    Serialization.py
 Author:  David J. Cartwright
 Purpose: Serialization/Deserialization of gedcomx Objects

 Created: 2025-08-25
 Updated:
   - 2025-08-31: cleaned up imports and documentation
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .address import Address
from .agent import Agent
from .attribution import Attribution
from .conclusion import ConfidenceLevel
from .date import Date
from .document import Document, DocumentType, TextType
from .evidence_reference import EvidenceReference
from .event import Event, EventType, EventRole, EventRoleType
from .fact import Fact, FactType, FactQualifier
from .gedcomx import TypeCollection
from .gender import Gender, GenderType
from .identifier import IdentifierList, Identifier
from ..logging_hub import hub, ChannelConfig, logging
from .name import Name, NameType, NameForm, NamePart, NamePartType, NamePartQualifier
from .note import Note
from .online_account import OnlineAccount
from .person import Person
from .place_description import PlaceDescription
from .place_reference import PlaceReference
from .qualifier import Qualifier
from .relationship import Relationship, RelationshipType
from .resource import Resource
from .schemas  import SCHEMA
from .source_description import SourceDescription, ResourceType, SourceCitation, Coverage
from .source_reference import SourceReference
from .textvalue import TextValue
from .uri import URI
#======================================================================

log = logging.getLogger("gedcomx")

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
        if cache_hit: self.cache_hits += 1
        else:         self.cache_misses += 1
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
        if obj is not None:
            with hub.use(serial_log):
                if SCHEMA.is_toplevel(type(obj)):
                    if hub.logEnabled: log.debug("-" * 20)
                    if hub.logEnabled: log.debug(f"Serializing TOP LEVEL TYPE '{type(obj).__name__}'")
                else:
                    if hub.logEnabled: log.debug(f"Serializing type: '{type(obj).__name__}'")

                #if hub.logEnabled: log.debug(f"Serializing a '{type(obj).__name__}'")
                
                if hasattr(obj,'_serializer'):
                    if hub.logEnabled: log.debug(f"'%s' has a serializer, using it.",type(obj).__name__)
                    s = obj._serializer #TODO make this a callable/method?
                    
                    if hub.logEnabled: log.debug(f"Serializer returned '{type(s).__name__}' with value '{s}")
                    return s
                    
                if isinstance(obj, (str, int, float, bool, type(None))):
                    return obj
                if isinstance(obj, dict):
                    if hub.logEnabled: log.debug(f"'Value is a dict with value: {obj}")
                    r = {k: Serialization.serialize(v) for k, v in obj.items()}
                    return r if r != {} else None
                if isinstance(obj, URI):
                    return obj.value
                if isinstance(obj, (list, tuple, set)) or isinstance(obj, TypeCollection):
                    seq = obj if not isinstance(obj, TypeCollection) else list(obj)
                    if len(obj) == 0:
                        if hub.logEnabled: log.debug(f"'{type(obj).__name__}' is an empty (list, tuple, set)")
                        return None
                    return [Serialization.serialize(v) for v in seq]
                
                if isinstance(obj, enum.Enum): 
                    return Serialization.serialize(obj.value)
                
                #if hub.logEnabled: log.debug(f"Serializing a '{type(obj).__name__}'")
                type_as_dict = {}
                fields = SCHEMA.get_class_fields(type(obj).__name__)
                if fields:
                    for field_name, type_ in fields.items():
                        if hasattr(obj,field_name):
                            
                            if (v := getattr(obj,field_name)) is not None:
                                if hub.logEnabled: log.debug(f"Found {type(obj).__name__}.{field_name} with a '{type_}'")
                                if type_ == Resource or type_ == 'Resource':
                                    if type_ == 'Resource': 
                                        log.error(f"type_ was a {type(type_)}'")
                                    log.debug(f"<Resource> {type(obj).__name__}.{field_name} is a reference using a '{type_.__name__}'")
                                    res = Resource._of_object(target=v)
                                    type_as_dict[field_name] = Serialization.serialize(res.value)
                                elif type_ == URI or type_ == 'URI':
                                    if type_ == 'URI': 
                                        log.error(f"type_ was a {type(type_)}'")
                                    log.debug(f"<URI> {type(obj).__name__}.{field_name} is a reference using '{type_.__name__}'")
                                    uri = URI(target=v)
                                    type_as_dict[field_name] = uri.value
                                elif (sv := Serialization.serialize(v)) is not None:
                                    if hub.logEnabled: log.debug(f"{type(obj).__name__}.{field_name} was not a 'Resource' or 'URI', serialized normaly")
                                    type_as_dict[field_name] = sv
                            else:
                                if hub.logEnabled: log.warning(f"{type(obj).__name__}.{field_name}' was {type(v).__name__}")

                        else:
                            if hub.logEnabled: log.warning(f"{type(obj).__name__} did not have field '{field_name}'")
                    #if type_as_dict == {}: log.error(f"Serialized a '{type(obj).__name__}' with empty fields: '{fields}'")
                    #else: 
                        #if hub.logEnabled: log.debug(f"Serialized a '{type(obj).__name__}' with fields '{type_as_dict})'")
                    if hub.logEnabled: log.debug(f"<- Serialized a '%s'",type(obj).__name__)
                    #return Serialization._serialize_dict(type_as_dict)
                    return type_as_dict if type_as_dict != {} else None             
                else:
                    if hub.logEnabled: log.error(f"Could not find fields for {type(obj).__name__}")
        return None

    @staticmethod
    def _serialize_dict(dict_to_serialize: dict) -> dict:
        """
        Walk a dict and serialize nested GedcomX objects to JSON-compatible values.
        - Uses `_as_dict_` on your objects when present
        - Recurse into dicts / lists / sets / tuples
        - Drops None and empty containers
        """
        def _serialize(value):
            if isinstance(value, (str, int, float, bool, type(None))):
                return value
            if (fields := SCHEMA.get_class_fields(type(value).__name__)) is not None:
                # Expect your objects expose a snapshot via _as_dict_
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

                if hub.logEnabled:
                    log.debug("looking up: %r from %s at %s", key, ref_type, "/".join(_path))

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
            fields = SCHEMA.get_class_fields(type(x).__name__) or {}
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
                            if hub.logEnabled:
                                log.debug("'%s'.'%s' did not resolve", type(x).__name__, fname)
                return x

            # Anything else: leave as-is
            return x

    @classmethod
    def apply_resource_resolutions(cls, inst: Any, resolver: Callable[[Any], Any]) -> None:
        """Resolve any queued attribute setters stored on the instance."""
        setters: List[Callable[[Any], None]] = getattr(inst, "_resource_setters", [])
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
        
        with hub.use(deserial_log):
            t0 = perf_counter()
            class_fields = SCHEMA.get_class_fields(class_type.__name__)

            result: dict[str, Any] = {}
            pending: list[tuple[str, Any]] = []

            # bind hot callables
            _coerce = cls._coerce_value
            _hasres = cls._has_reference_value

            log.debug("deserialize[%s]: keys=%s", class_type.__name__, list(data.keys()))

            for name, typ in class_fields.items():
                log.debug("deserialize[%s]: field:%s of type%s", class_type.__name__, name, typ)
                raw = data.get(name, None)
                if raw is None:
                    continue
                try:
                    val = _coerce(raw, typ)
                except Exception:
                    log.exception("deserialize[%s]: coercion failed for field '%s' raw=%r",
                                class_type.__name__, name, raw)
                    raise
                result[name] = val
                if _hasres(val):
                    pending.append((name, val))

            # instantiate
            try:
                inst = class_type(**result)
            except TypeError:
                log.exception("deserialize[%s]: __init__ failed with kwargs=%s",
                            class_type.__name__, list(result.keys()))
                raise

            # resolve now (optional)
            if resolver and pending:
                for attr, raw in pending:
                    try:
                        resolved = cls._resolve_structure(raw, resolver)  # deep-resolve Resources
                        setattr(inst, attr, resolved)
                    except Exception:
                        log.exception("deserialize[%s]: resolver failed for '%s'", class_type.__name__, attr)
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

            log.debug("deserialize[%s]: done in %.3f ms (resolved=%d, queued=%d)",
                    class_type.__name__, (perf_counter() - t0) * 1000,
                    int(bool(resolver)) * len(pending), len(getattr(inst, "_resource_setters", [])))
            if isinstance(inst,Resource): assert False
            return inst

  
    @classmethod
    def _coerce_value(cls, value: Any, Typ: Any) -> Any:
        """Coerce `value` into `Typ` using the registry (recursively), with verbose logging."""
        log.debug("COERCE enter: value=%r (type=%s) -> Typ=%r", value, type(value).__name__, Typ)

        # Enums
        if cls._is_enum_type(Typ):
            U = cls._resolve_forward(cls._unwrap(Typ))
            log.debug("COERCE enum: casting %r to %s", value, getattr(U, "__name__", U))
            try:
                ret = U(value)
                log.debug("COERCE enum: success -> %r", ret)
                return ret
            except Exception:
                log.exception("COERCE enum: failed to cast %r to %s", value, U)
                return value

        # Unwrap typing once
        T = cls._resolve_forward(cls._unwrap(Typ))
        origin = get_origin(T) or T
        args = get_args(T)
        log.debug("COERCE typing: unwrapped Typ=%r -> T=%r, origin=%r, args=%r", Typ, T, origin, args)


        # Strings to Resource/URI
        if isinstance(value, str):
            if T is Resource:
                log.debug("COERCE str->Resource: %r", value)
                try:
                    ret = Resource(resourceId=value)
                    log.debug("COERCE str->Resource: built %r", ret)
                    return ret
                except Exception:
                    log.exception("COERCE str->Resource: failed for %r", value)
                    return value
            if T is URI:
                log.debug("COERCE str->URI: %r", value)
                try:
                    ret: Any = URI.from_url(value)
                    log.debug("COERCE str->URI: built %r", ret)
                    return ret
                except Exception:
                    log.exception("COERCE str->URI: failed for %r", value)
                    return value
            log.debug("COERCE str passthrough: target %r is not Resource/URI", T)
            return value

        # Dict to Resource
        if T is Resource and isinstance(value, dict):
            log.debug("COERCE dict->Resource: %r", value)
            try:
                ret = Resource(resource=value.get("resource"), resourceId=value.get("resourceId"))
                log.debug("COERCE dict->Resource: built %r", ret)
                return ret
            except Exception:
                log.exception("COERCE dict->Resource: failed for %r", value)
                return value

        # IdentifierList special
        
        if T is IdentifierList:
            log.debug("COERCE IdentifierList: %r", value)
            try:
                ret = IdentifierList._from_json_(value)
                log.debug("COERCE IdentifierList: built %r", ret)
                return ret
            except Exception:
                log.exception("COERCE IdentifierList: _from_json_ failed for %r", value)
                return value
        

        # Containers
        if cls._is_typecollection_annot(T):
            elem_t = cls._typecollection_elem_type(T)
            # Accept list/tuple/set/TypeCollection inputs; otherwise leave as-is
            if not isinstance(value, (list, tuple, set, TypeCollection)) and value is not None:
                log.warning("COERCE TypeCollection: expected list-like, got %r", type(value).__name__)
                return value
            try:
                # Coerce elements
                src_iter = [] if value is None else (list(value) if not isinstance(value, list) else value)
                items = [cls._coerce_value(v, elem_t) for v in src_iter]
                # Build the wrapper with the concrete element class if we can
                elem_cls = cls._as_concrete_class(elem_t) or object
                coll = TypeCollection(elem_cls)
                coll.extend(items)
                log.debug("COERCE TypeCollection<%s>: size=%d", getattr(elem_cls, "__name__", elem_cls), len(coll))
                return coll
            except Exception:
                log.exception("COERCE TypeCollection: failed value=%r elem_t=%r", value, elem_t)
                return value

        # B) Plain List[...] — leave as a plain list
        if cls._is_list_like(T):
            elem_t = args[0] if args else Any
            log.debug("COERCE list-like: len=%s, elem_t=%r", len(value or []), elem_t)
            try:
                ret = [cls._coerce_value(v, elem_t) for v in (value or [])]
                return ret
            except Exception:
                log.exception("COERCE list-like: failed for value=%r elem_t=%r", value, elem_t)
                return value

        if cls._is_set_like(T):
            elem_t = args[0] if args else Any
            log.debug("COERCE set-like: len=%s, elem_t=%r", len(value or []), elem_t)
            try:
                ret = {cls._coerce_value(v, elem_t) for v in (value or [])}
                log.debug("COERCE set-like: result size=%d", len(ret))
                return ret
            except Exception:
                log.exception("COERCE set-like: failed for value=%r elem_t=%r", value, elem_t)
                return value

        if cls._is_tuple_like(T):
            log.debug("COERCE tuple-like: value=%r, args=%r", value, args)
            try:
                if not value:
                    log.debug("COERCE tuple-like: empty/None -> ()")
                    return tuple(value or ())
                if len(args) == 2 and args[1] is Ellipsis:
                    elem_t = args[0]
                    ret = tuple(cls._coerce_value(v, elem_t) for v in (value or ()))
                    log.debug("COERCE tuple-like variadic: size=%d", len(ret))
                    return ret
                ret = tuple(cls._coerce_value(v, t) for v, t in zip(value, args))
                log.debug("COERCE tuple-like fixed: size=%d", len(ret))
                return ret
            except Exception:
                log.exception("COERCE tuple-like: failed for value=%r args=%r", value, args)
                return value

        if cls._is_dict_like(T):
            k_t = args[0] if len(args) >= 1 else Any
            v_t = args[1] if len(args) >= 2 else Any
            log.debug("COERCE dict-like: keys=%s, k_t=%r, v_t=%r", len((value or {}).keys()), k_t, v_t)
            try:
                ret = {
                    cls._coerce_value(k, k_t): cls._coerce_value(v, v_t)
                    for k, v in (value or {}).items()
                }
                log.debug("COERCE dict-like: result size=%d", len(ret))
                return ret
            except Exception:
                log.exception("COERCE dict-like: failed for value=%r k_t=%r v_t=%r", value, k_t, v_t)
                return value

        # Objects via registry
        if isinstance(T, type) and isinstance(value, dict):
            fields = SCHEMA.get_class_fields(T.__name__) or {}
            log.debug(
                "COERCE object: class=%s, input_keys=%s, registered_fields=%s",
                T.__name__, list(value.keys()), list(fields.keys())
            )
            if fields:
                kwargs = {}
                present = []
                for fname, ftype in fields.items():
                    if fname in value:
                        resolved = cls._resolve_forward(cls._unwrap(ftype))
                        log.debug("COERCE object.field: %s.%s -> %r, raw=%r", T.__name__, fname, resolved, value[fname])
                        try:
                            coerced = cls._coerce_value(value[fname], resolved)
                            kwargs[fname] = coerced
                            present.append(fname)
                            log.debug("COERCE object.field: %s.%s coerced -> %r", T.__name__, fname, coerced)
                        except Exception:
                            log.exception("COERCE object.field: %s.%s failed", T.__name__, fname)
                unknown = [k for k in value.keys() if k not in fields]
                if unknown:
                    log.debug("COERCE object: %s unknown keys ignored: %s", T.__name__, unknown)
                try:
                    log.debug("COERCE object: instantiate %s(**%s)", T.__name__, present)
                    ret = T(**kwargs)
                    log.debug("COERCE object: success -> %r", ret)
                    return ret
                except TypeError as e:
                    log.error("COERCE object: instantiate %s failed with kwargs=%s: %s", T.__name__, list(kwargs.keys()), e)
                    log.debug("COERCE object: returning partially coerced dict")
                    return kwargs

        # Already correct type?
        try:
            if isinstance(value, T):
                log.debug("COERCE passthrough: value already instance of %r", T)
                return value
        except TypeError:
            log.debug("COERCE isinstance not applicable: T=%r", T)

        log.warning("COERCE fallback: returning original value=%r (type=%s)", value, type(value).__name__)
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
            fields = SCHEMA.get_class_fields(type(node).__name__) or {}
            if fields:
                # Apply any queued per-instance setters first (lazy references)
                try:
                    cls.apply_resource_resolutions(node, resolve_resource)
                except Exception:
                    log.exception("resolve_references_recursive: apply_resource_resolutions failed for %r", node)
                # Walk fields according to SCHEMA
                for fname in fields.keys():
                    try:
                        if hasattr(node, fname):
                            cur = getattr(node, fname)
                            new = visit(cur)
                            if new is not cur:
                                setattr(node, fname, new)
                    except Exception:
                        log.exception("resolve_references_recursive: failed visiting %s.%s", type(node).__name__, fname)
                return node

            # Everything else: leave as-is
            return node

        return visit(root)

        
    # -------------------------- TYPE HELPERS --------------------------

    
    @lru_cache(maxsize=None)
    def _unwrap(T: Any) -> Any:
        origin = get_origin(T)
        if origin is None:
            return T
        if str(origin).endswith("Annotated"):
            args = get_args(T)
            return Serialization._unwrap(args[0]) if args else Any
        if origin in (Union, types.UnionType):
            args = tuple(a for a in get_args(T) if a is not type(None))
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

    
