"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/textvalue.py
 Author:  David J. Cartwright
 Purpose: GedcomX TextValue model: language-tagged text value

 Created: 2025-08-25
 Updated:
======================================================================
"""
from __future__ import annotations
from typing import ClassVar, Optional

from .gx_base import GedcomXModel


class TextValue(GedcomXModel):
    """A language-tagged text value, used for names, titles, and descriptions."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/TextValue"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    value: Optional[str] = None
    lang: Optional[str] = None

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_lang
        if self.value is None:
            result.warn("value", "TextValue has no value")
        elif not self.value.strip():
            result.warn("value", "TextValue.value is blank")
        check_lang(result, "lang", self.lang)

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
