"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_relationship.py
 Purpose: FamilySearch GedcomX relationship extension types.

 Types: ChildAndParentsRelationship

 Specification:
   https://github.com/FamilySearch/gedcomx-fs/blob/master/specifications/
   fs-gedcomx-extension-specification.md

 Created: 2026-03-21
======================================================================
"""
from __future__ import annotations

import enum
from typing import Any, ClassVar, List, Optional

from pydantic import Field

from gedcomtools.gedcomx.resource import Resource
from gedcomtools.gedcomx.subject import Subject
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class FsRelationshipType(str, enum.Enum):
    """URI constants for relationship types supported by FamilySearch.

    Includes the standard GedcomX types plus FS-extended types.
    """

    AncestorDescendant = "http://gedcomx.org/AncestorDescendant"
    Couple = "http://gedcomx.org/Couple"
    EnslavedBy = "http://gedcomx.org/EnslavedBy"
    Godparent = "http://gedcomx.org/Godparent"
    ParentChild = "http://gedcomx.org/ParentChild"


class ChildAndParentsRelationship(Subject):
    """A FamilySearch-specific relationship linking a child to two parents.

    Extends :class:`~gedcomtools.gedcomx.subject.Subject` with parent and
    child references and parent-specific facts.

    Fields:
        parent1:      The parent1 of the child.
        parent2:      The parent2 of the child.
        child:        The child in the relationship.
        parent1Facts: Fact conclusions for parent1.
        parent2Facts: Fact conclusions for parent2.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/ChildAndParentsRelationship"

    parent1: Optional[Resource] = None
    parent2: Optional[Resource] = None
    child: Optional[Resource] = None
    parent1Facts: List[Any] = Field(default_factory=list)
    parent2Facts: List[Any] = Field(default_factory=list)


log.debug(
    "fs_types_relationship extension loaded — "
    "FsRelationshipType, ChildAndParentsRelationship defined"
)
