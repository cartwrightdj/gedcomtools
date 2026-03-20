from __future__ import annotations

import re
from enum import Enum
from typing import Any, ClassVar, List, Optional, Union

from pydantic import Field

from .attribution import Attribution
from .conclusion import Conclusion, ConfidenceLevel
from .date import Date
from .document import Document
from .gx_base import GedcomXModel
from .note import Note
from .resource import Resource
from .source_reference import SourceReference


class NameType(Enum):
    BirthName = "http://gedcomx.org/BirthName"
    MarriedName = "http://gedcomx.org/MarriedName"
    AlsoKnownAs = "http://gedcomx.org/AlsoKnownAs"
    Nickname = "http://gedcomx.org/Nickname"
    AdoptiveName = "http://gedcomx.org/AdoptiveName"
    FormalName = "http://gedcomx.org/FormalName"
    ReligiousName = "http://gedcomx.org/ReligiousName"
    Other = "other"


class NamePartQualifier(Enum):
    Title = "http://gedcomx.org/Title"
    Primary = "http://gedcomx.org/Primary"
    Secondary = "http://gedcomx.org/Secondary"
    Middle = "http://gedcomx.org/Middle"
    Familiar = "http://gedcomx.org/Familiar"
    Religious = "http://gedcomx.org/Religious"
    Family = "http://gedcomx.org/Family"
    Maiden = "http://gedcomx.org/Maiden"
    Patronymic = "http://gedcomx.org/Patronymic"
    Matronymic = "http://gedcomx.org/Matronymic"
    Geographic = "http://gedcomx.org/Geographic"
    Occupational = "http://gedcomx.org/Occupational"
    Characteristic = "http://gedcomx.org/Characteristic"
    Postnom = "http://gedcomx.org/Postnom"
    Particle = "http://gedcomx.org/Particle"
    RootName = "http://gedcomx.org/RootName"


class NamePartType(Enum):
    Prefix = "http://gedcomx.org/Prefix"
    Suffix = "http://gedcomx.org/Suffix"
    Given = "http://gedcomx.org/Given"
    Surname = "http://gedcomx.org/Surname"


class NamePart(GedcomXModel):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/NamePart"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    type: Optional[NamePartType] = None
    value: Optional[str] = None
    qualifiers: List[NamePartQualifier] = Field(default_factory=list)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NamePart):
            return NotImplemented
        return (self.type == other.type and self.value == other.value
                and self.qualifiers == other.qualifiers)

    def __str__(self) -> str:
        parts = []
        if self.type is not None:
            parts.append(f"type={getattr(self.type, 'name', str(self.type))}")
        if self.value is not None:
            parts.append(f"value={self.value!r}")
        if self.qualifiers:
            parts.append(f"qualifiers={len(self.qualifiers)}")
        return f"NamePart({', '.join(parts)})" if parts else "NamePart()"


class NameForm(GedcomXModel):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/NameForm"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    lang: Optional[str] = None
    fullText: Optional[str] = None
    parts: List[NamePart] = Field(default_factory=list)


class Name(Conclusion):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/Name"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    type: Optional[NameType] = None
    nameForms: List[NameForm] = Field(default_factory=list)
    date: Optional[Date] = None

    @staticmethod
    def simple(text: str) -> "Name":
        """Create a Name from a plain string, parsing GEDCOM slash-notation."""
        if not text:
            return Name()
        name_parts: list = []
        slash_match = re.search(r"/([^/]*)/", text)
        if slash_match:
            surname_raw = slash_match.group(1).strip()
            before = text[: slash_match.start()].strip()
            after = text[slash_match.end() :].strip()
            if before:
                name_parts.append(NamePart(type=NamePartType.Given, value=before))
            if surname_raw:
                name_parts.append(NamePart(type=NamePartType.Surname, value=surname_raw))
            if after:
                name_parts.append(NamePart(type=NamePartType.Suffix, value=after))
            full_text = re.sub(r"\s+", " ", text.replace("/", "")).strip()
        else:
            full_text = text.strip()
            tokens = full_text.split()
            if len(tokens) >= 2:
                name_parts.append(NamePart(type=NamePartType.Given, value=" ".join(tokens[:-1])))
                name_parts.append(NamePart(type=NamePartType.Surname, value=tokens[-1]))
            elif tokens:
                name_parts.append(NamePart(type=NamePartType.Given, value=tokens[0]))
        name_form = NameForm(fullText=full_text, parts=name_parts)
        return Name(type=NameType.BirthName, nameForms=[name_form])

    def _add_name_part(self, namepart: NamePart) -> None:
        if namepart and isinstance(namepart, NamePart) and self.nameForms:
            for current in self.nameForms[0].parts:
                if namepart == current:
                    return
            self.nameForms[0].parts.append(namepart)

    def __str__(self) -> str:
        return f"Name(id={self.id}, type={self.type}, forms={len(self.nameForms)}, date={self.date})"

    def __repr__(self) -> str:
        return (
            f"Name(id={self.id!r}, lang={self.lang!r}, type={self.type!r}, "
            f"nameForms={self.nameForms!r}, date={self.date!r})"
        )


class QuickName:
    def __new__(cls, name: str) -> Name:  # type: ignore[misc]
        return Name(nameForms=[NameForm(fullText=name)])


def ensure_list(val: Any) -> list:
    if val is None:
        return []
    return val if isinstance(val, list) else [val]
