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

    # name is required by the spec, but made Optional here so that
    # ConfidenceLevel (a special subclass) can be constructed with only value.
    name: Optional[str] = None
    value: Optional[str] = None

    def _append(self, value: str) -> None:
        if value and isinstance(value, str):
            if self.value is None:
                self.value = value
            else:
                self.value += " " + value.strip()
        else:
            raise ValueError("value must be a string")

    def __str__(self) -> str:
        return f"{self.name}: {self.value}"
