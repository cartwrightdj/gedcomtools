from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Literal

"""
======================================================================
 Project: Gedcom-X
 File:    ExtensibleEnum.py
 Author:  David J. Cartwright
 Purpose: Create a class that can act like an enum but be extended by the user at runtime.

 Created: 2025-08-25
 Updated:
   - 2025-09-22: added ability to assign members normaly w/o register
   
======================================================================
"""


@dataclass(frozen=True, slots=True)
class _EnumItem:
    owner: type
    name: str
    value: Any
    def __repr__(self) -> str:  # e.g. Color.RED
        return f"{self.owner.__name__}.{self.name}"
    def __str__(self) -> str:
        return self.name

class _ExtEnumMeta(type):
    def __iter__(cls) -> Iterator[_EnumItem]:
        return iter(cls._members.values())

    def __contains__(cls, item: object) -> bool:
        return item in cls._members.values()

    # Color('RED') / Color(2) / Color(item)
    def __call__(cls, arg: Any, /, *, by: Literal["auto","name","value"]="auto") -> _EnumItem:
        if isinstance(arg, _EnumItem):
            if arg.owner is cls:
                return arg
            raise TypeError(f"{arg!r} is not a member of {cls.__name__}")
        if by == "name":
            return cls.get(str(arg))
        if by == "value":
            return cls.from_value(arg)
        if isinstance(arg, str) and arg in cls._members:
            return cls.get(arg)
        return cls.from_value(arg)

    # Allow: Color.red = "r" (register member); keep normal attrs intact
    def __setattr__(cls, name: str, value: Any) -> None:
        # allow normal internals & descriptors through unchanged
        if name.startswith("_") or name in {"__module__", "__doc__"}:
            return super().__setattr__(name, value)

        # If value is already an _EnumItem, install it directly (used by register)
        if isinstance(value, _EnumItem):
            if value.owner is not cls:
                raise TypeError(f"Cannot assign member from {value.owner.__name__} to {cls.__name__}")
            cls._members[name] = value
            return super().__setattr__(name, value)

        # If it's a descriptor/method/property/etc -> treat as normal attribute
        if isinstance(value, (staticmethod, classmethod, property)) or callable(value):
            return super().__setattr__(name, value)

        # Otherwise treat as member registration via assignment
        # (no uppercase requirement; any valid identifier works)
        item = cls.register(name, value)  # register will set the attribute (to _EnumItem)
        # Avoid double-setting here; register() already installed the attribute.
        return None

    # Optional: deleting a member removes it from the registry
    def __delattr__(cls, name: str) -> None:
        if name in cls._members:
            cls._members.pop(name, None)
        return super().__delattr__(name)

class ExtensibleEnum(metaclass=_ExtEnumMeta):
    """Runtime-extensible enum-like base."""
    _members: Dict[str, _EnumItem] = {}

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        cls._members = {}  # fresh registry per subclass

    @classmethod
    def __class_getitem__(cls, key: str) -> _EnumItem:  # Color['RED']
        return cls.get(key)

    @classmethod
    def register(cls, name: str, value: Any) -> _EnumItem:
        # Allow any identifier (no ALL-CAPS requirement)
        if not isinstance(name, str) or not name.isidentifier():
            raise ValueError("name must be a valid identifier")
        if name in cls._members:
            item = cls._members[name]
            if item.value != value:
                raise ValueError(f"name {name!r} already used with different value {item.value!r}")
            return item
        if any(m.value == value for m in cls._members.values()):
            raise ValueError(f"value {value!r} already used")
        item = _EnumItem(owner=cls, name=name, value=value)
        cls._members[name] = item
        # Set the attribute to the member object (triggers meta.__setattr__ branch for _EnumItem)
        super(_ExtEnumMeta, cls).__setattr__(name, item)
        return item

    @classmethod
    def names(cls) -> list[str]:
        return list(cls._members.keys())

    @classmethod
    def items(cls) -> list[_EnumItem]:
        return list(cls._members.values())

    @classmethod
    def get(cls, name: str) -> _EnumItem:
        try:
            return cls._members[name]
        except KeyError as e:
            raise KeyError(f"{cls.__name__} has no member named {name!r}") from e

    @classmethod
    def from_value(cls, value: Any) -> _EnumItem:
        for m in cls._members.values():
            if m.value == value:
                return m
        raise KeyError(f"{cls.__name__} has no member with value {value!r}")
