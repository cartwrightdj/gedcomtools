from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from collections.abc import Iterator
import json
import secrets
import string
import json

"""
======================================================================
 Project: Gedcom-X
 File:    identifier.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-03: _from_json_ refactor 
   - 2025-09-04: fixe identifier and identifieList json deserialization
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .extensible_enum import _EnumItem
from .resource import Resource
from .schemas import extensible, SCHEMA
from .uri import URI
from .extensible_enum import ExtensibleEnum
from ..logging_hub import hub, logging
"""
======================================================================
Logging
======================================================================
"""
log = logging.getLogger("gedcomx")
serial_log = "gedcomx.serialization"
#=====================================================================

def make_uid(length: int = 10, alphabet: str = string.ascii_letters + string.digits) -> str:
    """
    Generate a cryptographically secure alphanumeric UID.

    Args:
        length: Number of characters to generate (must be > 0).
        alphabet: Characters to choose from (default: A-Za-z0-9).

    Returns:
        A random string of `length` characters from `alphabet`.
    """
    if length <= 0:
        raise ValueError("length must be > 0")
    return ''.join(secrets.choice(alphabet) for _ in range(length)).upper()

class IdentifierType(ExtensibleEnum):
    pass

"""Enumeration of identifier types."""
IdentifierType.register("Primary", "http://gedcomx.org/Primary")
IdentifierType.register("Authority", "http://gedcomx.org/Authority")            
IdentifierType.register("Deprecated", "http://gedcomx.org/Deprecated")
IdentifierType.register("Persistent", "http://gedcomx.org/Persistent")
#IdentifierType.register("External", "https://gedcom.io/terms/v7/EXID")
IdentifierType.External = "https://gedcom.io/terms/v7/EXID"
IdentifierType.register("Other", "user provided")
IdentifierType.register("ChildAndParentsRelationship","http://familysearch.org/v1/ChildAndParentsRelationship")
IdentifierType.register("FamilySearchId", "https://gedcom.io/terms/v5/FSID")

@extensible()    
class Identifier:
    identifier = 'http://gedcomx.org/v1/Identifier'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self, value: Optional[List[URI]], type: Optional[IdentifierType] = IdentifierType.Primary) -> None: # type: ignore
        if not isinstance(value,list):
            value = [value] if value else []
        self.type = type
        self.values = value if value else []
    
    @property
    def _as_dict_(self):
        from .serialization import Serialization
        type_as_dict = {}
        if self.values:
            type_as_dict["value"] = None # [v._as_dict_ for v in self.values]
        if self.type:
            type_as_dict["type"] = None #getattr(self.type, "value", self.type)  # type: ignore[attr-defined]

        return Serialization._serialize_dict(type_as_dict)

    @classmethod
    def _from_json_(cls, data: Dict[str, Any]) -> Union[Identifier, None]:
        """
        Construct an Identifier from a dict parsed from JSON.
        """
        
        for key in data.keys():
            type = key
            value = data[key]
        uri_obj: Optional[Resource] = None
        # TODO DO THIS BETTER

        # Parse type
        raw_type = data.get('type')
        if raw_type is None:
            return None
        id_type: Union[_EnumItem,None] = IdentifierType(raw_type) if raw_type else None
        return cls(value=value, type=id_type) # type: ignore

@extensible()
class IdentifierList:
    def __init__(self,
                 identifiers: Optional[dict[str, list[URI]]] = None, **kargs) -> None:
        # maps identifier-type (e.g., str or IdentifierType.value) -> list of values
        self.identifiers: dict[str, list[URI]] = identifiers if identifiers else {}
        for arg in kargs.keys():
            self.add_identifier(Identifier(type=arg,values=kargs[arg]))

    # -------------------- hashing/uniqueness helpers --------------------
    def make_hashable(self, obj):
        """Convert any object into a hashable representation."""
        if isinstance(obj, dict):
            return tuple(sorted((k, self.make_hashable(v)) for k, v in obj.items()))
        elif isinstance(obj, (list, set, tuple)):
            return tuple(self.make_hashable(i) for i in obj)
        elif isinstance(obj, URI):
            return obj._as_dict_
        elif hasattr(obj, "_as_dict_"):
            d = getattr(obj, "_as_dict_")
            return tuple(sorted((k, self.make_hashable(v)) for k, v in d.items()))
        else:
            return obj

    def unique_list(self, items):
        """Return a list without duplicates, preserving order."""
        seen = set()
        result = []
        for item in items:
            h = self.make_hashable(item)
            if h not in seen:
                seen.add(h)
                result.append(item)
        return result

    # -------------------- public mutation API --------------------
    def append(self, identifier: "Identifier"):
        if isinstance(identifier, Identifier):
            self.add_identifier(identifier)
        else:
            raise ValueError("append expects an Identifier instance")
    
    def add_identifier(self, identifier: "Identifier"):
        """Add/merge an Identifier (which may contain multiple values)."""
        if not (identifier and isinstance(identifier, Identifier) and identifier.type):
            raise ValueError("The 'identifier' must be a valid Identifier instance with a type.")
        if not isinstance(identifier.type,_EnumItem):
            raise ValueError
        key = identifier.type.value if hasattr(identifier.type, "value") else str(identifier.type)
        existing = self.identifiers.get(key, [])
        merged = self.unique_list(list(existing) + list(identifier.values))
        self.identifiers[key] = merged

    # -------------------- queries --------------------
    def contains(self, identifier: "Identifier") -> bool:
        """Return True if any of the identifier's values are present under that type."""
        if not (identifier and isinstance(identifier, Identifier) and identifier.type):
            return False
        key = identifier.type.value if hasattr(identifier.type, "value") else str(identifier.type)
        if key not in self.identifiers:
            return False
        pool = self.identifiers[key]
        # treat values as a list on the incoming Identifier
        for v in getattr(identifier, "values", []):
            if any(self.make_hashable(v) == self.make_hashable(p) for p in pool):
                return True
        return False

    # -------------------- mapping-like dunder methods --------------------
    def __iter__(self) -> Iterator[str]:
        """Iterate over identifier *types* (keys)."""
        return iter(self.identifiers)

    def __len__(self) -> int:
        """Number of identifier types (keys)."""
        return len(self.identifiers)

    def __contains__(self, key) -> bool:
        """Check if a type key exists (accepts str or enum with .value)."""
        k = key.value if hasattr(key, "value") else str(key)
        return k in self.identifiers

    def __getitem__(self, key):
        """Lookup values by type key (accepts str or enum with .value)."""
        k = key.value if hasattr(key, "value") else str(key)
        return self.identifiers[k]

    # (optional) enable assignment via mapping syntax
    def __setitem__(self, key, values):
        """Set/replace the list of values for a type key."""
        k = key.value if hasattr(key, "value") else str(key)
        vals = values if isinstance(values, list) else [values]
        self.identifiers[k] = self.unique_list(vals)

    def __delitem__(self, key):
        k = key.value if hasattr(key, "value") else str(key)
        del self.identifiers[k]

    # -------------------- dict-style convenience --------------------
    def keys(self):
        return self.identifiers.keys()

    def values(self):
        return self.identifiers.values()

    def items(self):
        return self.identifiers.items()

    def iter_pairs(self) -> Iterator[tuple[str, object]]:
        """Flattened iterator over (type_key, value) pairs."""
        for k, vals in self.identifiers.items():
            for v in vals:
                yield (k, v)
    
    @classmethod
    def _from_json_(cls, data,context=None):
        if isinstance(data, dict):
            identifier_list = IdentifierList()
            for key, vals in data.items():
                vals = [URI(value=v) for v in vals]
                identifier_list.add_identifier(
                    Identifier(value=vals, type=IdentifierType(key))
                )
            return identifier_list if identifier_list != [] else None
        else:
            raise ValueError("Data must be a dict of identifiers.")

    @property
    def _serializer(self):
        type_as_dict = {}
        for k in self.identifiers.keys():
            type_as_dict[k] = [i._as_dict_ for i in self.identifiers[k]]
        return type_as_dict if type_as_dict != {} else None

    def __repr__(self) -> str:
        return f'{len(self.identifiers)} '.join(self.identifiers.keys())

    def __str__(self) -> str:
        return f'{len(self.identifiers)} '.join(self.identifiers.keys())

SCHEMA.field_type_table['IdentifierList'] = {
    "http://gedcomx.org/Primary":List[URI],
    "http://gedcomx.org/Authority":List[URI],            
    "http://gedcomx.org/Deprecated":List[URI],
    "http://gedcomx.org/Persistent":List[URI],
    "https://gedcom.io/terms/v7/EXID":List[URI],
    "user provided":List[URI],
    "http://familysearch.org/v1/ChildAndParentsRelationship":List[URI],
    "https://gedcom.io/terms/v5/FSID":List[URI],
}



