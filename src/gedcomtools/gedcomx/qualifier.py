"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/qualifier.py
 Author:  David J. Cartwright
 Purpose: GedcomX Qualifier model: key/value qualifier for conclusions and facts

 Created: 2025-08-25
 Updated:
======================================================================
"""
from __future__ import annotations
from typing import ClassVar, Optional

from .gx_base import GedcomXModel


class Qualifier(GedcomXModel):
    """Supplies additional details, annotations, or qualifying data to a data element.

    Attributes:
        name:  The name of the qualifier (RECOMMENDED: a constrained-vocabulary URI).
        value: Optional value; the name gives its semantic meaning.
    """

    identifier: ClassVar[str] = "http://gedcomx.org/v1/Qualifier"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"
    # Set to False in subclasses where name is intentionally absent (e.g. ConfidenceLevel)
    _name_required: ClassVar[bool] = True

    # name is required by the spec, but made Optional here so that
    # ConfidenceLevel (a special subclass) can be constructed with only value.
    name: Optional[str] = None
    value: Optional[str] = None

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        if self.__class__._name_required and self.name is None:
            result.warn("name", "Qualifier.name is required by the GedcomX spec")
        elif self.name is not None and not self.name.strip():
            result.warn("name", "Qualifier.name is blank")

    def _append(self, value: str) -> None:
        """Append *value* to the qualifier's value string, space-separated."""
        if value and isinstance(value, str):
            if self.value is None:
                self.value = value
            else:
                self.value += " " + value.strip()
        else:
            raise ValueError("value must be a string")

    def __str__(self) -> str:
        return f"{self.name}: {self.value}"
