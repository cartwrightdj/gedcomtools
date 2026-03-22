from __future__ import annotations

import secrets
import string
from collections.abc import Iterator
from typing import Any, ClassVar, Dict, List, Optional

from .extensible_enum import ExtensibleEnum, _EnumItem
from .gx_base import GedcomXModel
from .uri import URI


# ---------------------------------------------------------------------------
# make_uid
# ---------------------------------------------------------------------------

def make_uid(length: int = 10, alphabet: str = string.ascii_letters + string.digits) -> str:
    """Cryptographically-secure alphanumeric UID."""
    if length <= 0:
        raise ValueError("length must be > 0")
    return "".join(secrets.choice(alphabet) for _ in range(length)).upper()


# ---------------------------------------------------------------------------
# IdentifierType
# ---------------------------------------------------------------------------

class IdentifierType(ExtensibleEnum):
    pass


IdentifierType.register("Primary", "http://gedcomx.org/Primary")
IdentifierType.register("Authority", "http://gedcomx.org/Authority")
IdentifierType.register("Deprecated", "http://gedcomx.org/Deprecated")
IdentifierType.register("Persistent", "http://gedcomx.org/Persistent")
IdentifierType.External = "https://gedcom.io/terms/v7/EXID"
IdentifierType.register("Other", "user provided")
IdentifierType.register("ChildAndParentsRelationship", "http://familysearch.org/v1/ChildAndParentsRelationship")
IdentifierType.register("FamilySearchId", "https://gedcom.io/terms/v5/FSID")


# ---------------------------------------------------------------------------
# Identifier (pydantic model)
# ---------------------------------------------------------------------------

class Identifier(GedcomXModel):
    identifier_spec: ClassVar[str] = "http://gedcomx.org/v1/Identifier"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    type: Optional[IdentifierType] = None
    values: List[URI] = []

    def model_post_init(self, __context: object) -> None:
        # Normalise: value kwarg → values list
        raw = (self.model_extra or {}).get("value")
        if raw is not None and not self.values:
            if isinstance(raw, list):
                object.__setattr__(self, "values", raw)
            elif raw is not None:
                object.__setattr__(self, "values", [raw])
        if self.type is None:
            object.__setattr__(self, "type", IdentifierType.Primary)  # type: ignore[attr-defined]

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        if not self.values:
            result.error("values", "Identifier must have at least one value")
        for i, v in enumerate(self.values):
            if not isinstance(v, URI):
                result.error(f"values[{i}]", f"Expected URI, got {type(v).__name__}")


# ---------------------------------------------------------------------------
# IdentifierList  (NOT a pydantic model — dict-like container)
# Provides __get_pydantic_core_schema__ for use in pydantic field types.
# ---------------------------------------------------------------------------

