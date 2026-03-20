from __future__ import annotations

from enum import Enum
from typing import ClassVar, List, Optional

from .attribution import Attribution
from .conclusion import ConfidenceLevel, Conclusion
from .gx_base import GedcomXModel
from .note import Note
from .resource import Resource
from .source_reference import SourceReference


class GenderType(Enum):
    Male = "http://gedcomx.org/Male"
    Female = "http://gedcomx.org/Female"
    Unknown = "http://gedcomx.org/Unknown"
    Intersex = "http://gedcomx.org/Intersex"

    @property
    def description(self) -> str:
        descriptions = {
            GenderType.Male: "Male gender.",
            GenderType.Female: "Female gender.",
            GenderType.Unknown: "Unknown gender.",
            GenderType.Intersex: "Intersex (assignment at birth).",
        }
        return descriptions.get(self, "No description available.")


class Gender(Conclusion):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/Gender"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    type: Optional[GenderType] = None

    def __str__(self) -> str:
        parts = []
        if self.id:
            parts.append(f"id={self.id!r}")
        if self.type:
            try:
                parts.append(f"type={self.type.name}")
            except Exception:
                parts.append(f"type={self.type!r}")
        if self.lang:
            parts.append(f"lang={self.lang!r}")
        inner = ", ".join(parts) if parts else "no gender data"
        return f"Gender({inner})"

    def __repr__(self) -> str:
        return (
            f"Gender(id={self.id!r}, lang={self.lang!r}, "
            f"sources={self.sources!r}, notes={self.notes!r}, "
            f"confidence={self.confidence!r}, attribution={self.attribution!r}, "
            f"type={self.type!r})"
        )
