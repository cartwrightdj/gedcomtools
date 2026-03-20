from __future__ import annotations
from typing import ClassVar, Optional

from .gx_base import GedcomXModel


class TextValue(GedcomXModel):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/TextValue"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    value: Optional[str] = None
    lang: Optional[str] = None

    def _append_to_value(self, value_to_append: str) -> None:
        if not isinstance(value_to_append, str):
            raise ValueError(f"Cannot append object of type {type(value_to_append)}.")
        if self.value is None:
            self.value = value_to_append
        else:
            self.value += " " + value_to_append

    def __str__(self) -> str:
        return f"{self.value} ({self.lang})"

    def _key(self) -> tuple[str, str]:
        return ((self.lang or "").casefold(), (self.value or "").strip())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TextValue):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return f"{cls}(value={self.value!r}, lang={self.lang!r})"
