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

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if self.person is None:
            result.warn("person", "GroupRole has no person")
        else:
            from .resource import Resource
            from .person import Person
            check_instance(result, "person", self.person, Person, Resource)
        check_instance(result, "date", self.date, Date)


class Group(Subject):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/Group"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    names: List[TextValue] = Field(default_factory=list)
    date: Optional[Date] = None
    place: Optional[Any] = None  # PlaceReference
    roles: List[GroupRole] = Field(default_factory=list)

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if not self.names:
            result.warn("names", "Group has no names")
        check_instance(result, "date", self.date, Date)
        if self.place is not None:
            from .place_reference import PlaceReference
            check_instance(result, "place", self.place, PlaceReference)
        for i, role in enumerate(self.roles):
            check_instance(result, f"roles[{i}]", role, GroupRole)
