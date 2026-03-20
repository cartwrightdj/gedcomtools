from __future__ import annotations

from typing import Any, ClassVar, List, Optional

from pydantic import Field

from .attribution import Attribution
from .conclusion import Conclusion, ConfidenceLevel
from .date import Date
from .evidence_reference import EvidenceReference
from .extensible_enum import ExtensibleEnum
from .identifier import IdentifierList
from .note import Note
from .place_reference import PlaceReference
from .resource import Resource
from .source_reference import SourceReference
from .subject import Subject
from .textvalue import TextValue


class GroupRoleType(ExtensibleEnum):
    pass


class GroupRole(Conclusion):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/GroupRole"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    person: Optional[Any] = None
    type: Optional[Any] = None  # GroupRoleType
    date: Optional[Date] = None
    details: Optional[str] = None


class Group(Subject):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/Group"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    names: List[TextValue] = Field(default_factory=list)
    date: Optional[Date] = None
    place: Optional[Any] = None  # PlaceReference
    roles: List[GroupRole] = Field(default_factory=list)
