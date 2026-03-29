"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/group.py
 Author:  David J. Cartwright
 Purpose: GedcomX Group model: Group, GroupRole, and group membership

 Created: 2025-08-25
 Updated:
======================================================================
"""
from __future__ import annotations

from typing import ClassVar, List, Optional, Union

from pydantic import Field

from .conclusion import Conclusion
from .date import Date
from .extensible_enum import ExtensibleEnum
from .person import Person
from .place_reference import PlaceReference
from .resource import Resource
from .subject import Subject
from .textvalue import TextValue


class GroupRoleType(ExtensibleEnum):
    """Runtime-extensible enum of role types a person may hold within a group."""
    pass


class GroupRole(Conclusion):
    """A person's role within a group, with an optional type, date, and details."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/GroupRole"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    person: Optional[Union[Person, Resource]] = None
    type: Optional[GroupRoleType] = None
    date: Optional[Date] = None
    details: Optional[str] = None

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if self.person is None:
            result.warn("person", "GroupRole has no person")
        else:
            check_instance(result, "person", self.person, Person, Resource)
        check_instance(result, "date", self.date, Date)


class Group(Subject):
    """A named group of persons with optional date, place, and membership roles."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/Group"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    names: List[TextValue] = Field(default_factory=list)
    date: Optional[Date] = None
    place: Optional[PlaceReference] = None
    roles: List[GroupRole] = Field(default_factory=list)

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if not self.names:
            result.warn("names", "Group has no names")
        check_instance(result, "date", self.date, Date)
        if self.place is not None:
            check_instance(result, "place", self.place, PlaceReference)
        for i, role in enumerate(self.roles):
            check_instance(result, f"roles[{i}]", role, GroupRole)