class IdentifierList:
    """Maps identifier-type URI → list of URI values."""

    def __init__(
        self,
        identifiers: Optional[Dict[str, List[URI]]] = None,
        **kwargs: Any,
    ) -> None:
        self.identifiers: Dict[str, List[URI]] = identifiers if identifiers else {}
        for arg, val in kwargs.items():
            self.add_identifier(Identifier(type=IdentifierType(arg), values=val))  # type: ignore[arg-type]

    # ---- pydantic integration -------------------------------------------

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: Any) -> Any:
        from pydantic_core import core_schema

        def validate(v: Any) -> "IdentifierList":
            if isinstance(v, cls):
                return v
            if isinstance(v, dict):
                return cls(identifiers=v)
            return cls()

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: v._serializer or {},
                info_arg=False,
            ),
        )

    # ---- hashing helpers -----------------------------------------------

    def make_hashable(self, obj: Any) -> Any:
        if isinstance(obj, URI):
            return str(obj)  # urlunsplit — same result as model_dump(mode="json") but free
        if isinstance(obj, dict):
            return tuple(sorted((k, self.make_hashable(v)) for k, v in obj.items()))
        if isinstance(obj, (list, set, tuple)):
            return tuple(self.make_hashable(i) for i in obj)
        if hasattr(obj, "model_dump"):
            d = obj.model_dump(exclude_none=True, mode="json")
            if isinstance(d, dict):
                return tuple(sorted((k, self.make_hashable(v)) for k, v in d.items()))
            return self.make_hashable(d)
        if hasattr(obj, "__dict__"):
            return tuple(sorted((k, self.make_hashable(v)) for k, v in vars(obj).items()))
        return obj

    def unique_list(self, items: list) -> list:
        seen: set = set()
        result = []
        for item in items:
            h = self.make_hashable(item)
            if h not in seen:
                seen.add(h)
                result.append(item)
        return result

    # ---- public mutation API -------------------------------------------

    def append(self, identifier: Identifier) -> None:
        if isinstance(identifier, Identifier):
            self.add_identifier(identifier)
        else:
            raise ValueError("append expects an Identifier instance")

    def add_identifier(self, identifier: Identifier) -> None:
        if not (identifier and isinstance(identifier, Identifier) and identifier.type):
            raise ValueError("The 'identifier' must be a valid Identifier instance with a type.")
        if not isinstance(identifier.type, _EnumItem):
            raise ValueError("identifier.type must be an _EnumItem")
        key = identifier.type.value if hasattr(identifier.type, "value") else str(identifier.type)
        existing = self.identifiers.get(key, [])
        self.identifiers[key] = self.unique_list(existing + identifier.values)

    # ---- queries -------------------------------------------------------

    def contains(self, identifier: Identifier) -> bool:
        if not (identifier and isinstance(identifier, Identifier) and identifier.type):
            return False
        key = identifier.type.value if hasattr(identifier.type, "value") else str(identifier.type)  # type: ignore[attr-defined]
        if key not in self.identifiers:
            return False
        pool = self.identifiers[key]
        for v in getattr(identifier, "values", []):
            if any(self.make_hashable(v) == self.make_hashable(p) for p in pool):
                return True
        return False

    # ---- mapping-like interface ----------------------------------------

    def __iter__(self) -> Iterator[str]:
        return iter(self.identifiers)

    def __len__(self) -> int:
        return len(self.identifiers)

    def __contains__(self, key: Any) -> bool:
        k = key.value if hasattr(key, "value") else str(key)
        return k in self.identifiers

    def __getitem__(self, key: Any) -> List[URI]:
        k = key.value if hasattr(key, "value") else str(key)
        return self.identifiers[k]

    def __setitem__(self, key: Any, values: Any) -> None:
        k = key.value if hasattr(key, "value") else str(key)
        vals = values if isinstance(values, list) else [values]
        self.identifiers[k] = self.unique_list(vals)

    def __delitem__(self, key: Any) -> None:
        k = key.value if hasattr(key, "value") else str(key)
        del self.identifiers[k]

    def keys(self):
        return self.identifiers.keys()

    def values(self):
        return self.identifiers.values()

    def items(self):
        return self.identifiers.items()

    def iter_pairs(self) -> Iterator[tuple]:
        for k, vals in self.identifiers.items():
            for v in vals:
                yield (k, v)

    # ---- serialization -------------------------------------------------

    @property
    def _serializer(self) -> Optional[Dict[str, list]]:
        out: Dict[str, list] = {}
        for k, uris in self.identifiers.items():
            out[k] = [
                u.model_dump(exclude_none=True) if hasattr(u, "model_dump") else str(u)
                for u in uris
            ]
        return out if out else None

    @classmethod
    def from_json(cls, data: Any, _context: Any = None) -> "IdentifierList":
        if not isinstance(data, dict):
            raise ValueError("Data must be a dict of identifiers.")
        identifier_list = cls()
        for key, vals in data.items():
            uris = [URI.model_validate({"value": v}) if isinstance(v, str) else v for v in vals]
            identifier_list.add_identifier(
                Identifier(values=uris, type=IdentifierType(key))  # type: ignore[arg-type]
            )
        return identifier_list

    def __repr__(self) -> str:
        keys = ", ".join(self.identifiers.keys())
        return f"IdentifierList({len(self.identifiers)} types: [{keys}])"

    def __str__(self) -> str:
        return ", ".join(self.identifiers.keys()) or "IdentifierList(empty)"
