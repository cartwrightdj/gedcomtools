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
 Updated: 2026-04-08 — make ChildAndParentsRelationship a fully typed
                       Pydantic model with ResourceReference fields and
                       Fact-typed parent fact arrays
 Updated: 2026-04-08 — promote the FamilySearch docs name
                       `RelationshipType` to a first-class enum while
                       preserving `FsRelationshipType` as an alias
======================================================================
"""
from __future__ import annotations

import enum
from typing import ClassVar, List, Optional

from pydantic import Field

from gedcomtools.gedcomx.fact import Fact
from gedcomtools.gedcomx.resource import Resource
from gedcomtools.gedcomx.subject import Subject
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class RelationshipType(str, enum.Enum):
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
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    parent1: Optional[Resource] = None
    parent2: Optional[Resource] = None
    child: Optional[Resource] = None
    parent1Facts: List[Fact] = Field(default_factory=list)
    parent2Facts: List[Fact] = Field(default_factory=list)

    def _validate_self(self, result) -> None:
        """Validate FamilySearch child-and-parents relationship fields."""
        super()._validate_self(result)
        from gedcomtools.gedcomx.validation import check_instance

        check_instance(result, "parent1", self.parent1, Resource)
        check_instance(result, "parent2", self.parent2, Resource)
        check_instance(result, "child", self.child, Resource)
        for i, fact in enumerate(self.parent1Facts):
            check_instance(result, f"parent1Facts[{i}]", fact, Fact)
        for i, fact in enumerate(self.parent2Facts):
            check_instance(result, f"parent2Facts[{i}]", fact, Fact)

# Backward-compatible alias retained for older internal imports/tests.
FsRelationshipType = RelationshipType


log.debug(
    "fs_types_relationship extension loaded — "
    "RelationshipType, ChildAndParentsRelationship defined"
)
